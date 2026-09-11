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
    EGRESS = "egress"          # sends the owner's words or data OFF this machine
    DESTRUCTIVE = "destructive"


# Verbs that make a tool destructive whatever else it says about itself.
# Anchored to word pieces: MEASURED, the unanchored version made
# list_skills, get_information, get_order_book, read_messages and
# check_installed_packages "destructive" (kill, format, order, message,
# install as substrings).
_DESTRUCTIVE_PATTERNS = re.compile(
    r"(?:^|_)(delete|remove|rm|erase|wipe|purge|drop|destroy|format|"
    r"send|post|publish|email|telegram|tweet|message|"
    r"pay|transfer|withdraw|buy|sell|trade|order|"
    r"create_pr|apply_proposal|approve|rollback|"
    r"shell|bash|exec|run_command|execute|kill|shutdown|reboot|"
    r"install|uninstall|chmod|chown|sudo)(?:_|$)",
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
    "read_notes": Risk.SAFE,
    "recall": Risk.SAFE,
    "get_system_status": Risk.SAFE,
}


# "order", "message", "post", "trade", "format" are verbs AND nouns: after a
# read-only prefix they are the noun (get_order_book, read_messages).
_NOUNISH = {"order", "message", "post", "trade", "format", "transfer"}
_READ_PREFIX = re.compile(r"^(get|read|list|show|check|describe|fetch|lookup|query|search|find)_", re.I)


def classify(tool_name: str) -> Risk:
    if tool_name in EXPLICIT:
        return EXPLICIT[tool_name]
    m = _DESTRUCTIVE_PATTERNS.search(tool_name)
    if m and not (m.group(1).lower() in _NOUNISH and _READ_PREFIX.match(tool_name)):
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


# MEASURED 2026-09-11 (adversarial rows against the first version): a plain
# difflib match with no affirmative requirement accepted "δεν είμαι σίγουρος"
# (I am NOT sure) as a yes at 0.89, "μη συνεχίσεις" at 0.72, fragments like
# "και συνέχισε" at 0.92 and deferrals like "yes do it later" at 0.75 - while
# the old denial regex \bno\w* turned "yes go ahead now" into a NO because of
# "now". Three rules fix all of it, every remaining change is in the safe
# direction (yes -> re-ask), and the call costs under 1 ms.
_NEGATION = re.compile(
    r"\b(οχι|δε|δεν|μη|μην|τιποτα|no|nope|not|never|nothing|none|don|dont|wont|forget)\b"
    r"|\b(ακυρωσ|σταματ|ξεχασ|cancel|stop)\w*"
    r"|\b(ασ το|ασε το|αστο)\b")
# a time word is a decline of THIS request ("κάντο αύριο"); hesitation is unclear
_DEFER = re.compile(r"\b(αργοτερα|αυριο|later|tomorrow)\b")
_HESITATE = re.compile(r"\b(περιμενε|μισο|wait|hold)\b")
# a yes must contain a yes-word somewhere; bare verbs ("και συνέχισε") do not count
_AFFIRM = re.compile(
    r"\b(ναι|ενταξει|βεβαιως|ασφαλως|σιγουρα|φυσικα|αμε|συμφωνοι|μαλιστα|yes|yeah|yep|ok|okay|"
    r"συνεχισε κανονικα|go ahead and do it)\b")
# a yes-word plus an action verb is a yes even when it resembles no listed
# phrase: "ασφαλώς, συνέχισε" scored 0.71 against "ναι συνέχισε" and was re-asked
_ACTION = re.compile(r"\b(συνεχισ\w*|προχωρ\w*|καντο|κανε το|τρεξε|go ahead|do it|continue|proceed|run it)\b")


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
    if _NEGATION.search(said):
        return Verdict(False, best.matched, max(best.score, 0.99))
    if _DEFER.search(said):
        return Verdict(False, best.matched, max(best.score, 0.99))
    if _HESITATE.search(said):
        return Verdict(None, best.matched, best.score)

    if best.score < config.CONFIRM_MATCH_THRESHOLD:
        if _AFFIRM.search(said) and _ACTION.search(said):
            return Verdict(True, best.matched, max(best.score, config.CONFIRM_MATCH_THRESHOLD))
        return Verdict(None, best.matched, best.score)
    if best.decision is True and not _AFFIRM.search(said):
        return Verdict(None, best.matched, best.score)
    return best


def is_exit(transcript: str, lenient: bool = False) -> bool:
    """A spoken goodbye. Two words or more, fuzzy, like a confirmation
    (MEASURED: every one-word exit is under 1.2 s and 'Τέλος για σήμερα'
    1.47 s came back exact). `lenient` also accepts the single words, for
    the keyboard."""
    said = _norm(transcript)
    if lenient and said in {"exit", "quit", "τελος", "εξοδος", "κλεισε", "αντιο", "goodbye", "bye"}:
        return True
    if len(said.split()) < 2:
        return False
    for lang in ("el", "en"):
        for phrase in config.EXIT_PHRASES[lang]:
            if difflib.SequenceMatcher(None, _norm(phrase), said).ratio() >= config.EXIT_MATCH_THRESHOLD:
                return True
    return False


