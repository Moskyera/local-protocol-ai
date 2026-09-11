"""Greek text the way a Greek would SAY it, for the Greek voice only.

Piper phonemises through espeak-ng, and the Greek voice was trained on
Greek phonemes. MEASURED 2026-09-11 (Piper -> whisper round trip, 5 runs):
  "Κοστίζει 1.250 ευρώ."                 amount recovered 0/5  (espeak reads
                                          the digits with phonemes the voice
                                          never learned, e.g. ʂ)
  "Κοστίζει χίλια διακόσια πενήντα ευρώ." 4/5
  "Η ώρα είναι 11:25."                    CER 22%   words: 0%
  "κ.λπ."                                 "κάπα τελεία λάμδα πι"
  Latin tech terms (GPU, GitHub, Docker,
  PowerShell, Bitcoin)                    1/15 recovered; Greek spelling 9/15
So: numbers, money, percentages, times and abbreviations become words, and
the tech terms a Greek says every day get the spelling a Greek would use.
Years stay digits (MEASURED 0% CER as digits) unless followed by a unit.
Unknown Latin words are left alone; guard.announce routes them to the
English voice as their own unit instead.
"""

from __future__ import annotations

import re

# --------------------------------------------------------------------------- #
# Numbers. Greek numerals agree in gender with the noun for 1, 3, 4, the
# hundreds and the thousands; everything else is invariable.
# --------------------------------------------------------------------------- #
_UNITS = {
    "n": ["μηδέν", "ένα", "δύο", "τρία", "τέσσερα", "πέντε", "έξι", "επτά", "οκτώ", "εννέα",
          "δέκα", "έντεκα", "δώδεκα", "δεκατρία", "δεκατέσσερα", "δεκαπέντε", "δεκαέξι",
          "δεκαεπτά", "δεκαοκτώ", "δεκαεννέα"],
    "m": ["μηδέν", "ένας", "δύο", "τρεις", "τέσσερις", "πέντε", "έξι", "επτά", "οκτώ", "εννέα",
          "δέκα", "έντεκα", "δώδεκα", "δεκατρείς", "δεκατέσσερις", "δεκαπέντε", "δεκαέξι",
          "δεκαεπτά", "δεκαοκτώ", "δεκαεννέα"],
    "f": ["μηδέν", "μία", "δύο", "τρεις", "τέσσερις", "πέντε", "έξι", "επτά", "οκτώ", "εννέα",
          "δέκα", "έντεκα", "δώδεκα", "δεκατρείς", "δεκατέσσερις", "δεκαπέντε", "δεκαέξι",
          "δεκαεπτά", "δεκαοκτώ", "δεκαεννέα"],
}
_TENS = ["", "", "είκοσι", "τριάντα", "σαράντα", "πενήντα", "εξήντα", "εβδομήντα", "ογδόντα", "ενενήντα"]
_HUNDREDS = {
    "n": ["", "εκατό", "διακόσια", "τριακόσια", "τετρακόσια", "πεντακόσια", "εξακόσια", "επτακόσια", "οκτακόσια", "εννιακόσια"],
    "m": ["", "εκατό", "διακόσιοι", "τριακόσιοι", "τετρακόσιοι", "πεντακόσιοι", "εξακόσιοι", "επτακόσιοι", "οκτακόσιοι", "εννιακόσιοι"],
    "f": ["", "εκατό", "διακόσιες", "τριακόσιες", "τετρακόσιες", "πεντακόσιες", "εξακόσιες", "επτακόσιες", "οκτακόσιες", "εννιακόσιες"],
}


def _below_thousand(n: int, g: str) -> str:
    parts = []
    h, r = divmod(n, 100)
    if h:
        parts.append("εκατόν" if h == 1 and r else _HUNDREDS[g][h])
    if r:
        if r < 20:
            parts.append(_UNITS[g][r])
        else:
            t, u = divmod(r, 10)
            parts.append(_TENS[t] + (" " + _UNITS[g][u] if u else ""))
    return " ".join(parts)


