from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any

import httpx

from .config import settings
from .models import InputSnapshot, SignalMetadata


FRED_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"
MASSIVE_DAILY_SUMMARY_URL = "https://api.massive.com/v2/aggs/grouped/locale/us/market/stocks/{date}"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
HIGH_YIELD_OAS_SERIES = "BAMLH0A0HYM2"
MASSIVE_MAX_LOOKBACK_DAYS = 5


class DataUnavailableError(RuntimeError):
    pass


class RealStreamSource:
    """Polls public and credentialed APIs, then emits snapshots when inputs change."""

    def __init__(self) -> None:
        self.client = httpx.AsyncClient(timeout=10.0)
        self._signals: dict[str, float] = {}
        self._metadata: dict[str, SignalMetadata] = {}
        self._last_poll: dict[str, datetime] = {}
        self._last_fingerprint: tuple[tuple[str, float], ...] | None = None

    async def close(self) -> None:
        await self.client.aclose()

    async def next(self) -> InputSnapshot | None:
        results = await asyncio.gather(
            self._refresh_fred(),
            self._refresh_massive(),
            self._refresh_sec(),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                print(f"Upstream provider failed: {self._safe_error_detail(result)}")
        if not self._signals:
            raise DataUnavailableError(
                "No upstream data is available. Configure FRED, Massive, or SEC credentials and check provider errors."
            )

        fingerprint = tuple(sorted(self._signals.items()))
        if fingerprint == self._last_fingerprint:
            return None
        self._last_fingerprint = fingerprint
        return InputSnapshot(
            timestamp=datetime.now(timezone.utc),
            high_yield_oas_bps=self._signals.get("high_yield_oas_bps"),
            bdc_selloff_pct=self._signals.get("bdc_selloff_pct"),
            credit_etf_selloff_pct=self._signals.get("credit_etf_selloff_pct"),
            software_etf_selloff_pct=self._signals.get("software_etf_selloff_pct"),
            sec_filing_count_30d=self._int_signal("sec_filing_count_30d"),
            signals=dict(self._metadata),
        )

    @staticmethod
    def _safe_error_detail(error: Exception) -> str:
        if isinstance(error, httpx.HTTPStatusError):
            request = error.request
            return f"{error.response.status_code} {request.method} {request.url.scheme}://{request.url.host}{request.url.path}"
        return type(error).__name__

    def _int_signal(self, name: str) -> int | None:
        value = self._signals.get(name)
        return int(value) if value is not None else None

    def _should_poll(self, provider: str, interval_seconds: float) -> bool:
        last_poll = self._last_poll.get(provider)
        return last_poll is None or datetime.now(timezone.utc) - last_poll >= timedelta(seconds=interval_seconds)

    def _record(
        self,
        name: str,
        value: float,
        *,
        source: str,
        observed_at: datetime,
        is_proxy: bool,
        detail: str,
    ) -> None:
        self._signals[name] = round(value, 4)
        self._metadata[name] = SignalMetadata(
            source=source,
            observed_at=observed_at,
            fetched_at=datetime.now(timezone.utc),
            is_proxy=is_proxy,
            detail=detail,
        )

    async def _refresh_fred(self) -> None:
        if not settings.fred_api_key or not self._should_poll("fred", settings.fred_poll_interval_seconds):
            return
        response = await self.client.get(
            FRED_OBSERVATIONS_URL,
            params={
                "api_key": settings.fred_api_key,
                "series_id": HIGH_YIELD_OAS_SERIES,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 1,
            },
        )
        response.raise_for_status()
        observation = response.json()["observations"][0]
        if observation["value"] == ".":
            return
        self._last_poll["fred"] = datetime.now(timezone.utc)
        self._record(
            "high_yield_oas_bps",
            float(observation["value"]) * 100,
            source=f"FRED:{HIGH_YIELD_OAS_SERIES}",
            observed_at=datetime.fromisoformat(observation["date"]).replace(tzinfo=timezone.utc),
            is_proxy=False,
            detail="ICE BofA US High Yield Index option-adjusted spread, converted from percent to basis points.",
        )

    async def _refresh_massive(self) -> None:
        if not settings.massive_api_key or not self._should_poll("massive", settings.massive_poll_interval_seconds):
            return
        market_days: list[dict[str, dict[str, Any]]] = []
        for days_ago in range(1, MASSIVE_MAX_LOOKBACK_DAYS + 1):
            date = datetime.now(timezone.utc).date() - timedelta(days=days_ago)
            response = await self.client.get(
                MASSIVE_DAILY_SUMMARY_URL.format(date=date.isoformat()),
                params={"adjusted": "true"},
                headers={"Authorization": f"Bearer {settings.massive_api_key}"},
            )
            response.raise_for_status()
            summary = {item["T"]: item for item in response.json().get("results", [])}
            if summary:
                market_days.append(summary)
            if len(market_days) == 2:
                break
        self._last_poll["massive"] = datetime.now(timezone.utc)
        if len(market_days) < 2:
            return
        latest, previous = market_days

        bdc_changes = [
            self._daily_selloff(latest[ticker], previous[ticker])
            for ticker in settings.bdc_tickers
            if ticker in latest and ticker in previous
        ]
        if bdc_changes:
            observed_at = max(
                self._massive_observed_at(latest[ticker])
                for ticker in settings.bdc_tickers
                if ticker in latest and ticker in previous
            )
            self._record(
                "bdc_selloff_pct",
                mean(bdc_changes),
                source=f"Massive:{','.join(settings.bdc_tickers)}",
                observed_at=observed_at,
                is_proxy=True,
                detail="Average completed trading-day downside move of the configured listed BDC basket versus previous close.",
            )

        self._record_massive_daily_selloff(
            latest,
            previous,
            settings.credit_etf_ticker,
            "credit_etf_selloff_pct",
            "Completed trading-day downside move of the configured liquid credit ETF versus previous close.",
        )
        self._record_massive_daily_selloff(
            latest,
            previous,
            settings.software_etf_ticker,
            "software_etf_selloff_pct",
            "Completed trading-day downside move of the configured software ETF versus previous close.",
        )

    def _record_massive_daily_selloff(
        self,
        latest: dict[str, dict[str, Any]],
        previous: dict[str, dict[str, Any]],
        ticker: str,
        name: str,
        detail: str,
    ) -> None:
        latest_bar = latest.get(ticker)
        previous_bar = previous.get(ticker)
        if latest_bar is None or previous_bar is None:
            return
        self._record(
            name,
            self._daily_selloff(latest_bar, previous_bar),
            source=f"Massive:{ticker}",
            observed_at=self._massive_observed_at(latest_bar),
            is_proxy=True,
            detail=detail,
        )

    @staticmethod
    def _daily_selloff(latest: dict[str, Any], previous: dict[str, Any]) -> float:
        latest_close = float(latest["c"])
        previous_close = float(previous["c"])
        if previous_close == 0:
            return 0.0
        return max(0.0, (previous_close - latest_close) / previous_close * 100)

    @staticmethod
    def _massive_observed_at(bar: dict[str, Any]) -> datetime:
        timestamp = int(bar.get("t", 0))
        if timestamp <= 0:
            return datetime.now(timezone.utc)
        divisor = 1_000_000_000 if timestamp > 10**15 else 1_000
        return datetime.fromtimestamp(timestamp / divisor, tz=timezone.utc)

    async def _refresh_sec(self) -> None:
        if (
            not settings.sec_user_agent
            or not settings.sec_ciks
            or not self._should_poll("sec", settings.sec_poll_interval_seconds)
        ):
            return
        responses = await asyncio.gather(
            *[
                self.client.get(
                    SEC_SUBMISSIONS_URL.format(cik=cik.zfill(10)),
                    headers={"User-Agent": settings.sec_user_agent},
                )
                for cik in settings.sec_ciks
            ]
        )
        cutoff = datetime.now(timezone.utc).date() - timedelta(days=30)
        filing_count = 0
        for response in responses:
            response.raise_for_status()
            dates = response.json().get("filings", {}).get("recent", {}).get("filingDate", [])
            filing_count += sum(datetime.fromisoformat(date).date() >= cutoff for date in dates)
        now = datetime.now(timezone.utc)
        self._last_poll["sec"] = now
        self._record(
            "sec_filing_count_30d",
            filing_count,
            source="SEC:EDGAR submissions",
            observed_at=now,
            is_proxy=True,
            detail="Count of EDGAR submissions over 30 days for configured public-company CIKs.",
        )