# --------------------------------------------------------------------------- #
# What the agent says, per class, per language
# --------------------------------------------------------------------------- #

# MEASURED 2026-09-11 (Piper -> whisper): the old one-sentence announcement
# 'Θα εκτελέσω διαγραφή φακέλου — C:/Users/you/Documents/old_project.'
# went to the ENGLISH voice (more Latin than Greek letters) and came back
# as Greek letter names, 13.3 s, CER 278%; through the Greek voice the path
# was lost (CER 56%). Split into units - the Greek frame in the Greek voice
# ('Θα διαγράψω τον φάκελο:' CER 0%) and the target words in the English
# voice ('old project, inside Documents.' CER 0%) - it is 4.1 s and exact.
# 'Προσοχή.' alone was unintelligible 0/5; as one clause 'Προσοχή, θα ...'
# 5/5. The guillemet phrase 'Πες «ναι, συνέχισε»' lost its pause; the
# colon form 'Για να προχωρήσω πες: ναι, συνέχισε.' was 5/5.

_EL_FRAMES = {
    "delete_folder": "θα διαγράψω τον φάκελο:", "delete_file": "θα διαγράψω το αρχείο:",
    "run_command": "θα τρέξω στο τερματικό:", "execute_v2_task": "θα βάλω τους agents να δουλέψουν σε:",
    "create_pr": "θα δημιουργήσω pull request:", "apply_proposal": "θα εφαρμόσω την πρόταση:",
    "approve_and_apply_proposal": "θα εγκρίνω και θα εφαρμόσω την πρόταση:",
    "rollback_proposal": "θα αναιρέσω την πρόταση:", "integrate_research_idea": "θα ενσωματώσω στον κώδικα την ιδέα:",
    "evaluate_and_rollback_if_degraded": "θα αξιολογήσω και ίσως αναιρέσω:",
    "improve_the_blockchain_expert": "θα αλλάξω τον κώδικα του blockchain expert:",
    "write_note": "κρατάω σημείωση.", "open_path": "ανοίγω το εξής:", "generate_image": "φτιάχνω εικόνα για:",
    "web_research": "θα κατεβάσω από το ίντερνετ τη σελίδα:", "research": "θα ψάξω στο GitHub και στο arXiv για:",
    "analyze_wallet": "θα στείλω σε υπηρεσία blockchain τη διεύθυνση:", "fetch_full_wallet_profile": "θα στείλω σε υπηρεσία blockchain τη διεύθυνση:",
    "check_large_ecosystem_movements": "θα ελέγξω στο δίκτυο τη διεύθυνση:", "get_market_context": "θα ζητήσω τιμές από το ίντερνετ.",
    "scan_large_ecosystem_movements_on_pulsechain": "θα σαρώσω το PulseChain για μεγάλες κινήσεις.",
    "scan_and_research_large_ecosystem_movements": "θα σαρώσω το PulseChain και θα ερευνήσω τις κινήσεις.",
    "consult_wealth_mentor": "ρωτάω τον σύμβουλο:",
    "generate_video": "φτιάχνω βίντεο για:", "send_telegram": "θα στείλω μήνυμα στο Telegram:",
    "supervise": "βάζω τον επόπτη να δουλέψει σε:", "run_scheduled_proactive_research": "ξεκινάω έρευνα για:",
    "propose_blockchain_improvements_from_lab": "ετοιμάζω προτάσεις από το εργαστήριο.",
    "mcp_github_context": "διαβάζω από το GitHub:",
}
_EN_FRAMES = {
    "delete_folder": "I will delete the folder:", "delete_file": "I will delete the file:",
    "run_command": "I will run in the terminal:", "execute_v2_task": "I will put the agents to work on:",
    "create_pr": "I will create a pull request:", "apply_proposal": "I will apply the proposal:",
    "approve_and_apply_proposal": "I will approve and apply the proposal:",
    "rollback_proposal": "I will roll back the proposal:", "write_note": "Taking a note.",
    "open_path": "Opening this:", "generate_image": "Making an image of:", "generate_video": "Making a video of:",
    "web_research": "I will fetch from the internet the page:", "research": "I will search GitHub and arXiv for:",
    "analyze_wallet": "I will send to a blockchain service the address:", "get_market_context": "I will fetch prices from the internet.",
    "consult_wealth_mentor": "Asking the mentor:",
}
_EGRESS_TAIL = {
    "el": "Αυτό φεύγει από το μηχάνημα. Για να το στείλω πες: ναι, συνέχισε. Αλλιώς πες: όχι, ακύρωσέ το.",
    "en": "This leaves the machine. To send it say: yes, go ahead. Otherwise say: no, cancel it.",
}
_TAIL = {
    "el": "Αυτό δεν αναιρείται εύκολα. Για να προχωρήσω πες: ναι, συνέχισε. Για να το ακυρώσω πες: όχι, ακύρωσέ το.",
    "en": "This is hard to undo. To go ahead say: yes, go ahead. To cancel say: no, cancel it.",
}


