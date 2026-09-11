"""The model call. gemma-4 through llama.cpp, tools on, thinking off.

One function does the work: `turn()` takes the conversation so far and the
tool registry, asks the model, and returns either text to speak or a list of
tool calls to run. The agent loop in agent.py decides what to do with tool
calls (that is where the safety gate lives) and calls back in with results.

Language: the system prompt tells the model to answer in the language the
owner spoke. Whisper detects that per utterance (measured 0.99+), and the
detected code is passed in as a hint so a mixed sentence still gets a
consistent reply.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

from . import config

SYSTEM_PROMPT = """Είσαι ο προσωπικός βοηθός του χρήστη — επαγγελματίας, άμεσος, με φυσικά ελληνικά όπως τα μιλάει ένας Έλληνας, και άψογα αγγλικά όταν σου μιλούν αγγλικά. Απαντάς ΠΑΝΤΑ στη γλώσσα που μίλησε ο χρήστης στην τελευταία του φράση.

Μιλάς, δεν γράφεις: οι απαντήσεις σου θα ΕΚΦΩΝΗΘΟΥΝ. Άρα:
- σύντομες προτάσεις, χωρίς λίστες, χωρίς markdown, χωρίς σύμβολα, χωρίς κώδικα στην απάντηση·
- ώρες με λέξεις («έντεκα και είκοσι»)· ημερομηνίες, έτη και μεγάλους αριθμούς ΜΕ ΨΗΦΙΑ («11 Σεπτεμβρίου 2026», «1.250 ευρώ») — ποτέ μην γράφεις έτη ολογράφως·
- γράφεις ΜΟΝΟ ελληνικά ή αγγλικά· ποτέ άλλες γραφές ή αλφάβητα·
- μία έως τρεις προτάσεις εκτός αν ζητηθεί περισσότερο.

Έχεις εργαλεία. Όταν ο χρήστης ζητά κάτι που απαιτεί ενέργεια ή πληροφορία που δεν έχεις, ΚΑΛΕΙΣ το κατάλληλο εργαλείο αντί να μαντεύεις. Αν κάτι μπορεί να πάει στραβά — λάθος αρχείο, διφορούμενη εντολή, ενέργεια που δεν αναιρείται — το ΛΕΣ πριν το κάνεις, καθαρά και σύντομα. Δεν κρύβεις αποτυχίες: αν ένα εργαλείο απέτυχε, το λες ακριβώς.

Ποτέ δεν ισχυρίζεσαι ότι έκανες κάτι που δεν έκανες."""


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class Reply:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw_message: dict = field(default_factory=dict)
    seconds: float = 0.0
    tokens: int = 0


class LLMError(RuntimeError):
    pass


def _post(body: dict) -> dict:
    req = urllib.request.Request(
        config.LLM_BASE_URL + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {config.LLM_API_KEY}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=config.LLM_TIMEOUT_S) as r:
            return json.load(r)
    except urllib.error.URLError as e:
        raise LLMError(f"the model server is not answering at {config.LLM_BASE_URL}: {e.reason}") from e


def turn(messages: list[dict], tool_schemas: list[dict], lang_hint: Optional[str] = None) -> Reply:
    import time
    sys_prompt = SYSTEM_PROMPT
    if lang_hint == "en":
        sys_prompt += "\n\n(The user is speaking English right now. Answer in English.)"
    elif lang_hint == "el":
        sys_prompt += "\n\n(Ο χρήστης μιλάει ελληνικά τώρα. Απάντησε στα ελληνικά.)"

    body = {
        "model": config.LLM_MODEL,
        "messages": [{"role": "system", "content": sys_prompt}] + messages,
        "temperature": config.LLM_TEMPERATURE,
        "max_tokens": config.LLM_MAX_TOKENS,
        # MEASURED: thinking ON ate the whole budget in reasoning_content and
        # left a seven-word answer. See config.py.
        "chat_template_kwargs": {"enable_thinking": config.LLM_THINKING},
    }
    if tool_schemas:
        body["tools"] = tool_schemas
        body["tool_choice"] = "auto"

    t0 = time.perf_counter()
    data = _post(body)
    dt = time.perf_counter() - t0

    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    calls = []
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function") or {}
        args_raw = fn.get("arguments") or "{}"
        try:
            args = json.loads(args_raw) if isinstance(args_raw, str) else dict(args_raw)
        except json.JSONDecodeError:
            args = {"_raw": args_raw}
        calls.append(ToolCall(tc.get("id") or fn.get("name", "call"), fn.get("name", ""), args))

    text = (msg.get("content") or "").strip()
    # If the parser missed a native tool-call and it leaked as text, do not
    # SPEAK the markup at the owner. Say so instead. (Seen once with Qwen.)
    if re.search(r"<\|?tool_call|<function=|</tool_call", text):
        text = ""
        if not calls:
            calls.append(ToolCall("unparsed", "_unparsed_tool_call", {"raw": msg.get("content", "")[:300]}))

    return Reply(text=text, tool_calls=calls, raw_message=msg, seconds=dt,
                 tokens=int((data.get("usage") or {}).get("completion_tokens") or 0))


def strip_for_speech(text: str) -> str:
    """The model was told not to emit markup; make sure none reaches the
    voice anyway. Bullets, code fences, bold, links, emoji-ish symbols."""
    t = re.sub(r"```.*?```", " ", text, flags=re.S)
    t = re.sub(r"`([^`]*)`", r"\1", t)
    t = re.sub(r"\*\*(.+?)\*\*|\*(.+?)\*|__(.+?)__", lambda m: next(g for g in m.groups() if g), t)
    t = re.sub(r"^\s*[-*•]\s+", "", t, flags=re.M)
    t = re.sub(r"^\s*\d+\.\s+", "", t, flags=re.M)
    t = re.sub(r"#+\s*", "", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"[\U0001F300-\U0001FAFF☀-➿]", "", t)
    # MEASURED: asked to say a year in words, gemma emitted Tamil and Cyrillic
    # inside Greek ("του இரண்டтисяν"). A character outside Greek, Latin,
    # digits and ordinary punctuation is always a glitch in speech; drop it.
    t = re.sub(r"[^\t\n\r\x20-\u024F\u0370-\u03FF\u1F00-\u1FFF\u2000-\u206F\u20AC]", "", t)
    return " ".join(t.split())


def detect_lang(text: str) -> str:
    """Greek if the text is mostly Greek letters; used to pick the TTS voice
    for the REPLY, which may not match the question's language."""
    greek = sum(1 for c in text if "Ͱ" <= c <= "Ͽ" or "ἀ" <= c <= "῿")
    latin = sum(1 for c in text if c.isascii() and c.isalpha())
    return "el" if greek >= latin else "en"


def split_sentences(text: str) -> list[str]:
    """For speaking as the model finishes each sentence. Greek question mark
    is ';', which also ends clauses in English text - so we split on it only
    when followed by space and a capital, and on . ! ? normally."""
    parts = re.split(r"(?<=[.!?])\s+|(?<=;)\s+(?=[Α-ΩA-Z])", text.strip())
    return [p for p in parts if p]
