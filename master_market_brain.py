from signal_engine import generate_signal
from consensus_engine import generate_consensus
from volatility_engine import analyze_volatility
from regime_engine import analyze_market_regime
from alert_engine import generate_alerts
from memory_engine import store_market_snapshot, analyze_memory
from signal_history_engine import store_signal, analyze_signal_history
from performance_engine import update_signal_performance, analyze_performance
from adaptive_ai_engine import calculate_adaptive_confidence, generate_ai_outlook
from regime_transition_engine import detect_market_phase
from whale_tracker_engine import detect_whale_activity
from smart_money_engine import analyze_smart_money
from ai_scoring_engine import calculate_market_score
from portfolio_ai_engine import generate_portfolio_strategy
from config import config
from logger import log


def generate_master_report(symbol=config.DEFAULT_SYMBOL):
    log.info(f"Generating Master Report for {symbol}")

    # Core Analysis
    signal = generate_signal(symbol)
    consensus = generate_consensus(symbol)
    volatility = analyze_volatility(symbol)
    regime = analyze_market_regime()
    alerts = generate_alerts(symbol)
    whale_data = detect_whale_activity("BTC/USDT")
    smart_money = analyze_smart_money("BTC/USDT")

    # Risk & Volatility
    risk = "MODERATE"
    if abs(volatility.get("change_percent", 0)) >= 3:
        risk = "HIGH"
    elif abs(volatility.get("change_percent", 0)) <= 1:
        risk = "LOW"

    volatility_state = "ELEVATED" if len(volatility.get("alerts", [])) > 1 else "STABLE"

    # Phase & Scoring
    phase, phase_explanation = detect_market_phase(
        rsi=signal["rsi"],
        macd=signal["macd"],
        signal=signal["signal"],
        regime=regime["crypto_regime"],
        volatility=volatility_state
    )

    market_score = calculate_market_score(
        signal=signal["signal"],
        regime=regime["crypto_regime"],
        phase=phase,
        volatility=volatility_state,
        smart_money=smart_money["state"],
        whale_activity=whale_data["state"],
        rsi=signal["rsi"],
        macd=signal["macd"]
    )

    portfolio = generate_portfolio_strategy(
        market_score=market_score["final_score"],
        regime=regime["crypto_regime"],
        volatility=volatility_state,
        smart_money=smart_money["state"],
        whale_activity=whale_data["state"]
    )

    # Performance & Memory
    update_signal_performance()
    performance = analyze_performance()

    probability = calculate_adaptive_confidence(
        signal=signal["signal"],
        consensus=consensus["consensus"],
        volatility=volatility_state,
        regime=regime["crypto_regime"],
        performance_accuracy=performance["accuracy"]
    )

    outlook = generate_ai_outlook(probability, regime["crypto_regime"])

    store_market_snapshot(
        symbol=symbol,
        signal=signal["signal"],
        regime=regime["crypto_regime"],
        probability=probability,
        rsi=signal["rsi"],
        macd=signal["macd"],
        consensus=consensus["consensus"]
    )
    store_signal(
        symbol=symbol,
        signal=signal["signal"],
        price=signal["price"],
        regime=regime["crypto_regime"],
        probability=probability
    )

    memory_insights = analyze_memory()
    signal_stats = analyze_signal_history()

    # ==================== FINAL REPORT (ΧΩΡΙΣ GEOPOLITICAL) ====================
    report = f"""
===================================
      iNFO DUST MARKET BRAIN
===================================

Symbol: {symbol}

Market Structure: {phase}
Momentum State: {signal['signal']}
Market Regime: {regime['crypto_regime']}
Risk Level: {risk}
Volatility: {volatility_state}
AI Probability Score: {probability}%

AI Outlook: {outlook}

Market Phase Insight: {phase_explanation}

Whale Activity: {whale_data['state']}
Whale Insight: {whale_data['message']}

Smart Money: {smart_money['state']}
Smart Money Insight: {smart_money['insight']}

Market Quality Score: {market_score['final_score']} / 100
Market Score Insight: {market_score['interpretation']}

Portfolio AI Strategy: {portfolio['strategy']}
Risk Mode: {portfolio['risk_mode']}
Recommended BTC Allocation: {portfolio['btc_allocation']}%
Recommended Cash Allocation: {portfolio['cash_allocation']}%
"""

    report += "\nActive Alerts:\n"
    for alert in alerts:
        report += f"- {alert}\n"

    report += "\nHistorical AI Insights:\n"
    for insight in memory_insights:
        report += f"- {insight}\n"

    report += f"""
Signal History Analysis:
Total Signals: {signal_stats['total']}
BUY Signals: {signal_stats['buy_signals']}
SELL Signals: {signal_stats['sell_signals']}
NEUTRAL Signals: {signal_stats['neutral_signals']}

AI Performance Metrics:
Winning Signals: {performance['wins']}
Losing Signals: {performance['losses']}
Neutral Signals: {performance['neutral']}
AI Accuracy: {performance['accuracy']}%
===================================
"""

    log.success(f"Master Report generated for {symbol}")
    return report