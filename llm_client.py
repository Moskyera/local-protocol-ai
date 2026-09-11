"""
Unified LLM Client for MOSKY AI Workstation
Primary: llama.cpp (OpenAI-compatible) on :8080 via Vulkan (gemma-4-26b-qat QAT MoE on RX 9070 XT)
No legacy Ollama in main boot path (voice support removed per requirements).

This replaces scattered direct requests throughout the codebase.
"""

import os
import re
from typing import Optional, List, Dict, Any
import httpx
from openai import OpenAI
from config import config
from logger import log

#: Bounded per-request timeout (connect, read). See get_llm_client().
LLM_TIMEOUT = httpx.Timeout(connect=10.0, read=300.0, write=60.0, pool=60.0)

#: Returned (NOT raised) when the backend fails. Callers that render text to
#: users must check with is_llm_error() — otherwise this string is displayed as
#: if it were a real report.
LLM_ERROR_SENTINEL = "(LLM error - check llama-server logs)"

#: Marks recovered scratchpad text. Real words from the model, but its working
#: notes rather than a finished answer — labelled so it is never passed off as one.
LLM_DRAFT_PREFIX = "⚠️ (πρόχειρες σημειώσεις του μοντέλου, όχι τελική απάντηση)"

#: Appended when the model was still writing at the token limit. Without it a
#: chapter summary that stops mid-sentence reads as if the model had nothing
#: more to say. Measured: a 22-page story came back as 1109 characters ending
#: in "...είναι η" under a confident header.
LLM_TRUNCATED_SUFFIX = "\n\n⚠️ (η απάντηση κόπηκε στο όριο tokens — ζήτησε τη συνέχεια)"

#: Every failure string this repo generates. Anything starting with one of these
#: is a sentinel, not content. Kept as a tuple so adding a new one is one line.
_ERROR_PREFIXES = (
    "(LLM error",
    "(model returned thinking only",
    "(expert '",                      # expert_base.consult failure
    "(Legacy Ollama support has been removed",
)


#: Two of the five failure sentinels this repo generates cannot be matched by a
#: fixed prefix, because they begin with the agent's ROLE:
#:
#:     "(coder agent LLM error: ...)"          base_llm_agent.py:97
#:     "(LLM backend unavailable for coder agent: ...)"   base_llm_agent.py:82
#:
#: _ERROR_PREFIXES caught neither, so every v2 agent's backend failure — coder,
#: reviewer, tester, debugger, security — passed is_llm_error() as if it were a
#: real answer, and callers that gate on it published the sentinel as content.
_ERROR_RE = re.compile(
    r"^\((?:LLM backend unavailable for |[\w\-]{1,40} agent LLM error:)")


def is_llm_error(text: str) -> bool:
    """True when `text` is a failure sentinel rather than real model output."""
    t = (text or "").strip()
    return (not t) or t.startswith(_ERROR_PREFIXES) or bool(_ERROR_RE.match(t))


def is_llm_draft(text: str) -> bool:
    """True when `text` is the model's scratchpad, recovered but not an answer.

    Deliberately NOT folded into is_llm_error(): a draft is real model text, and
    a caller rendering it with its warning intact is behaving correctly. What
    must never happen is a draft being cached forever or merged into a summary
    as though it were a finished note.
    """
    return (text or "").strip().startswith(LLM_DRAFT_PREFIX)


def is_usable(text: str) -> bool:
    """True only for text safe to store or merge as real content."""
    return not is_llm_error(text) and not is_llm_draft(text)

# --- Primary client (llama.cpp server - recommended for all new code) ---
#: A second backend, for a model that does not have to share the GPU.
#: 16GB fits ONE model on the card, but the box has 61.6GB of RAM and 16 CPU
#: cores sitting idle while llama-server works. A small specialist (e.g. a Greek
#: model for the final rendering pass) can run there on its own port at the same
#: time, so nothing has to be swapped mid-pipeline. Empty = not configured.
SECONDARY_BASE_URL = os.getenv("MOSKY_LLM2_URL", "").strip()


def get_llm_client(base_url: Optional[str] = None) -> OpenAI:
    """Returns OpenAI client configured for the reliable llama.cpp backend.

    `base_url` selects a specific backend. Without it, the primary one is used.
    Routing MUST be by URL, not by model name: llama-server answers with
    whatever GGUF it has loaded and ignores the `model` field entirely.
    """
    import lpai_private
    base_url = lpai_private.require_local_endpoint(base_url or getattr(config, "OPENAI_BASE_URL",
                                   "http://127.0.0.1:8080/v1"))
    api_key = getattr(config, "OPENAI_API_KEY", "sk-dummy-local")
    # Bound the call. The openai SDK default read timeout is 600s, so a hung or
    # mid-swap llama-server would stall each briefing section for 10 minutes
    # (up to an hour for the 6-message run) before anyone noticed.
    # 300s is comfortably above a full 8k-token local generation.
    return OpenAI(base_url=base_url, api_key=api_key,
                  timeout=LLM_TIMEOUT, max_retries=1)