def number_to_words(n: int, gender: str = "n") -> str:
    """0..999 999 999 in Greek words. gender: n (ευρώ, λεπτά), m (μήνες), f (ώρες)."""
    if n < 0:
        return "μείον " + number_to_words(-n, gender)
    if n == 0:
        return "μηδέν"
    if n >= 1_000_000_000:
        return str(n)
    parts = []
    millions, rest = divmod(n, 1_000_000)
    if millions:
        parts.append("ένα εκατομμύριο" if millions == 1 else _below_thousand(millions, "n") + " εκατομμύρια")
    thousands, units = divmod(rest, 1000)
    if thousands:
        if thousands == 1:
            parts.append({"n": "χίλια", "m": "χίλιοι", "f": "χίλιες"}[gender])
        else:
            parts.append(_below_thousand(thousands, "f") + " χιλιάδες")   # χιλιάδες is feminine
    if units:
        parts.append(_below_thousand(units, gender))
    return " ".join(parts)


# nouns that follow a number and are not neuter
_FEMININE = {"ώρα", "ώρες", "μέρα", "μέρες", "ημέρα", "ημέρες", "εβδομάδα", "εβδομάδες", "λέξη", "λέξεις",
             "σελίδα", "σελίδες", "γραμμή", "γραμμές", "φορά", "φορές", "μετοχή", "μετοχές", "μονάδα", "μονάδες",
             "εικόνα", "εικόνες", "σημείωση", "σημειώσεις", "εντολή", "εντολές", "λίρα", "λίρες", "δραχμή", "δραχμές"}
_MASCULINE = {"μήνας", "μήνες", "χρόνος", "χρόνοι", "βαθμός", "βαθμοί", "χρήστης", "χρήστες", "φάκελος", "φάκελοι",
              "πόντος", "πόντοι", "τόνος", "τόνοι", "υπολογιστής", "υπολογιστές", "πυρήνας", "πυρήνες"}


def _gender_for(following: str) -> str:
    w = following.strip().lower()
    if w in _FEMININE:
        return "f"
    if w in _MASCULINE:
        return "m"
    return "n"


