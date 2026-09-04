"""
Thin backward-compatible wrapper.
All existing call sites (ai_commentary_engine, ai_advisor_engine, macro_tech_report, etc.)
continue to work unchanged. The real work is now in llm_client.py (primary = llama.cpp).
"""

from llm_client import generate_market_report, chat, chat_messages, legacy_ollama_check  # re-export for convenience

# Keep the old function name + signature exactly as before for zero-breakage imports.
# The implementation now routes through the modern OpenAI-compatible client (llama.cpp on :8080).
__all__ = ["generate_market_report", "chat", "chat_messages", "legacy_ollama_check"]