_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def _extract_text(choice) -> tuple:
    """Pull the model's words out of a choice. Returns (text, source).

    llama.cpp splits reasoning models into `reasoning_content` + `content`. When
    generation is cut off at max_tokens the model never emits the marker that
    closes reasoning, so the ENTIRE answer stays in `reasoning_content` and
    `content` comes back "". Measured with gemma-4-26b-qat: every DocAnalyst
    chapter died on "(model returned thinking only)" while a correct Greek
    answer sat in the discarded field.

    `source` lets the caller tell a real answer from the model's scratchpad —
    handing scratchpad notes to a user as if they were the summary is exactly
    the kind of fake output this system is supposed to be rid of.
    """
    msg = choice.message
    content = _THINK_RE.sub("", msg.content or "").strip()
    if content:
        return content, "content"

    reasoning = _THINK_RE.sub("", getattr(msg, "reasoning_content", "") or "").strip()
    if reasoning:
        return reasoning, "reasoning"

    return "", "empty"


#: A truncated reasoning block is a budget problem, not a model failure. Retry
#: once with room to actually finish; 3x was measured to be enough for gemma.
#: The cap must stay ABOVE the default max_tokens or the retry is dead code —
#: it was, at 8192 against a default of 8192. Server runs -c 65536 --parallel 1,
#: so the whole context belongs to one request.
_RETRY_TOKEN_FACTOR = 3
#: (asked, served) pairs already reported. See the MODEL MISMATCH block.
_MISMATCH_SEEN = set()

_RETRY_TOKEN_CAP = 16384


def chat(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 8192,
    system_prompt: Optional[str] = None,
    thinking: bool = False,
    grammar: Optional[str] = None,
    sampling: Optional[Dict[str, Any]] = None,
    base_url: Optional[str] = None,
) -> str:
    """
    Primary chat interface using the llama.cpp OpenAI-compatible endpoint.
    This is the recommended way for all market reports, commentary, advisor, etc.

    thinking: gemma's reasoning channel. OFF by default, and that is a measured
        decision, not a preference. With it on, a 300-token budget produced 895
        characters of scratchpad and ZERO answer (finish_reason='length'); with
        it off the same prompt produced a complete 613-character answer using
        FEWER tokens (234 vs 300). Every answer this repo lost to "(model
        returned thinking only)" was this. Callers that genuinely want the model
        to deliberate can pass thinking=True together with a large max_tokens.
    grammar: GBNF passed straight to llama.cpp. This is the only mechanism that
        can suppress a wrong token the model ranks FIRST — measured: the ' lạ'
        fragment corrupting Greek output was the argmax, so min_p/top_k cannot
        touch it by construction, and tightening them made corruption worse
        (1.89 vs 0.86 foreign chars per 1000). A grammar took it to zero.
    sampling: extra sampler knobs (top_k, min_p, repeat_penalty, ...). Nothing
        was ever passed before, so output silently followed server defaults.
    base_url: send this call to a DIFFERENT llama-server. Only 16GB of VRAM is
        available, so the GPU holds one model — but a second server can serve a
        small specialist from RAM on another port, and then a pipeline can use
        both without swapping anything. Routing must be by URL: the `model`
        field is ignored by llama-server.
    """
    client = get_llm_client(base_url)
    model_name = model or getattr(config, "LLM_MODEL", "gemma-4-26b-qat")

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    extra: Dict[str, Any] = {"chat_template_kwargs": {"enable_thinking": thinking}}
    if grammar:
        extra["grammar"] = grammar
    if sampling:
        extra.update(sampling)

    def _ask(budget: int):
        return client.chat.completions.create(
            model=model_name, messages=messages, temperature=temperature,
            max_tokens=budget, extra_body=extra,
        )

    try:
        resp = _ask(max_tokens)
        # The server answers with WHATEVER model is loaded and ignores the name
        # we asked for. Verified: asked "gemma-4-26b-qat" while qwen3-coder was
        # loaded -> HTTP 200, answered by qwen. Without this warning a briefing
        # generated by the coding model looks completely normal.
        served = getattr(resp, "model", None)
        # Not a mismatch when the caller deliberately picked a second backend —
        # it holds a different model on purpose, that is the whole point.
        if base_url is None and served and model_name and served != model_name:
            # Once per (asked, served) pair, not once per call. Every skill with
            # USE_CODING_MODEL=True asks for CODING_MODEL, and only one model
            # fits on this card at a time (gemma 15.84 GB, qwen3-coder 16.5 GB,
            # 16 GB of VRAM), so in normal single-server operation this fires on
            # EVERY coding call. A warning that appears hundreds of times per
            # run is one nobody reads — including the time it means something
            # else, like a briefing quietly generated by the coding model.
            key = (model_name, served)
            if key not in _MISMATCH_SEEN:
                _MISMATCH_SEEN.add(key)
                log.warning(
                    f"[LLM] MODEL MISMATCH: asked for '{model_name}' but the "
                    f"server is serving '{served}', and llama.cpp ignores the "
                    f"model field — every request in this process will be "
                    f"answered by '{served}'. Both models are ~16 GB and the "
                    f"card holds 16 GB, so only one can be loaded: restart with "
                    f"the other launcher if you need it. Logged once."
                )

        text, source = _extract_text(resp.choices[0])
        cut = resp.choices[0].finish_reason == "length"

        # Retry whenever the model was still writing at the limit — NOT only
        # when it produced nothing. A summary that stops mid-sentence is just as
        # broken as an empty one, and the old check skipped it entirely because
        # it returned on `source == "content"` before ever reading finish_reason.
        bigger = min(_RETRY_TOKEN_CAP, max_tokens * _RETRY_TOKEN_FACTOR)
        if cut and bigger > max_tokens:
            log.warning(f"[LLM] answer truncated at {max_tokens} tokens "
                        f"(channel={source}); retrying once with {bigger}")
            try:
                resp2 = _ask(bigger)
                text2, source2 = _extract_text(resp2.choices[0])
                cut2 = resp2.choices[0].finish_reason == "length"
                # Adopt the retry only if it is genuinely better. Overwriting
                # unconditionally would throw away good text whenever the second
                # call came back empty — reintroducing the bug being fixed here,
                # after paying for two generations.
                better = (source2 == "content" and source != "content") or \
                         (source2 != "empty" and not cut2)
                if better:
                    text, source, cut = text2, source2, cut2
            except Exception as e:
                log.warning(f"[LLM] retry failed, keeping first answer: {e}")

        if source == "content":
            return text + (LLM_TRUNCATED_SUFFIX if cut else "")

        if source == "reasoning":
            # It never left the reasoning channel. The text is real, so return
            # it — labelled, so nobody mistakes notes for a finished answer.
            log.warning("[LLM] model stayed in the reasoning channel; returning "
                        "its notes marked as draft")
            return f"{LLM_DRAFT_PREFIX}\n\n{text}"

        return "(model returned thinking only; try a more specific prompt)"
    except Exception as e:
        log.error(f"[LLM] Primary backend error (llama.cpp @ {config.OPENAI_BASE_URL}): {e}")
        return LLM_ERROR_SENTINEL


