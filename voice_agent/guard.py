"""The safety gate: nothing risky happens without the owner saying so, aloud.

Every tool the agent can call is assigned a risk class BEFORE it is exposed
to the model. The class decides what happens when the model asks for it:

  SAFE         run it, say the result.
  RISKY        say what is about to happen in one sentence, then run it. The
               owner can interrupt. Used for things that change state but are
               reversible: writing a file, opening an app, a network call.
  DESTRUCTIVE  say exactly what will happen, name the target, and STOP until
               the owner confirms with a spoken phrase. Deleting, sending
               anything to anyone, paying, creating pull requests, applying
               self-improvement proposals, and any shell command.

The confirmation is a PHRASE, never a word. Measured: whisper transcribes
"Ναι"/"Όχι" alone wrongly more often than not ("Ναι" -> "Ευχαριστώ",
"Όχι" -> "Ποια"), and correctly every time at two or more words. So the agent
asks for "ναι, συνέχισε" or "όχι, ακύρωσέ το", matches the answer fuzzily
against a small set, and re-asks when it is unsure. Silence is a refusal.

The classification is by NAME PATTERN and by an explicit table, and it is
deliberately pessimistic: an unknown tool is RISKY, and any name containing a
destructive verb is DESTRUCTIVE no matter what its description says.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from . import config


class Risk(str, Enum):
    SAFE = "safe"
    RISKY = "risky"
    DESTRUCTIVE = "destructive"


# Verbs that make a tool destructive whatever else it says about itself.
_DESTRUCTIVE_PATTERNS = re.compile(
    r"(delete|remove|\brm(?:\b|_)|erase|wipe|purge|drop|destroy|format|"
    r"send|post|publish|email|telegram|tweet|message|"
    r"pay|transfer|withdraw|buy|sell|trade|order|"
    r"create_pr|apply_proposal|approve|rollback|"
    r"shell|bash|exec|run_command|execute|kill|shutdown|reboot|"
    r"install|uninstall|chmod|chown|sudo)",
    re.I,
)

# Read-only by name. Only these prefixes are SAFE without an explicit entry.
_SAFE_PATTERNS = re.compile(
    r"^(get_|read_|list_|search|find|lookup|fetch_|query|check_|analyze|"
    r"analyse|scan_|research|what_|show_|describe|summar|x_semantic|x_keyword|"
    r"x_thread|get_market|get_system|get_meta|get_research|get_proposal|"
    r"consult_|safe_web|web_research)",
    re.I,
)

# Explicit table wins over patterns. Add here when a name misleads.
EXPLICIT: dict[str, Risk] = {
    "generate_image": Risk.RISKY,        # writes files, uses the GPU
    "generate_video": Risk.RISKY,
    "fix_tool_call_error": Risk.SAFE,
    "list_pending_proposals": Risk.SAFE,
    "evaluate_and_rollback_if_degraded": Risk.DESTRUCTIVE,
    "integrate_research_idea": Risk.DESTRUCTIVE,   # edits the codebase
    "improve_the_blockchain_expert": Risk.DESTRUCTIVE,
    "propose_blockchain_improvements_from_lab": Risk.RISKY,
    "run_scheduled_proactive_research": Risk.RISKY,
    "supervise": Risk.RISKY,
    "execute_v2_task": Risk.DESTRUCTIVE,           # runs agents that write
    "mcp_github_context": Risk.RISKY,
    # local tools (tools.py)
    "current_time": Risk.SAFE,
    "read_clipboard": Risk.SAFE,
    "read_file": Risk.SAFE,
    "list_folder": Risk.SAFE,
    "write_note": Risk.RISKY,
    "open_path": Risk.RISKY,
    "run_command": Risk.DESTRUCTIVE,
}


def classify(tool_name: str) -> Risk:
    if tool_name in EXPLICIT:
        return EXPLICIT[tool_name]
    if _DESTRUCTIVE_PATTERNS.search(tool_name):
        return Risk.DESTRUCTIVE
    if _SAFE_PATTERNS.search(tool_name):
        return Risk.SAFE
    return Risk.RISKY          # unknown: announce before acting


# --------------------------------------------------------------------------- #
# Spoken confirmation
# --------------------------------------------------------------------------- #

def _norm(text: str) -> str:
    """Lowercase, strip accents and punctuation. "Ναι, συνέχισε!" and
    "ναι συνεχισε" must compare equal; whisper's punctuation is not ours."""
    t = unicodedata.normalize("NFD", text.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^\w\s]", " ", t)
    return " ".join(t.split())