# --------------------------------------------------------------------------- #
# The tech vocabulary, spelled as a Greek says it
# --------------------------------------------------------------------------- #
# MEASURED 2026-09-11 (Piper joy -> whisper, 2-3 runs each): letter-spelled
# acronyms fail in every spelling ("έι-εμ-ντι" -> "E carta ime", "εμ-σι-πι"
# -> "NCP γεραπαντάει"), so acronyms get the WORD a Greek uses instead
# ("κάρτα γραφικών" 2/2, "επεξεργαστής" 2/2, "γίγα" 8/9) or the one-word
# form Greeks actually say ("έιπιάι" -> API 2/2, "γιουεσμπί" -> USB 1/2).
# Two-word "πάουερ σελ" -> PowerShell 2/2 where "πάουερσελ" was 1/3;
# "πάιθων" -> Python 2/2; "τέλεγκραμ" 2/2; "ιμέιλ" 3/3; "ντόκερ" 3/3.
# GitHub stays hard in every spelling (1/2 at best).
TERMS = {
    "gpu": "κάρτα γραφικών", "cpu": "επεξεργαστής", "vram": "μνήμη της κάρτας γραφικών", "ram": "μνήμη ραμ",
    "ssd": "δίσκος", "usb": "γιουεσμπί", "wifi": "γουάι-φάι", "wi-fi": "γουάι-φάι", "api": "έιπιάι",
    "mcp": "διακομιστής εργαλείων", "url": "λινκ", "pdf": "πιντιέφ", "json": "τζέισον",
    "ai": "τεχνητή νοημοσύνη", "llm": "γλωσσικό μοντέλο", "vpn": "βιπιέν", "ip": "αϊπί",
    "powershell": "πάουερ σελ", "windows": "γουίντοους", "linux": "λίνουξ", "docker": "ντόκερ",
    "github": "γκίτ-χαμπ", "git": "γκιτ", "python": "πάιθων", "javascript": "τζάβα σκριπτ", "script": "σκριπτ",
    "bitcoin": "μπιτκόιν", "ethereum": "ιθίριουμ", "solana": "σολάνα", "usdt": "τέθερ", "tether": "τέθερ",
    "binance": "μπάιναντς", "telegram": "τέλεγκραμ", "whisper": "γουίσπερ", "piper": "πάιπερ",
    "llama": "λάμα", "gemma": "τζέμα", "qwen": "κουέν", "canvas": "κάνβας", "openhands": "όπεν χαντς",
    "email": "ιμέιλ", "e-mail": "ιμέιλ", "chrome": "κρόουμ", "firefox": "φάιρφοξ", "notepad": "νόουτπαντ",
    "excel": "έξελ", "google": "γκουγκλ", "youtube": "γιουτιούμπ", "vulkan": "βούλκαν",
    "backup": "μπάκαπ", "server": "σέρβερ", "online": "ονλάιν", "offline": "όφλαιν", "download": "ντάουνλοουντ",
    "update": "απντέιτ", "cache": "κας", "cloud": "κλάουντ", "internet": "ίντερνετ", "browser": "μπράουζερ",
    "desktop": "ντέσκτοπ", "laptop": "λάπτοπ", "clipboard": "πρόχειρο", "folder": "φάκελος",
    "gb": "γίγα", "mb": "μέγκα", "tb": "τέρα", "kb": "κιλομπάιτ", "ms": "χιλιοστά του δευτερολέπτου",
}
_TERM_RE = re.compile(r"(?<![A-Za-z\-])(" + "|".join(sorted((re.escape(k) for k in TERMS), key=len, reverse=True)) + r")(?![A-Za-z\-])", re.I)

_ABBREV = {
    "π.χ.": "για παράδειγμα", "κ.λπ.": "και λοιπά", "κλπ.": "και λοιπά", "κλπ": "και λοιπά", "δηλ.": "δηλαδή",
    "κ.ά.": "και άλλα", "π.μ.": "το πρωί", "μ.μ.": "το απόγευμα", "κ.": "κύριε", "τηλ.": "τηλέφωνο",
    "αρ.": "αριθμός", "σελ.": "σελίδα", "βλ.": "βλέπε", "ό.π.": "όπως παραπάνω",
}
_ABBREV_RE = re.compile("|".join(re.escape(k) for k in sorted(_ABBREV, key=len, reverse=True)), re.I)


# --------------------------------------------------------------------------- #
# The passes
# --------------------------------------------------------------------------- #

def _time_words(h: int, m: int) -> str:
    if h > 23 or m > 59:
        return f"{h}:{m:02d}"
    hour = ["δώδεκα", "μία", "δύο", "τρεις", "τέσσερις", "πέντε", "έξι", "επτά", "οκτώ", "εννέα", "δέκα", "έντεκα"][h % 12]
    if m == 0:
        return f"{hour} ακριβώς"
    if m == 30:
        return f"{hour} και μισή"
    if m == 15:
        return f"{hour} και τέταρτο"
    if m == 45:
        return f"{['μία', 'δύο', 'τρεις', 'τέσσερις', 'πέντε', 'έξι', 'επτά', 'οκτώ', 'εννέα', 'δέκα', 'έντεκα', 'δώδεκα'][h % 12]} παρά τέταρτο"
    return f"{hour} και {number_to_words(m, 'n')}"


def _int_words(digits: str, gender: str) -> str:
    n = int(digits.replace(".", "").replace(" ", ""))
    return number_to_words(n, gender)


