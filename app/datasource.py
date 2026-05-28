from __future__ import annotations

import math
import random
from datetime import datetime, timezone

from .models import InputSnapshot


class MockStreamSource:
    """Generates plausible but fake stress data.

    Replace this with adapters for filings, market proxies, and analyst overrides.
    """

    def __init__(self) -> None:
        self.t = 0
        random.seed(42)

    def next(self) -> InputSnapshot:
        self.t += 1
        wave = math.sin(self.t / 8)
        stress_pulse = 1 if self.t % 50 > 35 else 0
        idio = random.uniform(-2.2, 2.2)
        redemption_rate_pct = min(max(12 + 8 * wave + 8 * stress_pulse + idio, 2), 45)
        inflow_offset_usd_bn = min(max(1.2 - 0.5 * stress_pulse + random.uniform(-0.2, 0.3), 0), 2.5)
        peer_redemption_avg_pct = min(max(9 + 3.5 * wave + 3 * stress_pulse + idio / 2, 1), 25)
        software_sector_stress = min(max(45 + 20 * wave + 18 * stress_pulse + idio * 2, 5), 95)
        default_rate_estimate_pct = min(max(4 + 1.5 * wave + 2.2 * stress_pulse + abs(idio) / 3, 1), 12)
        secondary_discount_pct = min(max(7 + 4 * wave + 5 * stress_pulse + abs(idio), 1), 30)
        funding_spread_bps = min(max(320 + 80 * wave + 110 * stress_pulse + idio * 15, 100), 900)
        regulator_attention = min(max(35 + 12 * stress_pulse + 10 * wave + abs(idio), 0), 100)
        confidence_shock = min(max(30 + 25 * stress_pulse + 18 * wave + abs(idio), 0), 100)
        return InputSnapshot(
            timestamp=datetime.now(timezone.utc),
            redemption_rate_pct=round(redemption_rate_pct, 2),
            inflow_offset_usd_bn=round(inflow_offset_usd_bn, 2),
            peer_redemption_avg_pct=round(peer_redemption_avg_pct, 2),
            software_sector_stress=round(software_sector_stress, 2),
            default_rate_estimate_pct=round(default_rate_estimate_pct, 2),
            secondary_discount_pct=round(secondary_discount_pct, 2),
            funding_spread_bps=round(funding_spread_bps, 2),
            regulator_attention=round(regulator_attention, 2),
            confidence_shock=round(confidence_shock, 2),
        )
