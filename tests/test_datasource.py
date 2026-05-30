import httpx
import pytest

from app.config import settings
from app.datasource import RealStreamSource


@pytest.mark.asyncio
async def test_fred_observation_is_converted_to_basis_points_and_emitted_once(monkeypatch):
    monkeypatch.setattr(settings, "fred_api_key", "fred-key")
    monkeypatch.setattr(settings, "massive_api_key", "")
    monkeypatch.setattr(settings, "sec_user_agent", "")
    monkeypatch.setattr(settings, "fred_poll_interval_seconds", 0)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"observations": [{"date": "2026-05-29", "value": "3.75"}]},
            request=request,
        )

    source = RealStreamSource()
    await source.client.aclose()
    source.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        snapshot = await source.next()
        assert snapshot is not None
        assert snapshot.high_yield_oas_bps == 375
        assert snapshot.signals["high_yield_oas_bps"].is_proxy is False
        assert await source.next() is None
    finally:
        await source.close()


@pytest.mark.asyncio
async def test_massive_data_survives_fred_failure(monkeypatch, capsys):
    monkeypatch.setattr(settings, "fred_api_key", "fred-key")
    monkeypatch.setattr(settings, "massive_api_key", "massive-key")
    monkeypatch.setattr(settings, "sec_user_agent", "")
    monkeypatch.setattr(settings, "fred_poll_interval_seconds", 0)
    monkeypatch.setattr(settings, "massive_poll_interval_seconds", 0)
    monkeypatch.setattr(settings, "bdc_tickers", ["ARCC", "BXSL"])
    monkeypatch.setattr(settings, "credit_etf_ticker", "HYG")
    monkeypatch.setattr(settings, "software_etf_ticker", "IGV")

    massive_requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal massive_requests
        if request.url.host == "api.stlouisfed.org":
            return httpx.Response(503, request=request)
        assert request.url.host == "api.massive.com"
        assert request.headers["Authorization"] == "Bearer massive-key"
        assert "apiKey" not in request.url.params
        assert request.url.params["adjusted"] == "true"
        assert request.url.path.startswith("/v2/aggs/grouped/locale/us/market/stocks/")
        massive_requests += 1
        closes = (
            {"ARCC": 98.0, "BXSL": 96.0, "HYG": 98.5, "IGV": 101.0}
            if massive_requests == 1
            else {"ARCC": 100.0, "BXSL": 100.0, "HYG": 100.0, "IGV": 100.0}
        )
        return httpx.Response(
            200,
            json={
                "results": [
                    {"T": ticker, "c": close, "t": 1_700_000_000_000}
                    for ticker, close in closes.items()
                ]
            },
            request=request,
        )

    source = RealStreamSource()
    await source.client.aclose()
    source.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        snapshot = await source.next()
        assert snapshot is not None
        assert snapshot.bdc_selloff_pct == 3
        assert snapshot.credit_etf_selloff_pct == 1.5
        assert snapshot.software_etf_selloff_pct == 0
        assert massive_requests == 2
        output = capsys.readouterr().out
        assert "fred-key" not in output
        assert "503 GET https://api.stlouisfed.org/fred/series/observations" in output
    finally:
        await source.close()