def announce_units(risk: Risk, tool_name: str, arguments: dict, lang: str) -> list[tuple[str, str]]:
    """What is spoken before a RISKY or DESTRUCTIVE tool runs, as (text,
    voice) units. The frame is in the owner's language; a path or command
    is its own unit in the English voice; Greek text stays Greek."""
    lang = "el" if lang == "el" else "en"
    frames = _EL_FRAMES if lang == "el" else _EN_FRAMES
    frame = frames.get(tool_name)
    if frame is None:
        pretty = tool_name.replace("_", " ")
        frame = f"θα εκτελέσω {pretty}:" if lang == "el" else f"I will run {pretty}:"
    if lang == "el":
        frame = ("Προσοχή, " + frame) if risk is Risk.DESTRUCTIVE else (frame[0].upper() + frame[1:])
        if risk is Risk.EGRESS and not frame.startswith("Θα"):
            frame = "Στέλνω στο ίντερνετ, " + frame[0].lower() + frame[1:]
    else:
        frame = ("Careful, " + frame) if risk is Risk.DESTRUCTIVE else frame
        if risk is Risk.EGRESS and not frame.startswith("I will"):
            frame = "Sending to the internet, " + frame[0].lower() + frame[1:]
    units = []
    target = spoken_target(arguments, full=(risk is Risk.EGRESS))
    if frame.endswith(":") and target is None:
        frame = frame[:-1] + "."
    units.append((frame, lang))
    if target is not None:
        units.append(target)
    if risk is Risk.DESTRUCTIVE:
        units.append((_TAIL[lang], lang))
    elif risk is Risk.EGRESS:
        units.append((_EGRESS_TAIL[lang], lang))
    return units


def announce(risk: Risk, tool_name: str, arguments: dict, lang: str) -> str:
    """The same, joined - for logs and tests."""
    return " ".join(t for t, _ in announce_units(risk, tool_name, arguments, lang))


_TARGET_KEYS = ("path", "file", "folder", "command", "repo", "address", "url", "symbol",
                "query", "prompt", "task_description", "proposal_id", "text", "message", "idea")


def spoken_target(arguments: dict, full: bool = False) -> "Optional[tuple[str, str]]":
    """The one argument worth reading back, as a (text, voice) unit.
    `full`: never shorten it (an egress argument IS the data leaving)."""
    for key in _TARGET_KEYS:
        v = arguments.get(key)
        if v in (None, "", False):
            continue
        v = str(v).strip()
        if key == "command":
            return (_spoken_command(v), "en")
        if key in ("path", "file", "folder") or ("/" in v or chr(92) in v) and len(v) < 200:
            return (_spoken_path(v), "en")
        if key == "url":
            return (v, "en")
        if not full:
            v = v if len(v) <= 160 else v[:157] + "…"
        return (v, "el" if _has_greek(v) else "en")
    return None


def _has_greek(s: str) -> bool:
    return any("\u0370" <= c <= "\u03ff" or "\u1f00" <= c <= "\u1fff" for c in s)


def _spoken_path(p: str) -> str:
    """'C:/Users/you/Documents/old_project' -> 'old project, inside Documents.'
    The full path stays in the console log."""
    parts = [x for x in re.split(r"[\\/]+", p.strip()) if x and not re.fullmatch(r"[A-Za-z]:", x)]
    if not parts:
        return p
    def word(x):
        x = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", x)          # drop the extension
        return re.sub(r"[_\-]+", " ", x).strip() or x
    if len(parts) == 1:
        return word(parts[0]) + "."
    return f"{word(parts[-1])}, inside {word(parts[-2])}."


def _spoken_command(c: str) -> str:
    """The WHOLE command, never truncated (MEASURED: a 147-char command was
    cut at 'Where-Object…' and 'Remove-Item' never spoken). Separators are
    said out loud so the English voice does not swallow them."""
    if len(c) > 200:
        c = c[:90] + f" ... and {len(c) - 180} more characters ... " + c[-90:]
    c = c.replace(chr(92), " backslash ").replace("|", " pipe ").replace(";", " semicolon ")
    c = re.sub(r"(?<=\s)-(?=\w)", "dash ", c).replace("&&", " and then ")
    return re.sub(r"\s{2,}", " ", c).strip() + "."
