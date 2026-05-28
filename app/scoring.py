from __future__ import annotations

from .models import Alert, DashboardState, InputSnapshot, RiskBreakdown, Severity


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


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

    if snapshot.redemption_rate_pct >= 15:
        alerts.append(Alert(
            title="Redemption pressure elevated",
            message="Outflows are large enough to test periodic-liquidity promises against underlying loan illiquidity.",
            severity=Severity.red if snapshot.redemption_rate_pct < 25 else Severity.deep_red,
        ))

    if snapshot.software_sector_stress >= 65:
        alerts.append(Alert(
            title="Software concentration danger",
            message="Tech/software weakness is now a portfolio transmission channel, not background noise.",
            severity=Severity.red,
        ))

    if snapshot.secondary_discount_pct >= 12:
        alerts.append(Alert(
            title="Secondary buyers smell blood",
            message="Wider discounts suggest forced-liquidity demand is rising faster than patient capital.",
            severity=Severity.red,
        ))

    if breakdown.oversight_heat >= 60:
        alerts.append(Alert(
            title="Regulatory heat rising",
            message="Official attention is increasing. That does not guarantee collapse, but it usually means the easy narrative is over.",
            severity=Severity.amber,
        ))

    if overall_score >= 75:
        alerts.append(Alert(
            title="Reflexive unwind risk",
            message="Confidence, liquidity, and repricing are feeding each other. This is where structures break reputationally before they break legally.",
            severity=Severity.deep_red,
        ))

    if not alerts:
        alerts.append(Alert(
            title="No immediate structural break",
            message="Stress is present, but the system is still behaving like a monitored credit market rather than a disorderly run.",
            severity=Severity.green,
        ))

    return alerts


def annotations(snapshot: InputSnapshot, breakdown: RiskBreakdown) -> list[str]:
    notes: list[str] = []

    if breakdown.liquidity_mismatch >= 65:
        notes.append("Danger lies in the wrapper: redemption demand is outrunning the liquidity of the underlying loans.")
    if breakdown.contagion >= 60:
        notes.append("Danger lies in cross-manager signaling: redemptions at peers validate more redemptions elsewhere.")
    if breakdown.sector_damage >= 60:
        notes.append("Danger lies in software-heavy books: weak marks and AI repricing can turn concentration into defaults.")
    if breakdown.market_stress >= 60:
        notes.append("Danger lies in the secondary market: discounts are revealing where patience has vanished.")
    if breakdown.oversight_heat >= 60:
        notes.append("Danger lies in policy attention: regulators show up when private assurances stop being enough.")

    if not notes:
        notes.append("No single fracture line dominates yet.")

    return notes


def score_snapshot(snapshot: InputSnapshot) -> DashboardState:
    liquidity_mismatch = clamp(
        1.10 * snapshot.redemption_rate_pct
        + 0.25 * snapshot.confidence_shock
        + 0.40 * max(0.0, 20 - snapshot.inflow_offset_usd_bn * 10)
    )

    contagion = clamp(
        0.50 * snapshot.peer_redemption_avg_pct
        + 0.30 * snapshot.confidence_shock
        + 0.20 * snapshot.regulator_attention
    )

    sector_damage = clamp(
        0.65 * snapshot.software_sector_stress
        + 0.35 * snapshot.default_rate_estimate_pct * 8
    )

    market_stress = clamp(
        0.50 * snapshot.secondary_discount_pct * 4
        + 0.50 * min(snapshot.funding_spread_bps / 6, 100)
    )

    oversight_heat = clamp(
        0.70 * snapshot.regulator_attention
        + 0.30 * snapshot.confidence_shock
    )

    overall_score = clamp(
        0.31 * liquidity_mismatch
        + 0.20 * contagion
        + 0.23 * sector_damage
        + 0.18 * market_stress
        + 0.08 * oversight_heat
        + (8 if liquidity_mismatch >= 70 and sector_damage >= 70 else 0)
        + (6 if contagion >= 60 and market_stress >= 60 else 0)
        + (5 if snapshot.redemption_rate_pct >= 25 and snapshot.secondary_discount_pct >= 15 else 0)
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
