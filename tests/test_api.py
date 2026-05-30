from datetime import datetime, timezone

from app.models import InputSnapshot
from app.scoring import score_snapshot


def test_extreme_public_proxy_snapshot_scores_deep_red():
    snap = InputSnapshot(
        timestamp=datetime.now(timezone.utc),
        high_yield_oas_bps=850,
        bdc_selloff_pct=7,
        credit_etf_selloff_pct=4,
        software_etf_selloff_pct=6,
        sec_filing_count_30d=30,
    )
    state = score_snapshot(snap)
    assert state.overall_score >= 75
    assert state.severity.value == "deep_red"