def chat_messages(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 8192,
) -> str:
    """Lower level messages interface (for voice with history etc.)."""
    client = get_llm_client()
    model_name = model or getattr(config, "LLM_MODEL", "gemma-4-26b-qat")
    try:
        resp = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        text, source = _extract_text(resp.choices[0])
        if source == "reasoning":
            return f"{LLM_DRAFT_PREFIX}\n\n{text}"
        if source == "content" and resp.choices[0].finish_reason == "length":
            return text + LLM_TRUNCATED_SUFFIX
        return text or "(model returned thinking only; try a more specific prompt)"
    except Exception as e:
        log.error(f"[LLM] Primary backend (messages) error: {e}")
        # Fallback: convert last user message
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        return _legacy_ollama_chat(last_user, model=model, temperature=temperature)


# (Legacy Ollama support removed from main path; this stub is kept only for any remaining example scripts that import it.
# All main code now uses the primary client exclusively.)
def _legacy_ollama_chat(*args, **kwargs):
    return "(Legacy Ollama support has been removed from the boot system.)"


def legacy_ollama_check() -> bool:
    """Quick health check for the legacy Ollama (used by voice launchers)."""
    import urllib.request
    ollama_url = os.getenv("OLLAMA_URL", getattr(config, "OLLAMA_URL", "http://127.0.0.1:11434"))
    try:
        with urllib.request.urlopen(f"{ollama_url.rstrip('/')}/api/tags", timeout=4) as resp:
            return resp.status == 200
    except Exception:
        return False


# --- Convenience for old call sites ---
def generate_market_report(prompt: str) -> str:
    """
    Backward compatible wrapper.
    All existing imports (ai_commentary_engine, ai_advisor_engine, macro_tech_report, etc.)
    will continue to work without changes.
    """
    return chat(prompt, temperature=0.7, max_tokens=8192)


# Optional: simple test when run directly
if __name__ == "__main__":
    print("Testing primary LLM client (llama.cpp)...")
    reply = chat("Say hello in one short professional sentence.")
    print("Reply:", reply[:200])