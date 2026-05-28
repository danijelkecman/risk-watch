from datetime import datetime, timezone

from app.models import InputSnapshot, Severity
from app.scoring import score_snapshot


def test_high_redemption_environment_scores_hot():
    snapshot = InputSnapshot(
        timestamp=datetime.now(timezone.utc),
        redemption_rate_pct=40,
        inflow_offset_usd_bn=0.1,
        peer_redemption_avg_pct=20,
        software_sector_stress=92,
        default_rate_estimate_pct=10,
        secondary_discount_pct=24,
        funding_spread_bps=780,
        regulator_attention=82,
        confidence_shock=95,
    )
    state = score_snapshot(snapshot)
    assert state.overall_score >= 75
    assert state.severity == Severity.deep_red
    assert state.alerts


def test_mild_environment_stays_below_red():
    snapshot = InputSnapshot(
        timestamp=datetime.now(timezone.utc),
        redemption_rate_pct=6,
        inflow_offset_usd_bn=1.6,
        peer_redemption_avg_pct=5,
        software_sector_stress=25,
        default_rate_estimate_pct=2.5,
        secondary_discount_pct=4,
        funding_spread_bps=240,
        regulator_attention=15,
        confidence_shock=18,
    )
    state = score_snapshot(snapshot)
    assert state.overall_score < 55
    assert state.severity in {Severity.green, Severity.amber}
