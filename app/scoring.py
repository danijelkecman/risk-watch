from __future__ import annotations

from statistics import mean

from .models import Alert, DashboardState, InputSnapshot, RiskBreakdown, Severity


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def average(*values: float | None) -> float:
    available = [value for value in values if value is not None]
    return mean(available) if available else 0.0


def scale(value: float | None, multiplier: float) -> float | None:
    return clamp(value * multiplier) if value is not None else None


def severity_for(score: float) -> Severity:
    if score < 30:
        return Severity.green
    if score < 55:
        return Severity.amber
    if score < 75:
        return Severity.red
    return Severity.deep_red


def build_alerts(snapshot: InputSnapshot, breakdown: RiskBreakdown, overall_score: float) -> list[Alert]:
    alerts: list[Alert] = []

    if snapshot.high_yield_oas_bps is not None and snapshot.high_yield_oas_bps >= 500:
        alerts.append(Alert(
            title="High-yield spreads elevated",
            message="The public high-yield spread proxy has widened into a stressed range.",
            severity=Severity.red if snapshot.high_yield_oas_bps < 700 else Severity.deep_red,
        ))

    if snapshot.software_etf_selloff_pct is not None and snapshot.software_etf_selloff_pct >= 3:
        alerts.append(Alert(
            title="Software proxy under pressure",
            message="The configured software ETF is selling off, which can pressure software-heavy private-credit books.",
            severity=Severity.red,
        ))

    if snapshot.bdc_selloff_pct is not None and snapshot.bdc_selloff_pct >= 3:
        alerts.append(Alert(
            title="Listed BDC basket repricing",
            message="Public BDC prices are moving lower together. This is a liquid-market proxy, not a private-loan mark.",
            severity=Severity.red,
        ))

    if breakdown.oversight_heat >= 60:
        alerts.append(Alert(
            title="Public filing activity elevated",
            message="EDGAR activity for the configured public-company basket is elevated and warrants review.",
            severity=Severity.amber,
        ))

    if overall_score >= 75:
        alerts.append(Alert(
            title="Cross-proxy stress elevated",
            message="Credit spreads and liquid-market proxies are deteriorating together.",
            severity=Severity.deep_red,
        ))

    if not alerts:
        alerts.append(Alert(
            title="No immediate public-market break",
            message="Configured public indicators are not showing a synchronized stress event.",
            severity=Severity.green,
        ))

    return alerts


def annotations(snapshot: InputSnapshot, breakdown: RiskBreakdown) -> list[str]:
    notes: list[str] = []

    if breakdown.liquidity_mismatch >= 60:
        notes.append("Liquid credit proxies are weakening; this can precede pressure in less liquid private-credit holdings.")
    if breakdown.contagion >= 60:
        notes.append("Listed BDCs are repricing together, indicating cross-manager public-market pressure.")
    if breakdown.sector_damage >= 60:
        notes.append("The software ETF proxy is under pressure, raising concentration risk for software-heavy books.")
    if breakdown.market_stress >= 60:
        notes.append("High-yield spreads and traded credit proxies are jointly signaling market stress.")
    if breakdown.oversight_heat >= 60:
        notes.append("Public filing activity is elevated for the monitored company basket.")

    if not notes:
        notes.append("No single public-market proxy dominates the current score.")
    notes.append("Private-fund redemptions, inflows, NAV marks, and gates require an internal administrator feed.")
    return notes


def score_snapshot(snapshot: InputSnapshot) -> DashboardState:
    high_yield_stress = (
        clamp((snapshot.high_yield_oas_bps - 300) / 5)
        if snapshot.high_yield_oas_bps is not None
        else None
    )
    bdc_stress = scale(snapshot.bdc_selloff_pct, 18)
    credit_etf_stress = scale(snapshot.credit_etf_selloff_pct, 30)
    software_stress = scale(snapshot.software_etf_selloff_pct, 22)
    filing_stress = scale(snapshot.sec_filing_count_30d, 3)

    liquidity_mismatch = average(credit_etf_stress, bdc_stress)
    contagion = average(bdc_stress, credit_etf_stress)
    sector_damage = average(software_stress, high_yield_stress)
    market_stress = average(high_yield_stress, credit_etf_stress, bdc_stress)
    oversight_heat = filing_stress or 0.0

    overall_score = clamp(
        0.24 * liquidity_mismatch
        + 0.20 * contagion
        + 0.20 * sector_damage
        + 0.29 * market_stress
        + 0.07 * oversight_heat
        + (8 if market_stress >= 70 and sector_damage >= 70 else 0)
        + (6 if contagion >= 60 and liquidity_mismatch >= 60 else 0)
    )
    breakdown = RiskBreakdown(
        liquidity_mismatch=round(liquidity_mismatch, 1),
        contagion=round(contagion, 1),
        sector_damage=round(sector_damage, 1),
        market_stress=round(market_stress, 1),
        oversight_heat=round(oversight_heat, 1),
    )
    severity = severity_for(overall_score)
    return DashboardState(
        timestamp=snapshot.timestamp,
        overall_score=round(overall_score, 1),
        severity=severity,
        snapshot=snapshot,
        breakdown=breakdown,
        alerts=build_alerts(snapshot, breakdown, overall_score),
        annotations=annotations(snapshot, breakdown),
    )
