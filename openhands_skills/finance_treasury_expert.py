"""
Finance & Treasury Expert Skill for OpenHands - ULTRA GOD-LIKE
Institutional-grade CFO/Treasury specialist for serious web3, crypto, and Hacash projects.
Focus: Professional treasury management, tokenomics financial modeling, DeFi strategies, risk frameworks, liquidity, on-chain operations, investor-grade reporting.
EXTREME CAUTION: Finance and business require zero hype, full auditability, regulatory alignment, and conservative risk models. All outputs must pass legal, security, and PM gates.
Integrates with: legal_compliance_expert (god-tier), crypto_payments_expert, hacash_* experts, analytics-specialist, project-manager, supervisor.
"""

from logger import log
from typing import Dict, Any, List, Optional

try:
    from openhands_skills.code_researcher import code_researcher
except Exception:
    code_researcher = None

try:
    from persistent_memory import persistent_memory
except Exception:
    persistent_memory = None


class FinanceTreasuryExpert:
    """
    ULTRA GOD-LIKE Finance & Treasury Specialist.
    Acts as virtual CFO for client projects involving money, tokens, treasuries, or economic models.
    10x institutional standards: formal IPS, multisig policies, stress-tested models, on-chain visibility, conservative yield.
    Never chase yield. Diversify. Document everything. Coordinate with legal for compliance.
    """

    def __init__(self):
        self.focus = "Protecting and growing client capital with god-like precision, especially in volatile crypto/Hacash environments. Zero tolerance for avoidable financial risk."

    def god_tier_treasury_strategy_and_ips(self, project: str, include_hacash: bool = False, include_defi: bool = False) -> Dict[str, Any]:
        """GOD-LIKE: Full Investment Policy Statement (IPS) + treasury architecture. The foundation for all financial work. Ultra conservative by default."""
        log.info(f"FinanceTreasuryExpert (ULTRA GOD TIER): Treasury strategy for: {project[:60]}")

        past = ""
        if persistent_memory:
            try:
                past = persistent_memory.retrieve_relevant_evolution(project + " treasury finance", max_results=3) or ""
            except Exception:
                pass

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(project + " crypto treasury 2026", "DeFi treasury IPS multisig diversification best practices 2026")
            except Exception:
                pass

        god = {
            "project": project,
            "god_tier_ips": {
                "objectives": "Preserve capital, maintain liquidity for operations, generate conservative real yield without principal risk. Target: 3-8% net annualized after fees/risk, in stable or blue-chip assets.",
                "constraints": "No single asset >20-25% (except operating stablecoins). No single platform/counterparty >15%. Cold storage minimum 60-70% for strategic reserves. All yields must be stress-tested for -50% market moves.",
                "allocation_guidelines": "Core: 40-60% high-quality stables (USDC/USDT diversified across 3+ custodians/jurisdictions). Strategic: 20-30% BTC/ETH or Hacash equivalents (HAC/HACD if applicable). Yield: 10-20% max in audited DeFi (AAVE, Curve, or equivalent blue-chips). Cash buffer: 10-15% fiat rails.",
                "hacash_specific": "If include_hacash: Model separate HAC (utility/fee) vs HACD (scarcity/value) treasuries. Factor one-way BTC peg inflows as strategic reserve. Mining rewards as operating cashflow with 30%+ reserve policy. Diamond economics: treat HACD as illiquid premium asset with long hold bias.",
                "defi_strategies": "Dollar-cost average into yield. Diversify across 3-5 protocols minimum. Use only audited, high-TVL, battle-tested. Prefer stablecoin lending over volatile LP. Monitor for smart contract, oracle, and liquidity risks constantly. Rebalance triggers: TVL drop >30%, APY compression >50%, or governance changes.",
                "technical_policies": "Multisig minimum 3/5 or 4/7 for treasury wallets. Timelocks on large outflows. Separate hot (ops, <5% of treasury) / warm / cold. On-chain monitoring + alerts (via analytics or custom). Full audit trail for every tx. Use agentic execution tools only after human + legal review for material moves.",
                "risk_management": "Monthly stress tests (historical + hypothetical). Liquidity forecasting (30/90/365 days). Counterparty limits + diversification matrix. Insurance review (if available). Breach/ hack response playbooks integrated with security-auditor and legal.",
                "governance": "Written IPS signed by client + PM. Quarterly review cadence. Any deviation = guarded proposal + legal sign-off."
            },
            "god_tier_notes": "Think like a top crypto CFO + traditional treasury pro who survived 2022. Anticipate black swans, regulatory shocks (MiCA, SEC actions), and 10x scale. Every model must be defensible in a boardroom or courtroom. No 'degen' strategies ever. Conservative > clever.",
            "deliverables": "Full IPS document (PDF + editable), treasury dashboard spec (for analytics-specialist), multisig policy + runbook, 12-month cashflow model, risk heatmaps, client presentation deck with conservative scenarios.",
            "handoffs": "To legal_compliance_expert.god_tier (tax, securities, AML on treasury ops). To crypto_payments_expert (payment rails integration). To hacash_* experts (token-specific modeling). To programmer (on-chain treasury scripts/WASM if needed). To project-manager (financial gates in every review). To analytics-specialist (real-time treasury KPIs, LTV/ROI tie-in).",
            "past_learnings_research": (past + " " + (research[:700] if research else ""))[:900]
        }
        print("💰 FinanceTreasuryExpert (ULTRA GOD TIER): God-like treasury IPS + strategy delivered. Extreme caution applied.")
        return god

    def god_tier_financial_modeling_and_tokenomics(self, requirements: str, include_hacash: bool = False) -> Dict[str, Any]:
        """GOD-LIKE: Rigorous financial models, tokenomics projections, unit economics, scenario planning. Ultra detailed and conservative."""
        log.info(f"FinanceTreasuryExpert (ULTRA GOD TIER): Financial modeling for: {requirements[:60]}")

        god = {
            "requirements": requirements,
            "god_tier_models": {
                "core": "3-statement model (P&L, BS, CF) in fiat + crypto terms. Monthly granularity for first 24 months, then quarterly. Conservative assumptions only (base, bear -50%, stress -80%).",
                "tokenomics_financials": "Supply/demand curves, velocity modeling, staking/reward dilution, burn mechanisms, treasury allocation impact. For Hacash: separate HAC fee/settlement economics vs HACD scarcity value accrual. Peg inflow modeling with redemption scenarios.",
                "unit_economics": "CAC, LTV, payback period, contribution margin per user/transaction (on-chain fees, 3D usage, payments). Tie directly to analytics-specialist data.",
                "treasury_projections": "Inflows (rewards, sales, yields), outflows (ops, dev, marketing, legal). Runway in months under multiple scenarios. Yield contribution capped at conservative 5-8% net.",
                "risk_adjusted": "Sharpe-like ratios for treasury strategies. VaR, CVaR, scenario Monte Carlo (10k+ paths). Liquidity coverage ratios. Counterparty concentration risk.",
                "hacash_crypto_specific": "Mining economics sensitivity (hashrate, difficulty, energy). Channel/L2 settlement volume impact on L1 fees. Diamond (HACD) as treasury asset: illiquidity premium + volatility modeling. One-way peg: inflow probability + custody risk premium."
            },
            "god_tier_standards": "All models versioned, assumptions documented, sensitivity tables included. Must survive external audit or investor diligence. No hockey-stick growth without 3+ bear cases. Integrate with legal for any securities implications.",
            "tools_recommendations": "Excel/Google Sheets for core (auditable). Python (pandas, numpy, Monte Carlo libs) for advanced. On-chain dashboards via analytics or custom (Dune-like for Hacash). Reconcile monthly vs quarterly.",
            "deliverables": "Interactive model file + PDF summary, executive one-pager with key risks/assumptions, investor-grade appendix, integration spec for PM client deck and analytics dashboards.",
            "handoffs": "legal_compliance_expert.god_tier_crypto_hacash (securities classification). programmer_expert (on-chain financial logic or WASM models). analytics-specialist (live data feeds). project-manager (financial review gates). hacash_l* experts (economic model validation).",
            "caution_note": "Finance mistakes kill projects and reputations. Every assumption must be stress-tested. Conservative bias always. When in doubt, model lower returns and higher risks."
        }
        print("💰 FinanceTreasuryExpert (ULTRA GOD TIER): Ultra detailed financial + tokenomics models delivered.")
        return god

    def god_tier_liquidity_risk_and_operations(self) -> Dict[str, Any]:
        """GOD-LIKE: Day-to-day treasury ops, liquidity forecasting, execution policies, on-chain controls. The 'how we actually move money safely'."""
        return {
            "liquidity_framework": "Daily/weekly/monthly forecasting. Operating buffer (30-90 days). Strategic reserves (1-3+ years). Funding sources mapped (yields, inflows, raises). Stress: model -70% liquidity event + delayed inflows.",
            "execution_policies": "Tiered approvals (small ops vs large treasury). Multisig + timelock for >X threshold. Pre-approved counterparties list. Rebalancing rules (calendar + threshold). Full pre/post tx documentation.",
            "on_chain_controls": "Separate treasury vs operating wallets. Hardware + multisig. Real-time monitoring + alerts (balance, tx, anomalies). Agentic tools only for routine small moves after policy approval. Audit every quarter.",
            "best_practices_from_research": "Written treasury policy document. Separate hot/warm/cold. Diversify stables across issuers/jurisdictions. Reconcile on-chain vs off-chain monthly. Insurance where sensible. Rehearse breach response.",
            "god_tier_caution": "One bad treasury decision or hack can end the project. Liquidity is oxygen. Never optimize for yield over survival. All ops must be reversible or insured where possible.",
            "handoffs": "To security-auditor (wallet/ops audit). To legal (counterparty contracts, tax). To devops (monitoring infra). To programmer (custom on-chain treasury scripts if needed). To PM (ops gates)."
        }

    def god_tier_team_finance_handoff_manifest(self, project: str) -> Dict[str, Any]:
        """GOD-LIKE: Exact manifest for PM + supervisor to orchestrate finance across the full god-like team."""
        return {
            "project": project,
            "mandatory_early_calls": [
                "finance_treasury_expert.god_tier_treasury_strategy_and_ips(...) at discovery",
                "god_tier_financial_modeling_and_tokenomics(...) before any token or payment work",
                "god_tier_liquidity_risk_and_operations(...) for execution policies"
            ],
            "integration_points": "Legal god-tier (compliance/tax overlap), crypto_payments (rails), hacash_* (economic models), analytics (KPIs + live data), programmer (on-chain finance), PM (financial gates at every review + client deck), supervisor (god-mode for any treasury change).",
            "god_tier_standards": "Finance is non-negotiable. Every model/decision must be auditable, conservative, and client-approved. Guarded proposals required for any material treasury or tokenomics change. 10x means surviving black swans and regulators.",
            "caution": "We are extremely careful here. No shortcuts. When finance/business is involved, god-like means institutional + paranoid + perfect documentation."
        }

# Register
finance_treasury_expert = FinanceTreasuryExpert()
print("💰 FinanceTreasuryExpert (ULTRA GOD TIER) registered. Ready for sub_type='finance'. Institutional CFO for crypto/web3/Hacash - extreme caution, zero hype.")