@dataclass
class Verdict:
    decision: Optional[bool]     # True = confirmed, False = denied, None = unclear
    matched: str = ""
    score: float = 0.0


def interpret_confirmation(transcript: str) -> Verdict:
    """Was that a yes, a no, or neither? Both languages, fuzzy, phrase-only."""
    said = _norm(transcript)
    if len(said.split()) < 2:
        # a single word is rejected on principle - see the module docstring
        return Verdict(None, said, 0.0)

    best: Verdict = Verdict(None, "", 0.0)
    for lang in ("el", "en"):
        for phrase in config.CONFIRM_PHRASES[lang]:
            s = difflib.SequenceMatcher(None, _norm(phrase), said).ratio()
            if s > best.score:
                best = Verdict(True, phrase, s)
        for phrase in config.DENY_PHRASES[lang]:
            s = difflib.SequenceMatcher(None, _norm(phrase), said).ratio()
            if s > best.score:
                best = Verdict(False, phrase, s)

    # A denial word anywhere overrides a fuzzy yes: "όχι ... συνέχισε" is a no.
    if re.search(r"\b(οχι|no|not|μην|ακυρωσ|cancel|stop|σταματ)\w*", said):
        return Verdict(False, best.matched, max(best.score, 0.99))

    if best.score < config.CONFIRM_MATCH_THRESHOLD:
        return Verdict(None, best.matched, best.score)
    return best


# --------------------------------------------------------------------------- #
# What the agent says, per class, per language
# --------------------------------------------------------------------------- #

def announce(risk: Risk, tool_name: str, arguments: dict, lang: str) -> str:
    """The sentence spoken before a RISKY or DESTRUCTIVE tool runs."""
    target = _describe_target(arguments)
    if lang == "el":
        if risk is Risk.DESTRUCTIVE:
            return (f"Προσοχή. Θα εκτελέσω {_greek_tool(tool_name)}{target}. "
                    f"Αυτό δεν αναιρείται εύκολα. "
                    f"Πες «ναι, συνέχισε» για να προχωρήσω, ή «όχι, ακύρωσέ το».")
        return f"Εκτελώ {_greek_tool(tool_name)}{target}."
    if risk is Risk.DESTRUCTIVE:
        return (f"Careful. I am about to run {tool_name.replace('_', ' ')}{target}. "
                f"This is hard to undo. Say \"yes, go ahead\" to continue, or \"no, cancel it\".")
    return f"Running {tool_name.replace('_', ' ')}{target}."


def _describe_target(arguments: dict) -> str:
    for key in ("path", "file", "folder", "repo", "address", "url", "command", "symbol", "query", "prompt"):
        if key in arguments and arguments[key]:
            v = str(arguments[key])
            return f" — {v[:80]}" if len(v) <= 80 else f" — {v[:77]}…"
    return ""


_GREEK_NAMES = {
    "delete_folder": "διαγραφή φακέλου", "run_command": "εντολή τερματικού",
    "create_pr": "δημιουργία pull request", "apply_proposal": "εφαρμογή πρότασης",
    "approve_and_apply_proposal": "έγκριση και εφαρμογή πρότασης",
    "rollback_proposal": "αναίρεση πρότασης", "execute_v2_task": "εκτέλεση εργασίας agents",
    "write_note": "εγγραφή σημείωσης", "open_path": "άνοιγμα αρχείου",
    "generate_image": "δημιουργία εικόνας", "generate_video": "δημιουργία βίντεο",
}


def _greek_tool(name: str) -> str:
    return _GREEK_NAMES.get(name, name.replace("_", " "))
