"""
Market Analyst Agent - Ειδικός στην ανάλυση αγοράς, macro, sentiment και signals
"""

from tool_integration_hub import tool_hub
from logger import log

class MarketAnalystAgent:
    def analyze_market(self, symbol: str = "BTC/USDT"):
        log.info(f"Market Analyst: Analyzing {symbol}")
        master = tool_hub.run_master_report(symbol)
        snapshot = tool_hub.run_market_snapshot()
        macro = tool_hub.run_macro_report()
        print("Market Analyst completed analysis")
        return {"master": master, "snapshot": snapshot, "macro": macro}

# Register
market_analyst = MarketAnalystAgent()