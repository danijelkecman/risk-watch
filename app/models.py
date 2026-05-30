from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    green = "green"
    amber = "amber"
    red = "red"
    deep_red = "deep_red"


class SignalMetadata(BaseModel):
    source: str
    observed_at: datetime
    fetched_at: datetime
    is_proxy: bool
    detail: str


class InputSnapshot(BaseModel):
    timestamp: datetime
    high_yield_oas_bps: float | None = Field(default=None, ge=0)
    bdc_selloff_pct: float | None = Field(default=None, ge=0)
    credit_etf_selloff_pct: float | None = Field(default=None, ge=0)
    software_etf_selloff_pct: float | None = Field(default=None, ge=0)
    sec_filing_count_30d: int | None = Field(default=None, ge=0)
    signals: dict[str, SignalMetadata] = Field(default_factory=dict)


class RiskBreakdown(BaseModel):
    liquidity_mismatch: float
    contagion: float
    sector_damage: float
    market_stress: float
    oversight_heat: float


class Alert(BaseModel):
    title: str
    message: str
    severity: Severity


class DashboardState(BaseModel):
    timestamp: datetime
    overall_score: float = Field(ge=0, le=100)
    severity: Severity
    snapshot: InputSnapshot
    breakdown: RiskBreakdown
    alerts: list[Alert]
    annotations: list[str]


class ReplayMode(str, Enum):
    live = "live"
    replay = "replay"


class ReplayRequest(BaseModel):
    limit: int = Field(default=120, ge=10, le=1000)
    speed_multiplier: float = Field(default=8.0, ge=0.1, le=100.0)
