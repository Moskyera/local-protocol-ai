"""
Intent Router - αποφασίζει ΤΙ πρέπει να τρέξει για κάθε μήνυμα.

ΓΙΑΤΙ ΥΠΑΡΧΕΙ: το run_task() έτρεχε ΤΑ ΠΑΝΤΑ για κάθε μήνυμα — supervisor plan,
strategic_oracle (LLM + live market network fetches), market_analyst (3 network
reports), coder, tester, reviewer, security, debugger, evolution, synthesis.
Δηλαδή ~8-12 σειριακά LLM calls ακόμα και για ένα "hi". Σε τοπικό 30B = λεπτά.

Ο router ταξινομεί με ΦΘΗΝΗ λογική (καθαρό Python, ΚΑΝΕΝΑ επιπλέον LLM call) και
αφήνει τον caller να τρέξει μόνο ό,τι χρειάζεται.

ΣΧΕΔΙΑΣΤΙΚΕΣ ΑΠΟΦΑΣΕΙΣ (από adversarial review — μη τις αλλάξεις κατά λάθος):

1. Τα "κοινωνικά" intents (GREETING/CAPABILITY/STATUS) απαιτούν **ΠΛΗΡΕΣ match
   ολόκληρου του μηνύματος**, όχι contains-match. Αλλιώς το "hi, fix this bug"
   ταξινομείται ως χαιρετισμός και η πραγματική δουλειά χάνεται σιωπηλά.

2. Ελληνικά: κάνουμε NFD-decompose + αφαίρεση τόνων + casefold. Έτσι "ΓΕΙΑ",
   "γειά", "γεια" πέφτουν όλα στο ίδιο token. Το σκέτο re.IGNORECASE ΔΕΝ αρκεί
   για τονισμένα/κεφαλαία ελληνικά.

3. Το "status" ΔΕΝ είναι μόνο του λέξη-κλειδί: το "market status" είναι ερώτηση
   αγοράς, όχι health-check. Τα work intents προηγούνται πάντα.

4. Precedence: WALLET > SOLIDITY > WEBSITE > CODING > MARKET > social > LEGACY.
   Ό,τι δεν ταιριάζει πάει LEGACY = η παλιά πλήρης διαδρομή (καμία απώλεια).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import List


def normalize(text: str) -> str:
    """Lowercase + accent-strip, so Greek/English match reliably.

    'ΓΕΙΑ' -> 'γεια', 'γειά' -> 'γεια', 'Φτιάξε' -> 'φτιαξε'.
    """
    if not text:
        return ""
    folded = unicodedata.normalize("NFD", text.casefold())
    return "".join(c for c in folded if not unicodedata.combining(c))


_TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def tokens(text: str) -> List[str]:
    """Word tokens only — punctuation, digits and emoji are dropped."""
    return _TOKEN_RE.findall(normalize(text))


# --- Social vocabularies: matched against the WHOLE message ------------------
_GREETING = {
    # english
    "hi", "hello", "hey", "yo", "sup", "morning", "good", "evening", "afternoon",
    "thanks", "thank", "you", "ty", "thx", "ok", "okay", "cool", "nice", "bye",
    # greek (accent-stripped forms)
    "γεια", "σου", "σας", "καλημερα", "καλησπερα", "καληνυχτα", "χαιρετω",
    "ευχαριστω", "ευχαριστωι", "ωραια", "τελεια", "εντακει", "ενταξει", "οκ", "γεσου",
    # Measured missing: "goodbye", "see you", "nice one", "great thanks" and
    # "καλημέρα φίλε" all fell through to the 8-minute pipeline.
    "goodbye", "see", "later", "great", "perfect", "awesome", "welcome",
    # "hi there" / "hey there": "there" lived only in _STATUS, so the
    # greeting check failed on it and the status check failed on "hi".
    "there",
    "φιλε", "φιλαρακι", "καλα", "μπραβο", "συγγνωμη", "παρακαλω",
}

_CAPABILITY = {
    "what", "who", "how", "can", "do", "does", "you", "your", "are", "is", "it",
    "help", "capabilities", "capability", "abilities", "features", "commands", "tools",
    "τι", "ποιος", "πως", "μπορεις", "κανεις", "βοηθεια", "δυνατοτητες", "εργαλεια",
    "ξερεις", "με", "να", "μου", "εισαι",
}

_STATUS = {
    "status", "alive", "there", "you", "up", "online", "ready", "working",
    "ζεις", "εισαι", "εκει", "δουλευεις", "ετοιμος",
    # "are you there" and "are you alive" both failed on the word "are".
    "are", "still", "awake", "running", "live", "ακομα", "ακομη", "ξυπνιος",
}

# --- Work intents: keyword presence anywhere --------------------------------
_WALLET = (
    "wallet", "address", "0x", "whale", "holder", "portfolio", "pnl", "onchain",
    "on-chain", "token holder", "transactions", "πορτοφολι", "διευθυνση", "συναλλαγες",
)

_SOLIDITY = (
    "solidity", "smart contract", "erc20", "erc721", "erc-20", "evm", "defi",
    "pragma", "hvm", "staking contract", "vesting", "συμβολαιο",
)

_WEBSITE = (
    "website", "web site", "webpage", "web page", "landing page", "site",
    "frontend", "front-end", "web app", "webapp", "html", "css", "react",
    "next.js", "nextjs", "vite", "tailwind", "dashboard ui", "portfolio site",
    "ιστοσελιδα", "ιστοσελιδες", "σαιτ", "σελιδα", "ιστοτοπο", "ιστοτοπος",
)

_DATABASE = (
    "database", "db", "sql", "postgres", "postgresql", "sqlite", "mysql",
    "schema", "migration", "orm", "crud", "supabase", "prisma", "table",
    "βαση δεδομενων", "βαση", "πινακας", "σχημα",
)

_CODING = (
    "code", "function", "class", "script", "refactor", "bug", "fix", "debug",
    "implement", "api", "endpoint", "algorithm", "python", "javascript",
    "typescript", "module", "parser", "regex", "cli", "unit test", "pytest",
    "optimize", "rewrite", "error", "exception", "traceback", "compile",
    # found by measurement: "please define the helper" fell through to legacy
    "define", "helper", "method", "variable", "loop", "import", "docstring",
    "type hint", "unit tests", "snippet", "library", "package",
    "κωδικα", "κωδικας", "συναρτηση", "σφαλμα", "διορθωσε", "φτιαξε κωδικα",
    "υλοποιησε", "προγραμμα",
)

_MARKET = (
    "market", "btc", "eth", "price", "chart", "macro", "stock", "crypto",
    "bullish", "bearish", "outlook", "forecast", "trading", "signal", "rsi",
    "portfolio allocation", "briefing", "sentiment", "earnings",
    "αγορα", "τιμη", "μετοχη", "προβλεψη", "αναλυση αγορας",
)

_DOCUMENT = (
    "pdf", "book", "ebook", "document", "paper", "manual", "chapter",
    "summarize", "summarise", "summary", "explain the book",
    "βιβλιο", "εγγραφο", "κεφαλαιο", "περιληψη", "συνοψη", "αναλυσε το pdf",
    "εξηγησε το βιβλιο", "διαβασε το",
)

_CAD3D = (
    "3d model", "3d print", "3d printer", "stl", "cad", "cadquery", "openscad",
    "print it", "printable", "bracket", "enclosure", "3d design",
    "τρισδιαστατο", "εκτυπωτη", "εκτυπωση 3d", "σχεδιασε 3d", "μοντελο 3d",
)

_ANALYZE_FOLDER = (
    "analyze the folder", "analyse the folder", "review the folder", "audit the folder",
    "analyze folder", "review this project", "audit this codebase", "scan the folder",
    "αναλυσε τον φακελο", "αναλυσε το project", "ελεγξε τον φακελο", "αναλυσε τον κωδικα",
)


def _norm_set(words) -> set:
    """Normalize a vocabulary the SAME way messages are normalized.

    Critical for Greek: str.casefold() maps final sigma 'ς' -> 'σ', so a literal
    like 'κάνεις' becomes 'κανεισ'. If the vocabulary is not put through the same
    transform, those words silently never match.
    """
    return {normalize(w) for w in words}


def _norm_tuple(words):
    """Compile a keyword list into ONE word-boundary regex.

    Bare substring matching is a real bug source: 'define' contains 'defi',
    'e-commerce' contains 'erc', 'impulse' contains 'puls'. Without \\b those
    innocent words detonate the Solidity/PulseChain pipeline. Python's \\b is
    Unicode-aware, so it works for Greek too.
    """
    parts = sorted((normalize(w) for w in words), key=len, reverse=True)
    return re.compile(r"\b(?:%s)\b" % "|".join(re.escape(p) for p in parts), re.UNICODE)


# Normalize every vocabulary once, at import time.
_GREETING = _norm_set(_GREETING)
_CAPABILITY = _norm_set(_CAPABILITY)
_STATUS = _norm_set(_STATUS)
_WALLET = _norm_tuple(_WALLET)
_SOLIDITY = _norm_tuple(_SOLIDITY)
_WEBSITE = _norm_tuple(_WEBSITE)
_DATABASE = _norm_tuple(_DATABASE)
_CODING = _norm_tuple(_CODING)
_MARKET = _norm_tuple(_MARKET)
_ANALYZE_FOLDER = _norm_tuple(_ANALYZE_FOLDER)
_CAD3D = _norm_tuple(_CAD3D)
_DOCUMENT = _norm_tuple(_DOCUMENT)


@dataclass
class Route:
    name: str
    reason: str
    #: True when the caller can answer with at most ONE cheap LLM call.
    fast: bool = False
    #: Extra signals the caller may use without re-parsing.
    wants_database: bool = False


#: Words that carry no intent of their own. They are allowed alongside any
#: social vocabulary, because the whole-message rule was too strict for the way
#: people actually write: "hi" matched and "hi there" did not, "ευχαριστώ"
#: matched and "ευχαριστώ πολύ" did not. Measured on 43 ordinary social
#: messages, 15 of them — 35% — fell through to the full pipeline, which costs
#: about eight minutes each.
#:
#: The anti-hijack rule is NOT relaxed. These are connectives only: no verb, no
#: noun, nothing that could carry a request. "hi can you write me a parser"
#: still falls through, because "write", "me" and "parser" are in neither set.
_FILLER = {
    "a", "an", "the", "so", "very", "much", "lot", "lots", "really", "quite",
    "just", "man", "mate", "dude", "one", "all", "for", "and", "then",
    "πολυ", "παρα", "σε", "και", "λοιπον", "ρε", "να",
}


def _all_tokens_in(text: str, vocab: set) -> bool:
    """True only if every word token is in the vocabulary or is a connective.

    This is the anti-hijack rule: a greeting word buried in a real request must
    NOT win. Empty messages never match. A message made only of connectives
    never matches either — "a lot" is not a greeting.
    """
    tk = tokens(text)
    if not tk:
        return False
    if not any(t in vocab for t in tk):
        return False
    return all(t in vocab or t in _FILLER for t in tk)


def _has(text_norm: str, pattern) -> bool:
    """Word-boundary match. `pattern` is a compiled regex from _norm_tuple."""
    if hasattr(pattern, "search"):
        return bool(pattern.search(text_norm))
    return any(normalize(n) in text_norm for n in pattern)  # plain tuples (verbs)


def classify(user_task: str) -> Route:
    """Cheap, deterministic intent classification. No LLM call."""
    raw = (user_task or "").strip()
    if not raw:
        return Route("legacy", "empty message")

    norm = normalize(raw)

    # ---- Work intents FIRST (precedence rule 4) ---------------------------
    # A real request must never be swallowed by the social gates below.
    if _has(norm, _ANALYZE_FOLDER):
        return Route("analyze_folder", "explicit folder/codebase analysis request")

    if _has(norm, _DOCUMENT):
        return Route("document", "PDF / book analysis request")

    if _has(norm, _CAD3D):
        return Route("cad3d", "3D model / printable part request")

    if _has(norm, _WALLET) or re.search(r"0x[a-f0-9]{40}", norm):
        return Route("wallet", "wallet / on-chain address analysis")

    if _has(norm, _SOLIDITY):
        return Route("solidity", "smart-contract work")

    if _has(norm, _WEBSITE):
        return Route("website", "website build request",
                     wants_database=_has(norm, _DATABASE))

    # A DB request without an explicit website word is still usually a web/app build.
    if _has(norm, _DATABASE) and _has(norm, ("build", "create", "make", "φτιαξε", "δημιουργησε", "app")):
        return Route("website", "app + database build request", wants_database=True)

    if _has(norm, _CODING):
        return Route("coding", "code generation / fixing")

    if _has(norm, _MARKET):
        return Route("market", "market / trading question")

    # ---- Social intents: WHOLE-message match only -------------------------
    if _all_tokens_in(raw, _GREETING):
        return Route("greeting", "pure greeting / thanks", fast=True)

    if _all_tokens_in(raw, _STATUS):
        return Route("status", "health check", fast=True)

    if _all_tokens_in(raw, _CAPABILITY) and len(tokens(raw)) <= 8:
        return Route("capability", "asking what the system can do", fast=True)

    # ---- Fallthrough: never lose a request --------------------------------
    return Route("legacy", "no confident match — full pipeline")


__all__ = ["classify", "Route", "normalize", "tokens"]