def _money(m: re.Match) -> str:
    whole, frac = m.group("whole"), m.group("frac")
    unit = (m.group("unit") or m.group("pre") or "").strip().lower()
    unit_word = {"€": "ευρώ", "ευρώ": "ευρώ", "$": "δολάρια", "δολάρια": "δολάρια", "δολ.": "δολάρια",
                 "£": "λίρες", "λίρες": "λίρες"}[unit]
    gender = "f" if unit_word == "λίρες" else "n"
    n = int(whole.replace(".", ""))
    out = number_to_words(n, gender) + " " + (
        {"ευρώ": "ευρώ", "δολάρια": "δολάριο", "λίρες": "λίρα"}[unit_word] if n == 1 else unit_word)
    if frac and int(frac) > 0:
        cents = int(frac.ljust(2, "0")[:2])
        out += " και " + number_to_words(cents, "n") + (" λεπτό" if cents == 1 else " λεπτά")
    return out


_MONEY_RE = re.compile(
    r"(?P<pre>[€$£]\s?)?(?P<whole>\d{1,3}(?:\.\d{3})+|\d+)(?:,(?P<frac>\d{1,2}))?(?:\s?(?P<unit>ευρώ|δολάρια|δολ\.|λίρες|€|\$|£))?")
# seven or more digits in a row is a phone number, an id, a card: digit by digit
_LONG_DIGITS_RE = re.compile(r"(?<![\d.,])(\d{7,}|\d{3,4}[ -]\d{6,7})(?![\d.,])")
_TIME_RE = re.compile(r"\b(?P<h>[01]?\d|2[0-3]):(?P<m>[0-5]\d)\b")
_PERCENT_RE = re.compile(r"(?P<whole>\d+)(?:,(?P<frac>\d+))?\s?%")
_NUMBER_RE = re.compile(r"(?<![\d,.])(?P<num>\d{1,3}(?:\.\d{3})+|\d+)(?:,(?P<frac>\d+))?(?![\d.]\d)(?=\s*(?P<next>[^\W\d_]+)?)")


def _percent(m: re.Match) -> str:
    out = number_to_words(int(m.group("whole")), "n")
    if m.group("frac"):
        out += " κόμμα " + " ".join(number_to_words(int(d), "n") for d in m.group("frac"))
    return out + " τοις εκατό"


def _plain_number(m: re.Match) -> str:
    num, frac, nxt = m.group("num"), m.group("frac"), m.group("next") or ""
    digits = num.replace(".", "")
    # a bare year stays a year: MEASURED 0% CER as digits, and "το 2026"
    # spoken as "δύο χιλιάδες είκοσι έξι" is what a Greek says anyway
    if "." not in num and len(digits) == 4 and 1900 <= int(digits) <= 2099 and not frac:
        return num
    gender = _gender_for(nxt)
    out = number_to_words(int(digits), gender)
    if frac:
        out += " κόμμα " + " ".join(number_to_words(int(d), "n") for d in frac)
    return out


def verbalize_el(text: str) -> str:
    """Numbers, money, percentages, times, abbreviations and tech terms as a
    Greek would say them. Pure regex, under a millisecond."""
    t = _ABBREV_RE.sub(lambda m: _ABBREV[m.group(0).lower()], text)
    t = _LONG_DIGITS_RE.sub(lambda m: " ".join(_UNITS["n"][int(d)] if d.isdigit() else "," for d in m.group(1)), t)
    t = _TIME_RE.sub(lambda m: _time_words(int(m.group("h")), int(m.group("m"))), t)
    t = _PERCENT_RE.sub(_percent, t)
    # money needs a unit or a symbol on either side
    t = _MONEY_RE.sub(lambda m: _money(m) if (m.group("unit") or m.group("pre")) else m.group(0), t)
    t = _NUMBER_RE.sub(_plain_number, t)
    t = _TERM_RE.sub(lambda m: TERMS[m.group(1).lower()], t)
    return re.sub(r"\s{2,}", " ", t).strip()
