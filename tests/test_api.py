from datetime import datetime, timezone

from app.models import InputSnapshot
from app.scoring import score_snapshot


def test_extreme_snapshot_scores_deep_red():
    snap = InputSnapshot(
        timestamp=datetime.now(timezone.utc),
        redemption_rate_pct=35,
        inflow_offset_usd_bn=0.2,
        peer_redemption_avg_pct=18,
        software_sector_stress=82,
        default_rate_estimate_pct=9,
        secondary_discount_pct=20,
        funding_spread_bps=650,
        regulator_attention=78,
        confidence_shock=81,
    )
    state = score_snapshot(snap)
    assert state.overall_score >= 75
    assert state.severity.value == "deep_red"
