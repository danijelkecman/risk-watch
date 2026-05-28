from __future__ import annotations

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class Severity(str, Enum):
    green = "green"
    amber = "amber"
    red = "red"
    deep_red = "deep_red"


class InputSnapshot(BaseModel):
    timestamp: datetime
    redemption_rate_pct: float = Field(ge=0, le=100)
    inflow_offset_usd_bn: float
    peer_redemption_avg_pct: float = Field(ge=0, le=100)
    software_sector_stress: float = Field(ge=0, le=100)
    default_rate_estimate_pct: float = Field(ge=0, le=100)
    secondary_discount_pct: float = Field(ge=0, le=100)
    funding_spread_bps: float = Field(ge=0)
    regulator_attention: float = Field(ge=0, le=100)
    confidence_shock: float = Field(ge=0, le=100)


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


class RiskSnapshotCreate(BaseModel):
    source: str = "mock"
    payload: DashboardState


class ReplayMode(str, Enum):
    live = "live"
    replay = "replay"


class ReplayRequest(BaseModel):
    limit: int = Field(default=120, ge=10, le=1000)
    speed_multiplier: float = Field(default=8.0, ge=0.1, le=100.0)
