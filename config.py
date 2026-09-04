# =========================================
# CENTRAL CONFIGURATION ENGINE
# =========================================

from dotenv import load_dotenv
import os
from pathlib import Path
from typing import List

load_dotenv(override=True)

# =========================================
# SETTINGS CLASS
# =========================================

class Config:
    # === API KEYS & SECRETS ===
    FINNHUB_API_KEY: str = os.getenv("FINNHUB_API_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    FINLIGHT_API_KEY: str = os.getenv("FINLIGHT_API_KEY", "")
    MORALIS_API_KEY: str = os.getenv("MORALIS_API_KEY", "")  # Optional - free tier available for PulseChain wallet/token history (nice upgrade for chain analysis)

    # === PRIMARY RELIABLE LLM BACKEND (llama.cpp on AMD RX 9070 XT via Vulkan) ===
    # Served by start-llama-vulkan.ps1 → llama-server on :8080 (OpenAI compatible /v1)
    # Model: gemma-4-26B-A4B-it-UD-Q4_K_XL.gguf (Unsloth QAT MoE)
    # Legacy HIP / start-llama-hip.ps1 references have been retired.
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemma-4-26b-qat")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8080/v1")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "sk-dummy-local")

    # === CODING MODEL (Qwen3-Coder-30B-A3B on RX 9070 XT) ===
    # Το backend σερβίρει ΕΝΑ μοντέλο τη φορά (16GB VRAM δεν χωράει gemma-26B +
    # qwen-30B μαζί). Οι development agents (coder/tester/reviewer/security/
    # debugger) ζητούν αυτό το alias· όταν τρέχεις το start-llama-coder.ps1
    # φορτώνει το Qwen3-Coder. llama-server σερβίρει ό,τι είναι φορτωμένο, οπότε
    # το alias είναι κυρίως ετικέτα — άλλαξε backend με το coder launcher.
    CODING_MODEL: str = os.getenv("CODING_MODEL", "qwen3-coder-30b")

    # === OLLAMA REMOVED ===
    # Voice / legacy Ollama support has been dropped per user request (not needed).
    # If you ever want it back, the variables can be re-added.

    # === DEFAULTS ===
    DEFAULT_SYMBOL: str = "BTC/USDT"
    DEFAULT_TIMEFRAME: str = "1h"
    DEFAULT_LIMIT: int = 100

    # === PATHS ===
    BASE_DIR = Path(__file__).parent
    MARKET_MEMORY_FILE: str = "market_memory.json"
    SIGNAL_HISTORY_FILE: str = "signal_history.json"
    LOG_DIR: str = "logs"                     # ← Νέα προσθήκη για logging

    # === WATCHLISTS ===
    STOCKS: List[str] = [
        "NVDA", "MSFT", "AAPL", "AMZN", "META", "GOOGL", "TSLA", "AMD", "PLTR",
        "AVGO", "NFLX", "JPM", "GS", "BAC", "V", "MA", "ORCL", "CRM", "ADBE", "INTC",
        "SMCI", "ARM", "MU", "SHOP", "UBER"
    ]

    CRYPTO: List[str] = [
        "BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT",
        "ADA/USDT", "LINK/USDT", "AVAX/USDT", "SUI/USDT", "BNB/USDT",
        "TRX/USDT", "DOT/USDT", "LTC/USDT", "BCH/USDT", "UNI/USDT",
        "ATOM/USDT", "APT/USDT", "NEAR/USDT", "ARB/USDT", "OP/USDT",
        "HEX/USDT", "PLS/USDT", "PLSX/USDT", "HAC/USDT", "HACD/USDT"
    ]

    # Validation
    def validate(self):
        missing = []
        if not self.TELEGRAM_BOT_TOKEN:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not self.TELEGRAM_CHAT_ID:
            missing.append("TELEGRAM_CHAT_ID")
        if not self.FINNHUB_API_KEY:
            missing.append("FINNHUB_API_KEY")
        if not self.TAVILY_API_KEY:
            missing.append("TAVILY_API_KEY")
        if not self.FINLIGHT_API_KEY:
            missing.append("FINLIGHT_API_KEY")
        # MORALIS_API_KEY is optional (free tier bonus for richer PulseChain data in chain_analysis_expert)

        if missing:
            raise ValueError(f"❌ Missing required keys in .env: {', '.join(missing)}")


# Global instance (validate on import — required keys must be present in .env)
config = Config()
config.validate()
