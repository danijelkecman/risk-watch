from datetime import datetime, timezone

from app.models import InputSnapshot, Severity
from app.scoring import score_snapshot


def test_coordinated_public_proxy_stress_scores_hot():
    snapshot = InputSnapshot(
        timestamp=datetime.now(timezone.utc),
        high_yield_oas_bps=780,
        bdc_selloff_pct=6,
        credit_etf_selloff_pct=3.5,
        software_etf_selloff_pct=5,
        sec_filing_count_30d=28,
    )
    state = score_snapshot(snapshot)
    assert state.overall_score >= 75
    assert state.severity == Severity.deep_red
    assert state.alerts


def test_mild_environment_stays_below_red():
    snapshot = InputSnapshot(
        timestamp=datetime.now(timezone.utc),
        high_yield_oas_bps=340,
        bdc_selloff_pct=0.4,
        credit_etf_selloff_pct=0.2,
        software_etf_selloff_pct=0.5,
        sec_filing_count_30d=4,
    )
    state = score_snapshot(snapshot)
    assert state.overall_score < 55
    assert state.severity in {Severity.green, Severity.amber}


def test_missing_optional_feeds_do_not_require_fake_values():
    snapshot = InputSnapshot(
        timestamp=datetime.now(timezone.utc),
        high_yield_oas_bps=450,
    )
    state = score_snapshot(snapshot)
    assert state.snapshot.bdc_selloff_pct is None
    assert state.snapshot.sec_filing_count_30d is None
