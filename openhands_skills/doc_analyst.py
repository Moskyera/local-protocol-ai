"""
DocAnalyst - διαβάζει PDF (ακόμα και ολόκληρα βιβλία) και τα εξηγεί.

ΤΟ ΠΡΑΓΜΑΤΙΚΟ ΠΡΟΒΛΗΜΑ: το μοντέλο έχει 64k context. Ένα βιβλίο 300 σελίδων
είναι ~150k+ tokens, δηλαδή ΔΕΝ χωράει. Το να ρίξεις όσο χωράει και να ρωτήσεις
"κάνε περίληψη" δίνει περίληψη μόνο των πρώτων σελίδων — και το μοντέλο δεν σου
λέει ότι είδε μόνο το 20%.

ΠΩΣ ΤΟ ΛΥΝΕΙ:
  1. Εξαγωγή ανά ΣΕΛΙΔΑ (κρατάμε αριθμούς σελίδων για παραπομπές).
  2. MAP: περίληψη κάθε κομματιού ξεχωριστά.
  3. REDUCE: ιεραρχική συγχώνευση των περιλήψεων μέχρι να χωρέσει.
  4. Ερωτήσεις: BM25 retrieval — φέρνει ΜΟΝΟ τα σχετικά κομμάτια, οπότε η
     απάντηση είναι γρήγορη και θεμελιωμένη σε συγκεκριμένες σελίδες.
  5. ΕΠΑΛΗΘΕΥΣΗ στο _finalise(), που είναι η ΜΟΝΗ έξοδος: παραθέσεις (και σε
     «εισαγωγικά»), παραπομπές σε σελίδες που δόθηκαν, άγκυρες πάνω στη σελίδα
     που επικαλούνται, εκφυλισμός, ξένα αλφάβητα, όροι εκτός βιβλίου.

ΤΙ ΔΕΝ ΚΑΝΕΙ — και δεν πρέπει να το εμπιστεύεσαι ότι κάνει:
  · Δεν ελέγχει ΝΟΗΜΑ. Μια παράφραση που αποδίδει λάθος μια ιδέα στη σωστή
    σελίδα περνά· οι έλεγχοι βλέπουν αριθμούς και ονόματα, όχι ισχυρισμούς.
  · Πρόταση χωρίς αριθμό και χωρίς λατινικό όνομα δεν κρίνεται καθόλου.
  · Το 64k context επιβάλλει map-reduce: η περίληψη ΒΙΒΛΙΟΥ είναι περίληψη
    περιλήψεων και χάνει λεπτομέρεια σε κάθε επίπεδο. Δομικό, όχι bug.
  · Σκαναρισμένα PDF περνούν από OCR αυτόματα στο load()· αν αποτύχει, κάθε
    είσοδος επιστρέφει ❌ αντί για άδεια περίληψη.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from logger import log
except Exception:  # pragma: no cover
    import logging
    log = logging.getLogger("doc_analyst")

from openhands_skills.expert_base import ExpertSkill

try:
    from llm_client import (LLM_TRUNCATED_SUFFIX, is_llm_draft, is_llm_error,
                            is_usable)
except Exception:  # pragma: no cover - keeps the module importable standalone
    LLM_TRUNCATED_SUFFIX = "κόπηκε στο όριο tokens"

    def is_llm_error(text: str) -> bool:
        return not (text or "").strip() or text.strip().startswith("(")

    def is_llm_draft(text: str) -> bool:
        return (text or "").strip().startswith("⚠️")

    def is_usable(text: str) -> bool:
        t = (text or "").strip()
        return bool(t) and not t.startswith("(") and not t.startswith("⚠️")

CACHE_DIR = Path(os.getenv("MOSKY_DOC_CACHE",
                           Path(__file__).resolve().parent.parent / "doc_cache"))

#: Chunk size in characters. ~4 chars/token, so 6000 chars ~ 1500 tokens —
#: small enough that many chunks plus instructions still fit comfortably.
#: Τα βιβλία είναι στα αγγλικά αλλά ο χρήστης θέλει ΕΛΛΗΝΙΚΑ. Το ορίζουμε ρητά
#: σε ΚΑΘΕ prompt: αλλιώς το μοντέλο μιμείται τη γλώσσα του αποσπάσματος και
#: γυρίζει σιωπηλά στα αγγλικά στη μέση μιας μεγάλης ανάλυσης.
OUTPUT_LANGUAGE = os.getenv("MOSKY_DOC_LANGUAGE", "Greek")

#: How many chunk summaries to run at once. The chunks are independent, so this
#: is pure throughput — but it MUST match the server's slot count. Measured on
#: this box against a server started with --parallel 4, real chunks of the real
#: book, aggregate tokens/sec:
#:
#:     1 worker   55.1 tok/s   1.00x
#:     2 workers  74.0 tok/s   1.40x
#:     4 workers  99.4 tok/s   1.90x   <- matches the slots
#:     8 workers  70.8 tok/s   1.40x   <- WORSE; the extra four queue and thrash
#:
#: So guessing high is not free. Rather than ask the user to keep two numbers in
#: sync, ask the server: /props reports total_slots. Explicit env var wins;
#: otherwise match the server; fall back to serial if it cannot be reached.
_MAP_WORKERS_ENV = os.getenv("MOSKY_MAP_WORKERS", "").strip()


def _server_slots(timeout: float = 3.0) -> int:
    """How many requests this llama-server will genuinely run at once."""
    try:
        import json as _json
        import urllib.request
        from config import config
        base = getattr(config, "OPENAI_BASE_URL", "http://127.0.0.1:8080/v1")
        url = base.rstrip("/").removesuffix("/v1") + "/props"
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return max(1, int(_json.loads(r.read()).get("total_slots", 1)))
    except Exception:
        return 1


MAP_WORKERS = int(_MAP_WORKERS_ENV) if _MAP_WORKERS_ENV.isdigit() else 0

CHUNK_CHARS = 6000
CHUNK_OVERLAP = 400

#: Bump when ANYTHING that shapes a note changes — the prompts, the grammar, the
#: sampling. Cached notes from an older version are then discarded instead of
#: being silently reused; that is the whole reason the "use the prose model" fix
#: did nothing for a book already in the cache.
#: v3: grammar widened to allow symbols, so notes written under the narrow one
#:     contain "47θ 9'" where the source says "47° 9'".
#: v4: QUOTE_RULE added — word-by-word quote translation was the single
#:     largest source of phrases a Greek reader could not decode.
#: v5: QUOTE_RULE was ambiguous about WHICH language goes inside the quotes;
#:     the model chose wrong and one answer went from 0 to 18 English words.
PROMPT_VERSION = 5

#: Restricts decoding to Greek + ASCII + the punctuation real Greek prose uses.
#:
#: This is the ONLY thing that removes the foreign-script fragments, and the
#: reason is specific: the corrupting token (' lạ' inside «πελάγη») was the
#: model's FIRST choice, not a tail sample. min_p and top_k cannot remove an
#: argmax token by construction — measured, tightening them made corruption
#: worse (1.89 vs 0.86 per 1000 chars). A grammar makes the character
#: unrepresentable. Measured with a prompt deliberately provoking Greek place
#: names: 1 foreign char without it, 0 with it.
#:
#: ASCII stays allowed on purpose: proper names (Cthulhu, R'lyeh), page cites
#: and markdown must survive.
#:
#: Symbols and punctuation must be allowed too, and that is not cosmetic: a
#: first version omitted the degree sign, and the model rendered the coordinates
#: of R'lyeh as "47θ 9'" instead of "47° 9'" — the grammar substituting its own
#: corruption for the one it removed. The ranges below are symbol/punctuation
#: blocks ONLY; every letter range in them is excluded, so no script gets back in
#: (Latin-1 letters start at U+00C0, hence the cut at U+00BF).
#: NO COMMENTS AND NO BLANK LINES INSIDE THIS STRING. llama-server does not
#: reject a grammar it cannot parse — it silently DROPS it and generates
#: unconstrained. Measured the hard way: adding "# ..." comments to document the
#: ranges disabled the constraint completely (33 Cyrillic characters passed a
#: grammar that was supposed to make them impossible) with no error, no warning,
#: and no change in status code. An invalid grammar fails OPEN. Document the
#: ranges here in Python, never inside the grammar.
#:
#: Ranges, in order below: ASCII (names, digits, markdown, cites) / Greek with
#: accents / polytonic Greek / tonos + dialytika / Latin-1 symbols and
#: punctuation, which is where the degree sign lives — the cut at U+00BF is
#: deliberate, letters start at U+00C0 / multiply and divide / dashes, quotes,
#: bullet, ellipsis / per-mille, primes, dagger / euro / arrows / maths.
GREEK_GRAMMAR = (
    "root ::= char+\n"
    "char ::= [\\u0020-\\u007E] | [\\u0386-\\u03CE] | [\\u1F00-\\u1FFF] | "
    "[\\u0384-\\u0385] | [\\u00A0-\\u00BF] | \"\\u00D7\" | \"\\u00F7\" | "
    "[\\u2010-\\u2027] | [\\u2030-\\u205E] | \"\\u20AC\" | [\\u2190-\\u21FF] | "
    "[\\u2200-\\u22FF] | \"\\n\"\n"
)


def output_grammar() -> Optional[str]:
    """The alphabet constraint for the configured output language.

    Only Greek needs one. Constraining English output would be pointless — the
    same model produced 14,526 characters of English notes with zero foreign
    characters — and would risk blocking legitimate symbols in market text.
    """
    return GREEK_GRAMMAR if OUTPUT_LANGUAGE.strip().lower() == "greek" else None


@dataclass
class Page:
    number: int
    text: str


@dataclass
class Chunk:
    index: int
    text: str
    first_page: int
    last_page: int

    @property
    def cite(self) -> str:
        return (f"σ.{self.first_page}" if self.first_page == self.last_page
                else f"σ.{self.first_page}-{self.last_page}")


@dataclass
class Section:
    """A chapter from the PDF's own bookmarks — free, exact structure."""
    level: int
    title: str
    start_page: int
    end_page: int = 0

    @property
    def pages_count(self) -> int:
        return max(1, self.end_page - self.start_page + 1)


def main_sections(sections: List["Section"]) -> List["Section"]:
    """Pick the outline level that actually carries the content.

    Taking level 1 blindly is wrong: a real book on this machine ("A Dark Lore")
    has a single level-1 entry for the book title and all nine stories at
    level 2, so the outline reported "1 chapter, σ.1-1" and hid the entire book.
    Use the shallowest level that has more than one entry.
    """
    if not sections:
        return []
    for lvl in sorted({s.level for s in sections}):
        at_level = [s for s in sections if s.level == lvl]
        if len(at_level) > 1:
            return at_level
    return sections


@dataclass
class Document:
    path: str
    pages: List[Page] = field(default_factory=list)
    chunks: List[Chunk] = field(default_factory=list)
    sections: List[Section] = field(default_factory=list)
    needs_ocr: bool = False
    ocr_used: bool = False
    title: str = ""
    size_mb: float = 0.0

    @property
    def char_count(self) -> int:
        return sum(len(p.text) for p in self.pages)

    @property
    def approx_tokens(self) -> int:
        return self.char_count // 4

    @property
    def pages_with_text(self) -> int:
        return sum(1 for p in self.pages if len(p.text.strip()) > 40)

    def stats(self) -> str:
        """The provenance line under every summary — so it must not overstate.

        It counted pages that EXIST. A book three-quarters scanned, summarised
        from its minority of text pages, reported the full page count and read
        like a complete analysis.
        """
        read = self.pages_with_text
        pages = (f"{len(self.pages)} σελίδες" if read == len(self.pages)
                 else f"{read} από {len(self.pages)} σελίδες με κείμενο")
        base = f"{pages}, ~{self.approx_tokens:,} tokens, {len(self.chunks)} κομμάτια"
        return base + " (μέσω OCR)" if self.ocr_used else base


# --------------------------------------------------------------------------- #
def extract(path: str) -> Document:
    """Pull text out per page. Detects scanned PDFs instead of returning nothing."""
    doc = Document(path=str(path))
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(path)

    doc.size_mb = round(p.stat().st_size / 1_048_576, 1)
    text_by_page: List[Tuple[int, str]] = []
    try:
        import fitz  # pymupdf — much better layout handling than pypdf
        with fitz.open(str(p)) as f:
            doc.title = (f.metadata or {}).get("title") or p.stem
            # The PDF already knows its own chapters. Using that beats blind
            # chunking on a book: "explain chapter 4" then reads 30 pages, not 900.
            try:
                toc = f.get_toc() or []
                for lvl, title, start in toc:
                    doc.sections.append(Section(int(lvl), str(title).strip(), int(start)))
                for i, s in enumerate(doc.sections):
                    s.end_page = (doc.sections[i + 1].start_page - 1
                                  if i + 1 < len(doc.sections) else f.page_count)
            except Exception:
                pass
            for i, page in enumerate(f, start=1):
                text_by_page.append((i, page.get_text("text") or ""))
    except Exception as e:
        log.warning(f"pymupdf failed ({e}); falling back to pypdf")
        # Reset: pymupdf may have failed PART WAY through the page loop, and
        # appending the fallback's pages to what it already read duplicates them.
        text_by_page = []
        from pypdf import PdfReader
        r = PdfReader(str(p))
        doc.title = p.stem
        for i, page in enumerate(r.pages, start=1):
            try:
                text_by_page.append((i, page.extract_text() or ""))
            except Exception:
                text_by_page.append((i, ""))

    doc.pages = [Page(n, t) for n, t in text_by_page]

    # A PDF of scans has pages but almost no characters. Say so plainly.
    non_empty = sum(1 for pg in doc.pages if len(pg.text.strip()) > 40)
    doc.needs_ocr = bool(doc.pages) and non_empty < max(1, len(doc.pages) * 0.2)

    doc.chunks = _chunk(doc.pages)
    return doc


def _chunk(pages: List[Page]) -> List[Chunk]:
    """Split into overlapping chunks, remembering which pages each one REALLY spans.

    The range is derived from character OFFSETS, not from "which page did I last
    read". The old approach was wrong on 38 of 197 chunks (19%) of the user's
    real book, in two ways that both inflate the range:

      * it stamped a chunk with the page it had just appended, even when the cut
        fell before that page's text began — chunk 38 claimed [σ.63-65] while
        ending on page 64;
      * it then started the next chunk at that same page, ignoring that the
        400-character overlap carried across came from an earlier one — chunk 15
        claimed [σ.26-27] while its text starts on page 25.

    Every [σ.X] the model emits is copied from these numbers, so a reader
    following a citation landed on a page that does not contain the claim. That
    defeats the entire point of a page-grounded summariser.
    """
    chunks: List[Chunk] = []
    buf = ""
    #: (offset_in_buf, page_number), ascending: text from `offset` onward is
    #: that page's, until the next mark.
    marks: List[Tuple[int, int]] = []

    def page_at(off: int) -> int:
        pg = marks[0][1] if marks else 1
        for o, n in marks:
            if o > off:
                break
            pg = n
        return pg

    def span(text: str) -> Optional[Tuple[int, int]]:
        """The first and last page `text` actually contains, ignoring padding."""
        if not text.strip():
            return None
        i0 = len(text) - len(text.lstrip())
        i1 = len(text.rstrip()) - 1
        return page_at(i0), page_at(i1)

    def rebase(new_start: int) -> None:
        """Re-anchor `marks` after the buffer is rebuilt from `new_start`."""
        nonlocal marks
        marks = ([(0, page_at(new_start))]
                 + [(o - new_start, n) for o, n in marks if o > new_start])

    for pg in pages:
        t = re.sub(r"[ \t]+", " ", pg.text or "").strip()
        if not t:
            continue
        sep = "\n" if buf else ""
        marks.append((len(buf) + len(sep), pg.number))
        buf += sep + t

        while len(buf) >= CHUNK_CHARS:
            cut = buf.rfind("\n", 0, CHUNK_CHARS)
            if cut < CHUNK_CHARS // 2:
                cut = CHUNK_CHARS
            piece, rest = buf[:cut], buf[cut:]
            rng = span(piece)
            if rng:
                chunks.append(Chunk(len(chunks), piece.strip(), rng[0], rng[1]))
            # The next buffer starts inside `piece`, at the overlap tail — which
            # is exactly the offset the page range must now be measured from.
            keep = piece[-CHUNK_OVERLAP:]
            joined = keep + rest
            trimmed = joined.lstrip()
            rebase((len(piece) - len(keep)) + (len(joined) - len(trimmed)))
            buf = trimmed

    rng = span(buf)
    if rng:
        chunks.append(Chunk(len(chunks), buf.strip(), rng[0], rng[1]))
    return chunks


# --------------------------------------------------------------------------- #
#: Every quote character real Greek prose uses. ASCII-only matching examined
#: ZERO of the quotations in a delivered book: 6 guillemet spans, 1 ASCII.
_QUOTE_RE = re.compile(r'[«"“„]([^»"”\n]{25,300})[»"”]')


def verify_quotes(answer: str, doc: Document) -> List[str]:
    """Check that every quoted passage really exists in the document.

    A summariser that invents a convincing quote is worse than one that says
    nothing, so quotes are checked against the source rather than trusted.
    """
    problems: List[str] = []
    haystack = _normalise(" ".join(p.text for p in doc.pages))
    # _QUOTE_RE, not ASCII-only: Greek prose uses guillemets, and matching just
    # `"` meant this examined ZERO of the quotations in a real delivered book —
    # measured across three shipped chapters, 6 guillemet spans and 1 ASCII.
    for q in _QUOTE_RE.findall(answer or ""):
        if _normalise(q) not in haystack:
            problems.append(q[:90])
    return problems


def _normalise(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def _repeated_lines(text: str, min_lines: int = 6) -> Optional[str]:
    """One sentence emitted over and over as separate points.

    Observed for real: a 13-chunk chapter summary where points 5 to 16 were the
    identical sentence repeated twelve times.
    """
    lines = [_normalise(re.sub(r"^\s*[\d\-*.)]+\s*", "", ln))
             for ln in (text or "").splitlines() if len(ln.strip()) > 40]
    if len(lines) < min_lines:
        return None
    counts: Dict[str, int] = {}
    for ln in lines:
        counts[ln] = counts.get(ln, 0) + 1
    _, n = max(counts.items(), key=lambda kv: kv[1])
    if n >= 3 and n / len(lines) >= 0.3:
        return (f"το μοντέλο επανέλαβε την ίδια πρόταση {n} φορές "
                f"({100 * n // len(lines)}% του κειμένου)")
    return None


def _looping_phrase(text: str, n: int = 4) -> Optional[str]:
    """A phrase looping WITHIN a line — invisible to a line-based check.

    Measured: an English->Greek translation pass collapsed into
    '"λεπ scales" -> "λεπ scales" -> ...' hundreds of times on a single line.
    The line-repetition check above saw one unique line and passed it, and the
    22k characters of garbage then made the corruption RATE look better than
    the honest output it was being compared against. Length is not quality.
    """
    words = _normalise(text).split()
    if len(words) < n * 8:
        return None
    grams: Dict[tuple, int] = {}
    for i in range(len(words) - n + 1):
        g = tuple(words[i:i + n])
        grams[g] = grams.get(g, 0) + 1
    gram, hits = max(grams.items(), key=lambda kv: kv[1])
    covered = hits * n / len(words)
    if hits >= 5 and covered >= 0.15:
        return (f"η φράση «{' '.join(gram)}» επαναλαμβάνεται {hits} φορές "
                f"({int(100 * covered)}% του κειμένου) — το μοντέλο κόλλησε")
    return None


def detect_degeneration(text: str, min_lines: int = 6) -> Optional[str]:
    """Spot output that is long but empty: the model looping instead of writing."""
    return (_repeated_lines(text, min_lines) or _looping_phrase(text))


#: Scripts that cannot legitimately appear in a Greek summary of an English
#: book. The QAT-quantised model drops stray tokens from them into the middle of
#: Greek words ("πε lạ ξες", "Γренλандия", "λαﻋεών") — real, measured, and
#: invisible unless you read every line, which is the whole point of the tool.
_ALIEN_SCRIPT = re.compile(
    r"[Ѐ-ӿԀ-ԯ"      # Cyrillic
    r"֐-ۿ܀-ݏ"       # Hebrew, Arabic, Syriac
    r"ऀ-෿฀-໿"       # Indic scripts, Thai, Lao
    r"Ḁ-ỿ"                    # Latin Extended Additional (Vietnamese)
    r"぀-ヿ一-鿿"       # Kana, CJK
    r"가-힯]"                   # Hangul
)


#: A single token containing BOTH Greek and Latin letters. Latin is legitimately
#: allowed for proper names (Cthulhu, R'lyeh), so a script check alone cannot see
#: this — and blind judges found exactly this class in real output: «Γrenland»
#: for Γροιλανδία, and «Η Begegnση» (a German stem with a Greek ending) sitting
#: in a section heading. Both are unpronounceable and both passed every check.
#: Legitimate mixed tokens do exist (COVID-19ος, iPhone-άκι) but not in this
#: pipeline's output, so the false-positive risk is worth the catch.
_MIXED_SCRIPT = re.compile(
    r"\b(?=[^\W\d_]*[Ͱ-Ͽἀ-῿])"
    r"(?=[^\W\d_]*[A-Za-z])[^\W\d_]{3,}\b", re.UNICODE)


def detect_script_noise(text: str) -> Optional[str]:
    """Find characters and tokens that have no business being in the output."""
    problems = []
    hits = _ALIEN_SCRIPT.findall(text or "")
    if hits:
        words = sorted({w for w in re.findall(r"\S*\S", text or "")
                        if _ALIEN_SCRIPT.search(w)})[:5]
        problems.append(f"{len(hits)} χαρακτήρες από ξένα αλφάβητα "
                        f"(π.χ. {', '.join(words)})")

    mixed = sorted(set(_MIXED_SCRIPT.findall(text or "")))
    if mixed:
        problems.append(f"{len(mixed)} λέξεις που ανακατεύουν ελληνικά και "
                        f"λατινικά γράμματα (π.χ. {', '.join(mixed[:5])})")

    return "· ".join(problems) if problems else None


#: How the model is told to cite. Chunks carry RANGES ("σ.20-22"), but the old
#: instruction said "cite pages as [σ.X]" — singular — so the model narrowed each
#: range to one page it chose itself. That is invention: nothing in the notes
#: says which page inside the range a claim came from.
CITE_RULE = ("Cite with the EXACT bracket that precedes each note, copied "
             "verbatim — if a note is marked [σ.20-22], write [σ.20-22], never "
             "[σ.21]. Never cite a page you were not given.")

#: Blind readers found that almost every comprehension-breaking phrase in real
#: answers sat INSIDE quotation marks. Translating English phrasing word by word
#: produced «μυλιά ύψος», «Cyclopean μαζευτική εργασία», «αλκοολικής απάτης»,
#: «έκαναν κόντη» — each one a phrase a Greek reader cannot decode, wrapped in
#: quotes that present it as the book's own words. Paraphrasing is strictly
#: better here: the model can say what a passage MEANS in Greek far more
#: reliably than it can render its wording.
#: The first version of this rule said "keep the quote in English and explain it
#: in Greek after". The model did it BACKWARDS — «τρομακτικό κεφάλι καραβιάρη»
#: (awful squid-head) — putting a bad translation in the quotes and the English
#: in a parenthesis, so one answer went from 0 to 18 loose English words AND
#: kept the mistranslations («πειραματική ζελατίνα» for "pursuing jelly", where
#: «πειραματική» means experimental). Ambiguity in an instruction is a defect.
#: This version leaves no order to get wrong: quotes hold ENGLISH ONLY, and the
#: Greek that follows carries no quotes and no parentheses.
QUOTE_RULE = (
    "QUOTES: whatever you put inside «...» must be the EXACT English wording "
    "from the excerpt, copied character for character. NEVER put a Greek "
    "translation inside «...». After the quote, explain what it means in plain "
    "Greek with NO quotation marks and NO parentheses containing English. "
    "If you cannot do that, drop the quote entirely and just say in normal Greek "
    "what the passage says. Never invent a Greek word — if the exact word does "
    "not exist for you, describe the thing in ordinary words. Apart from quotes "
    "and proper names (Cthulhu, R'lyeh, Angell), no English may appear anywhere.")


#: One page reference. NOT anchored to a closing bracket on purpose: the model
#: packs several into one bracket — «[σ. 27, σ. 1]», «[σ. 46-47, σ. 48]» — and a
#: regex demanding «]» right after the number is blind to every one of them.
#: Measured: that blindness is why citations to pages the model never saw
#: survived a pass that was written to delete them.
#: The model does not always write «σ.». Counted across the delivered book and
#: its note cache: 1295 «σ.», 45 «σελ.», 4 «σελίδα». Those 49 escaped widening,
#: dropping, page-checking and claim-verification entirely — 3.6% of citations
#: with no oversight at all, including one pointing at the title page.
_PAGE_WORD = r"(?:σελίδ\w*|σελ\.|σ\.)"
_CITE_ONE = re.compile(_PAGE_WORD + r"\s*(\d+)(?:\s*[-–]\s*(\d+))?")
#: A whole bracket containing at least one page reference.
_CITE_RE = re.compile(r"\[([^\[\]]*" + _PAGE_WORD + r"\s*\d[^\[\]]*)\]")


def widen_citations(text: str, fed: List[Tuple[int, int]]) -> str:
    """Undo the model narrowing a page range it was given.

    CITE_RULE tells it to copy the bracket verbatim and it mostly does not: given
    a note marked [σ.24-26] it writes [σ.26]. Measured against the real book,
    that is where the surviving citation errors come from — «1913» cited σ.26
    when the book has it on σ.24, «1877» cited σ.55-56 when it is on σ.52. The
    fact is right and the page is wrong, which is the worst combination, because
    a reader who checks concludes the summary is unreliable.

    Nothing here guesses: a narrowed cite is restored to the range it came from,
    which is the honest statement of what is actually known.
    """
    if not fed:
        return text

    def one(m):
        lo = int(m.group(1))
        hi = int(m.group(2) or m.group(1))
        holders = [(a, b) for a, b in fed if a <= lo and hi <= b]
        # Normalise «σελ. 5» / «σελίδα 5» to «σ.5» even when nothing widens, so
        # the reader sees one form and later passes cannot miss a variant.
        if not holders:
            return f"σ.{lo}" if lo == hi else f"σ.{lo}-{hi}"
        a, b = min(holders, key=lambda r: r[1] - r[0])
        return f"σ.{a}" if a == b else f"σ.{a}-{b}"

    def bracket(m):
        return "[" + _CITE_ONE.sub(one, m.group(1)) + "]"

    return _CITE_RE.sub(bracket, text)


def drop_invalid_citations(text: str, allowed: set) -> Tuple[str, int]:
    """Remove citations to pages the model was never shown. Returns (text, n).

    Measured across all nine stories of a real book: chapters covering σ.22-51,
    σ.52-68, σ.100-185 and σ.186-234 each emitted citations to σ.1, σ.2, σ.11,
    σ.18 — the model numbering the STORY's own pages instead of the book's. Those
    brackets look exactly like the real ones and point somewhere arbitrary.

    Deleting is the honest repair. The right page is unknowable from here, and a
    sentence with no citation is visibly unsourced, while a sentence with a wrong
    citation is confidently misleading — and only costs the reader something when
    they go and check.
    """
    if not allowed:
        return text, 0
    dropped = 0

    def bracket(m):
        nonlocal dropped
        kept = []
        for c in _CITE_ONE.finditer(m.group(1)):
            lo = int(c.group(1))
            hi = int(c.group(2) or c.group(1))
            if any(p in allowed for p in range(lo, hi + 1)):
                kept.append(c.group(0).replace(" ", ""))
            else:
                dropped += 1
        # A bracket that loses every reference disappears entirely; one that
        # keeps some is rebuilt from only the survivors.
        return f"[{', '.join(kept)}]" if kept else ""

    out = _CITE_RE.sub(bracket, text)
    return (re.sub(r"[ \t]{2,}", " ", re.sub(r"\s+([.,;:])", r"\1", out)), dropped)


def check_citations(text: str, allowed: set) -> Optional[str]:
    """Flag [σ.X] references to pages that were never fed to the model.

    Cheap and worth it: a citation is the one part of a summary a reader can
    check, so a wrong one costs more trust than a vague sentence.
    """
    if not allowed:
        return None
    # Skip the analyst's own lines like verify_claims and unknown_terms do.
    # Without this the check reads its OWN warning — "παραπομπές σε σελίδες που
    # δεν δόθηκαν (σ.1, σ.2)" — and re-reports the page numbers inside it,
    # keeping a warning alive after the citations causing it were removed.
    body = _OWN_LINE.sub("", text or "")
    cited = set()
    for m in _CITE_ONE.finditer(body):
        lo = int(m.group(1))
        hi = int(m.group(2)) if m.group(2) else lo
        cited.update(range(lo, min(hi, lo + 60) + 1))
    stray = sorted(cited - allowed)
    if not stray:
        return None
    return (f"{len(stray)} παραπομπές σε σελίδες που δεν δόθηκαν στο μοντέλο "
            f"(σ.{', σ.'.join(str(p) for p in stray[:6])})")


#: Second backend for the language-polish pass. Empty = no polishing.
#: Start it with start-llama-greek.ps1 (CPU, port 8081), which does not touch
#: VRAM, so the main model keeps serving on the GPU throughout.
POLISH_URL = os.getenv("MOSKY_LLM2_URL", "").strip()

#: The model copies this preamble back before its answer, and that is on purpose:
#: moving these rules into the system prompt stopped the echo AND made it
#: SUMMARISE instead of proofread — 32% of the length, 12 of 35 citations, and
#: 1908, Gustaf, Henry Anthony, New Orleans, Esquimaux and Ph'nglui all gone.
#: The echo is what anchors it to "repair THIS", so it is kept and stripped
#: mechanically afterwards.
_POLISH_MARKER = "ΚΕΙΜΕΝΟ:"
_POLISH_PROMPT = (
    "Διόρθωσε ΜΟΝΟ τα ελληνικά στο παρακάτω κείμενο.\n\n"
    "ΑΠΑΡΑΒΑΤΟΙ ΚΑΝΟΝΕΣ:\n"
    "1. Κράτα ΚΑΘΕ παραπομπή [σ.X] ακριβώς όπως είναι, στην ίδια θέση.\n"
    "2. Κράτα ΟΛΕΣ τις επικεφαλίδες, τη δομή και τη σειρά των παραγράφων.\n"
    "3. Κράτα τα κύρια ονόματα στα λατινικά (Cthulhu, Angell, R'lyeh...).\n"
    "4. ΜΗΝ συντομεύσεις, ΜΗΝ περιλάβεις, ΜΗΝ αφαιρέσεις πληροφορία.\n"
    "5. Διόρθωσε: λάθος πτώσεις, λάθος ρηματικούς τύπους, ανύπαρκτες λέξεις.\n"
    "6. Επίστρεψε ΜΟΝΟ το διορθωμένο κείμενο, χωρίς σχόλια.\n\n"
    + _POLISH_MARKER + "\n")


def polish_is_safe(before: str, after: str) -> Optional[str]:
    """Reject a polish that changed anything but the language. None = safe.

    Deliberately does NOT require Latin proper names to survive: measured, the
    polisher renders «των Esquimaux στη Γrenland» as «των Εσκιμώων στη
    Γροιλανδία» — correct Greek for a people and a place, AND a repair of a
    corrupted token. An earlier version of this check called that "lost names"
    and would have thrown away a working pass.

    Numbers, citations and structure are checked strictly, because those are the
    things a reader verifies against the book.
    """
    if not after.strip():
        return "άδειο αποτέλεσμα"
    ratio = len(after) / max(1, len(before))
    if not 0.9 <= ratio <= 1.3:
        return f"το μήκος άλλαξε σε {ratio * 100:.0f}%"

    # ORDERED, not sets and counts. Comparing them as sets made every
    # rearrangement invisible: swapping the citations of two adjacent claims,
    # or swapping two years between two sentences, both passed as "safe" — and
    # rule 1 of the polish prompt is precisely "keep every [σ.X] where it is".
    if re.findall(r"\d+", before) != re.findall(r"\d+", after):
        return "οι αριθμοί άλλαξαν σειρά ή τιμή"
    if _CITE_RE.findall(before) != _CITE_RE.findall(after):
        return "οι παραπομπές άλλαξαν σειρά ή περιεχόμενο"

    # Structure. Deleting every heading kept the length identical, so the ratio
    # check above cannot see it.
    def shape(t):
        return [ln.strip()[:40] for ln in t.splitlines()
                if re.match(r"\s*(#{1,6}\s|\*\*|[*\-]\s)", ln)]
    if len(shape(after)) < len(shape(before)):
        return "χάθηκαν επικεφαλίδες ή σημεία λίστας"

    # The polisher CANNOT emit ⚠ or ❌ — GREEK_GRAMMAR contains no codepoint for
    # them — so any warning already in the text is deleted just by passing
    # through, silently, while every other check above still says "safe".
    for marker in ("⚠", "❌"):
        if before.count(marker) > after.count(marker):
            return f"ο διορθωτής έσβησε προειδοποιήσεις ({marker})"

    if detect_degeneration(after):
        return "ο διορθωτής εκφυλίστηκε"
    return None


#: Lines the analyst writes itself. They carry page numbers and Latin words that
#: are not claims about the book, and treating them as claims produced the one
#: false positive in the whole verification run.
#: The warning sign is TWO codepoints when typed (U+26A0 + U+FE0F variation
#: selector) and often one when round-tripped through a file or a model. Matching
#: the literal «⚠️» silently fails on the one-codepoint form, which is how a
#: check ended up re-reading its own warning and keeping it alive after the
#: citations that caused it had already been removed. Match the base character.
#: Matches the WHOLE line, not just its first characters. Stripping only the
#: marker left the rest of the sentence behind, so check_citations read the page
#: numbers out of its own warning — «(σ.1, σ.2)» — and kept reporting them after
#: the citations that caused it were deleted. The `.*$` is the entire fix.
_OWN_LINE = re.compile("^[ \\t]*(#|\\*σ\\.|⚠|❌|\\*\\*Υποθέσεις).*$", re.M)

#: A number must not be a fragment of a longer one. Without the separator guard,
#: «150,000,000» yields the anchor «000», which is then reported as unverifiable
#: — measured, that was one of the eleven warnings on a real run.
_ANCHOR_NUM = re.compile(r"(?<![\w°'.,])(\d{2,4})(?![\w'.,]|\s*\d)")

#: An anchor only proves something about a page if it is RARE. «Blake» is the
#: protagonist of a 17-page story and appears on most of its pages; demanding it
#: on the exact cited page flags nothing but noise. Measured: 5 of 11 warnings on
#: a real run were recurring names and common numbers that are genuinely in the
#: book. Anchors on more pages than this carry no page-specific information.
_ANCHOR_MAX_PAGES = 8
_ANCHOR_NAME = re.compile(r"\b[A-Z][A-Za-z'’]{3,}\b")
#: Words that appear everywhere or are the analyst's own vocabulary, so finding
#: them proves nothing about a particular page.
_ANCHOR_STOP = {"The", "This", "That", "These", "Great", "Old", "Ones", "Call",
                "Cthulhu", "None", "Note", "Cyclopean", "Mythos"}


def _cited_sentences(text: str):
    """Yield (sentence_without_cites, [(lo, hi), ...]) for cited sentences only."""
    body = _OWN_LINE.sub("", text or "")
    masked = _CITE_RE.sub("§C§", body)
    # One bracket can hold several references — «[σ. 27, σ. 1]» — so the pages of
    # a bracket are collected together, not one per mask.
    found = [[(int(a), int(b or a)) for a, b in _CITE_ONE.findall(inner)]
             for inner in _CITE_RE.findall(body)]
    i = 0
    for part in re.split(r"(?<=[.;:!?])\s+|\n+", masked):
        n = part.count("§C§")
        if n:
            cites = [c for group in found[i:i + n] for c in group]
            if cites:
                yield part.replace("§C§", " "), cites
        i += n


def verify_claims(text: str, pages: Dict[int, str], slack: int = 1) -> Optional[str]:
    """Check that each cited claim is actually ON the page it cites.

    check_citations() only confirms the page was SHOWN to the model, and that is
    not the same thing: measured on the real book, the output placed R'lyeh at
    «34°21' Ν [σ.18]» when those coordinates are on σ.15 and σ.18 has 47°9'.
    Right page number, wrong claim, nothing flagged.

    Verifies ANCHORS — numbers and Latin proper names, the things a reader would
    actually look up — not meaning. A sentence with no anchors is not judged.
    That narrowness is the point: measured 145 anchors across a real run with 6
    flagged, of which 5 were true defects. A check that cries wolf is a check
    people learn to ignore.
    """
    if not pages:
        return None

    def distinctive(anchor: str) -> bool:
        """True when finding this anchor says something about a PAGE."""
        return sum(1 for t in pages.values() if anchor in t) <= _ANCHOR_MAX_PAGES

    misses, checked = [], 0
    for sent, cites in _cited_sentences(text):
        # Each cited range plus slack — NOT one span from the lowest page to the
        # highest. A sentence stitched from two distant notes, «[σ.127-128, σ.170-171]»,
        # was being verified against all 47 pages in between, which is precisely
        # the sentence most likely to have gone wrong.
        want = {p for lo, hi in cites
                for p in range(lo - slack, hi + slack + 1)}
        src = " ".join(pages.get(p, "") for p in sorted(want))
        if not src.strip():
            continue
        anchors = set(_ANCHOR_NUM.findall(sent)) | {
            n for n in _ANCHOR_NAME.findall(sent) if n not in _ANCHOR_STOP}
        for a in anchors:
            if not distinctive(a):
                continue
            checked += 1
            if a not in src:
                misses.append(a)
    # One miss out of thirty is inside the noise of a heuristic like this, and
    # measured, single-miss warnings were what pushed two otherwise clean
    # chapters into the flagged column. Require a pattern, not an incident.
    if len(misses) < 2 or checked < 5:
        return None
    pct = 100 * len(misses) // checked
    if pct < 5:
        return None
    return (f"{len(misses)} από {checked} στοιχεία ({pct}%) δεν βρέθηκαν στη "
            f"σελίδα που επικαλούνται (π.χ. {', '.join(sorted(set(misses))[:5])})")


#: A lowercase Latin word inside Greek prose is an untranslated word, not a
#: name. Proper names are capitalised — Angell, Cthulhu, R'lyeh, Innsmouth — so
#: the case distinction separates the two almost perfectly and needs no list.
#: Four blind readers found these in real answers: «των necks τους», «παρόμοιους
#: με εκεί ones», «cessation των ονείρων», «η αίρεση (the cult)», «γίνονταν
#: «πολύ γλοιώδη» (bald)» — where the Greek says the OPPOSITE of the parenthesis
#: and a monolingual reader learns the wrong thing.
_UNTRANSLATED = re.compile(r"(?<![A-Za-z'’.])\b([a-z]{3,})\b(?![A-Za-z'’])")
#: Latin that legitimately appears lowercase in a Greek text about an English book.
_LATIN_OK = {"the", "of", "and", "in", "de", "von", "van", "al", "el",
             "www", "com", "org", "pdf", "html", "http", "https",
             # loanwords a Greek reader knows and would not want translated
             "voodoo", "internet", "email", "online", "web"}


def detect_untranslated(text: str) -> Optional[str]:
    """English words left mid-sentence where a Greek word was needed."""
    body = _OWN_LINE.sub("", text or "")
    # Citations, italicised titles, code — and QUOTED spans. Keeping a short
    # quote in the original English is what QUOTE_RULE now ASKS for, so flagging
    # words inside «...» would punish the instructed behaviour. Measured: the
    # only two false positives on eight real files were «fhtagn», inside the
    # ritual phrase, and «voodoo», a loanword.
    # The quoted-span cap was 300 characters and real quotes are longer. A
    # 320-character quotation — exactly what QUOTE_RULE asks for, exact English
    # followed by «δηλαδή» and the Greek — was reported as 33 untranslated
    # words. The check punished the instructed behaviour, which is worse than
    # not checking: it would have sent the model back to translating.
    body = re.sub(r"\[[^\]]*\]|\*[^*\n]{1,40}\*|`[^`\n]+`"
                  r"|«[^»]{0,1200}»|\"[^\"\n]{0,1200}\"|“[^”]{0,1200}”",
                  " ", body)
    found = sorted({w for w in _UNTRANSLATED.findall(body)
                    if w not in _LATIN_OK})
    if not found:
        return None
    return (f"{len(found)} αγγλικές λέξεις μέσα στο ελληνικό κείμενο "
            f"(π.χ. {', '.join(found[:5])})")


def unknown_terms(text: str, source: str) -> Optional[str]:
    """Latin-script terms in the output that appear NOWHERE in the book.

    This is how «Halloween» was caught: the book says «Hallowmass» throughout and
    the model quietly modernised it. The term reads authoritative, survives every
    other check, and is simply not what the source says. Anything the book never
    writes was not read out of the book.
    """
    if not source:
        return None
    body = _OWN_LINE.sub("", text or "")
    # Case-insensitive: «Mind» at the start of a Greek clause is the book's
    # «mind», not an invented term. Measured, that was a false alarm on a real run.
    low = source.lower()
    terms = {t for t in _ANCHOR_NAME.findall(body) if t not in _ANCHOR_STOP}
    strays = sorted(t for t in terms if t.lower() not in low)
    if not strays:
        return None
    return (f"{len(strays)} όροι που δεν υπάρχουν πουθενά στο βιβλίο "
            f"(π.χ. {', '.join(strays[:5])})")


def quality_notes(text: str, allowed_pages: Optional[set] = None,
                  pages: Optional[Dict[int, str]] = None) -> List[str]:
    """Every defect worth warning about, in one place."""
    source = " ".join(pages.values()) if pages else ""
    return [n for n in (detect_degeneration(text),
                        detect_script_noise(text),
                        detect_untranslated(text),
                        check_citations(text, allowed_pages or set()),
                        verify_claims(text, pages or {}),
                        unknown_terms(text, source)) if n]


#: Words that carry no retrieval signal. Kept small and explicit rather than
#: pulling in an NLP dependency: these are the ones that actually hijacked
#: ranking in testing.
_STOPWORDS = {
    # english
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "be",
    "been", "of", "in", "on", "at", "to", "for", "with", "by", "from", "as",
    "it", "its", "this", "that", "these", "those", "what", "which", "who",
    "how", "why", "when", "where", "does", "do", "did", "can", "could",
    "would", "should", "will", "about", "into", "than", "then", "there",
    "here", "have", "has", "had", "not", "no", "yes", "you", "your", "me",
    "my", "we", "our", "they", "their", "i", "s", "t",
    # greek (accent-stripped, since we normalise before matching)
    "και", "η", "ο", "το", "τα", "της", "του", "των", "στο", "στη", "στην",
    "στον", "σε", "με", "για", "απο", "που", "ποιο", "ποια", "ποιος", "τι",
    "ειναι", "ηταν", "θα", "να", "δεν", "μου", "σου", "μας", "σας", "ενα",
    "μια", "ως", "οτι", "αν", "πως", "παρα", "αλλα", "εχει", "εχουν", "λεει",
}


def _content_terms(text: str) -> List[str]:
    """Query terms worth matching on: no stopwords, keeps numbers and units."""
    import unicodedata
    folded = unicodedata.normalize("NFD", (text or "").casefold())
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    toks = re.findall(r"[\w%]+", folded)
    return [t for t in toks if t not in _STOPWORDS and (len(t) > 2 or t.isdigit())]


# --------------------------------------------------------------------------- #
class DocAnalyst(ExpertSkill):
    ROLE = "doc_analyst"
    EXPERTISE = ("a careful analyst who reads documents closely and explains "
                 "them accurately, always saying which page a claim comes from")
    DEFAULT_TEMPERATURE = 0.3
    # PROSE, not code. Measured on a real Lovecraft collection with the coding
    # model loaded: points 5-16 of a chapter summary were the SAME sentence
    # repeated verbatim, and the Greek was ungrammatical ("Ο έργος τέχνης",
    # "ο νόμιος"). A coding model is the wrong instrument for literary text.
    USE_CODING_MODEL = False

    _cache: Dict[str, Document] = {}
    #: Guards the shared note dict and its write-through file once
    #: several chunk summaries can complete at the same time.
    _cache_lock = __import__('threading').Lock()
    _slots_cache: Optional[int] = None

    @classmethod
    def _slots(cls) -> int:
        """Server slot count, asked once per process."""
        if cls._slots_cache is None:
            cls._slots_cache = _server_slots()
            if cls._slots_cache > 1:
                log.info(f"DocAnalyst: server offers {cls._slots_cache} slots; "
                         f"mapping chunks {cls._slots_cache}-way")
        return cls._slots_cache

    def grammar(self) -> Optional[str]:
        """Constrain the output alphabet — see GREEK_GRAMMAR for the evidence."""
        return output_grammar()

    @staticmethod
    def _pages_of(chunks: List[Chunk]) -> set:
        """Every page the model was actually shown — the set a cite must fall in."""
        pages = set()
        for c in chunks:
            pages.update(range(c.first_page, c.last_page + 1))
        return pages

    def polish(self, text: str) -> str:
        """Repair the Greek with a specialist model, or return `text` untouched.

        Runs on a SECOND llama-server on the CPU (start-llama-greek.ps1), so the
        main model keeps the GPU and nothing is swapped. Measured on a real
        chapter, twice, identically: length 100%, citations 35/35, headings 3/3,
        no number lost or invented, and every defect gone — «οκταποδού»,
        «όκτωπο», «Begegnση», «Γrenland».

        Never trusted blindly. If the result fails polish_is_safe() the original
        is returned unchanged: this model SHORTENS when it is not tightly
        anchored, and a summary silently replacing a summary is exactly the kind
        of failure this system exists to avoid.
        """
        if not POLISH_URL or not text.strip():
            return text
        try:
            import llm_client
            raw = llm_client.chat(
                _POLISH_PROMPT + text, temperature=0.2,
                max_tokens=max(2000, int(len(text) / 2)),
                system_prompt=("Είσαι επιμελητής ελληνικών κειμένων. Διορθώνεις "
                               "ΜΟΝΟ τη γλώσσα. Δεν είσαι συγγραφέας και δεν "
                               "έχεις γνώμη για το περιεχόμενο."),
                grammar=output_grammar(), base_url=POLISH_URL)
            if is_llm_error(raw) or is_llm_draft(raw):
                log.warning("DocAnalyst: polisher unavailable, keeping original")
                return text
            i = raw.rfind(_POLISH_MARKER)
            out = (raw[i + len(_POLISH_MARKER):] if i >= 0 else raw).strip()
            bad = polish_is_safe(text, out)
            if bad:
                log.warning(f"DocAnalyst: polish REJECTED ({bad}); keeping original")
                return text
            log.info("DocAnalyst: Greek polished by the specialist model")
            return out
        except Exception as e:
            log.warning(f"DocAnalyst: polish failed ({e}); keeping original")
            return text

    def _finalise(self, body: str, head: str = "",
                  allowed_pages: Optional[set] = None,
                  fed: Optional[List[Tuple[int, int]]] = None,
                  doc: Optional[Document] = None) -> str:
        """Single exit for every user-facing answer.

        Every quality check lives here so a new entry point cannot quietly ship
        unchecked text: quality_notes() used to run in chapter() only, while
        analyze(), ask() and explain() returned whatever came back.
        """
        if is_llm_error(body):
            # NO header. Prefixing the failure with "# The Call of Cthulhu
            # *σ.2-21 · 13 κομμάτια*" makes a dead backend look like a finished
            # analysis: measured, a harness scoring 9 totally failed chapters
            # reported "9/9 clean, 0 warnings" because it checked the first
            # character and found a heading. A failure must announce itself from
            # character one, to a reader and to a script alike.
            return ("❌ Το μοντέλο δεν απάντησε — δεν παρήχθη ανάλυση.\n"
                    "Έλεγξε ότι τρέχει ο llama-server (start-ai.bat) και "
                    "ξαναδοκίμασε.")
        if is_llm_draft(body):
            # Same rule as the error branch, and it was missing here: a draft is
            # the model's own deliberation, not an answer. Under a header reading
            # "# The Call of Cthulhu / *σ.2-21 · 13 κομμάτια*" it is indistinguishable
            # from a finished chapter — and if the polish pass then ran, the
            # grammar would delete its ⚠ label on the way out.
            return ("⚠️ Το μοντέλο δεν ολοκλήρωσε την ανάλυση — αυτό που "
                    "ακολουθεί είναι οι πρόχειρες σκέψεις του, ΟΧΙ περίληψη.\n\n"
                    + body)
        # Polish BEFORE checking: the checks should describe what the user
        # actually receives, not an intermediate the polisher already repaired.
        body = self.polish(body)
        body = widen_citations(body, fed or [])
        body, dropped = drop_invalid_citations(body, allowed_pages or set())
        if dropped:
            head += (f"⚠️ Αφαιρέθηκαν {dropped} παραπομπές σε σελίδες που δεν "
                     f"διαβάστηκαν — οι προτάσεις αυτές μένουν ατεκμηρίωτες.\n")
        # Quote verification lives HERE, not in individual entry points. It ran
        # in analyze() and ask() only, so chapter() — the path that produced
        # every one of the nine stories delivered from a real book — never
        # checked a single quotation, while the module docstring calls that the
        # headline feature.
        if doc:
            fake = verify_quotes(body, doc)
            if fake:
                head += ("⚠️ Παραθέσεις που ΔΕΝ βρέθηκαν στο κείμενο (μην τις "
                         "εμπιστευτείς): " + "; ".join(fake[:3]) + "\n")
        pages = {p.number: p.text for p in doc.pages} if doc else None
        for note in quality_notes(body, allowed_pages, pages):
            head += f"⚠️ Ποιότητα κειμένου: {note}.\n"
        if head and not head.endswith("\n\n"):
            head += "\n"
        return head + body

    # ---------------------------------------------------------------- #
    def _note_cache(self, doc: Document) -> Tuple[Path, dict]:
        """Per-book cache of chunk summaries.

        A 1500-page book is ~625 chunks ~ 1.5-2 hours of local inference. Losing
        that to a crash, a restart, or simply asking a second question would make
        the tool unusable, so every chunk summary is written to disk as it is
        produced and reused forever after.

        The key MUST include everything that shapes a note. It used to be just
        path+mtime, and that quietly defeated a real fix: after switching this
        skill off the coding model, chapter 1 of the user's book was still
        served 13/13 from cache — every note written by the coding model, in
        English, by the exact instrument the switch was meant to replace. A
        cache you cannot invalidate turns every future fix into a no-op.
        """
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        key = hashlib.sha1(
            f"{os.path.abspath(doc.path)}::{os.path.getmtime(doc.path)}"
            f"::{self._model_id()}::{OUTPUT_LANGUAGE}::{PROMPT_VERSION}"
            f"::{CHUNK_CHARS}::{CHUNK_OVERLAP}::{getattr(doc, 'ocr_used', False)}"
            .encode()).hexdigest()[:16]
        f = CACHE_DIR / f"{key}.notes.json"
        data = {}
        if f.exists():
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        return f, data

    @staticmethod
    def _model_id() -> str:
        """Which model actually answers, not which one we ask for.

        llama-server serves whatever GGUF is loaded and ignores the requested
        name, so the requested one is worthless as a cache dimension.
        """
        try:
            import llm_client
            resp = llm_client.get_llm_client().models.list()
            return resp.data[0].id if resp.data else "unknown"
        except Exception:
            return "unknown"

    def _summarise_chunk(self, c: Chunk, cache_file: Path, cache: dict) -> str:
        # Keyed on the TEXT, not the position. Chunk indices move whenever
        # CHUNK_CHARS changes or a scan is re-OCRed at a different DPI, and a
        # note silently re-attaching to a different page produces confident,
        # correctly-formatted, wrong citations.
        key = hashlib.sha1(c.text.encode("utf-8")).hexdigest()[:16]
        if key in cache:
            return cache[key]
        n = self.consult(
            "Summarise this excerpt in 3-5 bullets. Keep concrete claims, "
            "definitions, numbers and arguments. Add nothing that is not in "
            f"the text. Write the notes in {OUTPUT_LANGUAGE}."
            f"\n\n[{c.cite}]\n{c.text}",
            # 900, not 500: Greek costs ~1.8x more tokens per character than
            # English on this tokenizer, so the old budget would clip notes.
            max_tokens=900)
        if not is_usable(n):
            return ""
        note = f"[{c.cite}] {n.strip()}"
        with self._cache_lock:     # several chunks may finish at once now
            cache[key] = note
            try:                   # write through, so a crash loses one chunk
                cache_file.write_text(json.dumps(cache, ensure_ascii=False),
                                      encoding="utf-8")
            except Exception:
                pass
        return note

    def _map_chunks(self, chunks: List[Chunk], cache_file: Path, cache: dict,
                    label: str = "map", every: int = 10) -> List[str]:
        """Summarise every chunk, in parallel when the server allows it.

        The chunk summaries are INDEPENDENT — nothing in one depends on another —
        and they dominate the cost: 9 chapters of a real book took 67 minutes,
        almost all of it here, one request at a time against a server running
        --parallel 1. Order is preserved regardless of completion order, because
        the notes are fed to the reduce step as a sequence and page citations
        would otherwise arrive shuffled.

        MAP_WORKERS=1 restores the exact previous behaviour.
        """
        workers = MAP_WORKERS or self._slots()
        done = [None] * len(chunks)
        if workers <= 1 or len(chunks) < 2:
            for i, c in enumerate(chunks):
                done[i] = self._summarise_chunk(c, cache_file, cache)
                if (i + 1) % every == 0 or i + 1 == len(chunks):
                    log.info(f"  {label} {i + 1}/{len(chunks)}")
            return [n for n in done if n]

        from concurrent.futures import ThreadPoolExecutor, as_completed
        finished = 0
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(self._summarise_chunk, c, cache_file, cache): i
                       for i, c in enumerate(chunks)}
            for fut in as_completed(futures):
                i = futures[fut]
                try:
                    done[i] = fut.result()
                except Exception as e:      # one bad chunk must not kill the book
                    log.warning(f"  {label}: chunk {i} failed: {e}")
                    done[i] = ""
                finished += 1
                if finished % every == 0 or finished == len(chunks):
                    log.info(f"  {label} {finished}/{len(chunks)} "
                             f"({workers} parallel)")
        return [n for n in done if n]

    def load(self, path: str, ocr: bool = True) -> Document:
        """Load a PDF, running OCR automatically when it is a scan.

        The user's books are image scans, so without this every call would
        correctly but uselessly report "needs OCR". OCR results are cached on
        disk per page, so this is paid once per book.
        """
        key = f"{os.path.abspath(path)}::{os.path.getmtime(path)}"
        h = hashlib.sha1(key.encode()).hexdigest()[:16]
        if h in self._cache:
            return self._cache[h]
        doc = extract(path)

        if doc.needs_ocr and ocr:
            try:
                from openhands_skills import pdf_ocr
                if pdf_ocr.available():
                    cached = pdf_ocr.load_cache(path)
                    if len(cached) < len(doc.pages):
                        log.info(f"DocAnalyst: {Path(path).name} is a scan — "
                                 f"OCR ~{pdf_ocr.estimate_minutes(len(doc.pages)):.0f} min")
                    texts = pdf_ocr.ocr_pdf(path)
                    for pg in doc.pages:
                        t = texts.get(pg.number, "")
                        if t.strip():
                            pg.text = t
                    doc.chunks = _chunk(doc.pages)
                    non_empty = sum(1 for p in doc.pages if len(p.text.strip()) > 40)
                    doc.needs_ocr = non_empty < max(1, len(doc.pages) * 0.2)
                    doc.ocr_used = True
                else:
                    log.warning("DocAnalyst: scan detected but no OCR engine installed")
            except Exception as e:
                log.error(f"DocAnalyst: OCR failed: {e}")

        self._cache[h] = doc
        log.info(f"DocAnalyst loaded {Path(path).name}: {doc.stats()}")
        return doc

    # ---------------------------------------------------------------- #
    def outline(self, path: str) -> str:
        """Show the book's own chapter structure, with an honest time estimate.

        For a 100 MB / 900-page book, a full map-reduce read is roughly one LLM
        call per 1500 words. Telling you that up front — and letting you read one
        chapter instead — is the difference between a usable tool and one that
        appears to hang for an hour.
        """
        doc = self.load(path)
        lines = [f"# {doc.title}",
                 f"*{doc.size_mb} MB · {doc.stats()}*", ""]
        if doc.needs_ocr:
            lines.append("⚠️ Σκαναρισμένο — χρειάζεται OCR πριν διαβαστεί.")
            return "\n".join(lines)

        secs_per_chunk = 9.0     # measured on this machine, local 30B
        full_min = len(doc.chunks) * secs_per_chunk / 60.0
        lines.append(f"Πλήρης ανάλυση όλου: ~{full_min:.0f} λεπτά "
                     f"({len(doc.chunks)} κομμάτια).")

        if doc.sections:
            tops = main_sections(doc.sections)
            lines += ["", f"## Κεφάλαια ({len(tops)})", ""]
            for i, s in enumerate(tops, 1):
                est = max(1, int(s.pages_count * len(doc.chunks) /
                                 max(1, len(doc.pages)) * secs_per_chunk / 60))
                lines.append(f"{i:>3}. {s.title[:64]:<64} σ.{s.start_page}-{s.end_page} "
                             f"(~{est} λεπτά)")
            lines += ["", "Διάβασε ένα κεφάλαιο: "
                          "`doc_analyst.chapter(path, 3)`",
                      "Ρώτησε κάτι συγκεκριμένο (γρήγορο): "
                      "`doc_analyst.ask(path, '...')`"]
        else:
            lines += ["", "Το PDF δεν έχει bookmarks κεφαλαίων, οπότε δεν "
                          "μπορώ να δώσω δομή. Χρησιμοποίησε `ask()` για "
                          "συγκεκριμένες ερωτήσεις — είναι γρήγορο ανεξάρτητα "
                          "από το μέγεθος."]
        return "\n".join(lines)

    def chapter(self, path: str, which, detailed: bool = True) -> str:
        """Read ONE chapter properly — by number or by title match."""
        doc = self.load(path)
        if doc.needs_ocr:
            # analyze() and ask() have always refused here; these two did
            # not, so a scan with no text layer produced a confident
            # analysis of almost nothing.
            return ("❌ Σκαναρισμένο PDF χωρίς αναγνώσιμο κείμενο — δεν "
                    "παρήχθη ανάλυση. Χρειάζεται OCR πρώτα.")
        tops = main_sections(doc.sections)
        if not tops:
            return ("Το PDF δεν έχει κεφάλαια στα bookmarks. Δοκίμασε "
                    "`ask()` ή `analyze()`.")

        sec = None
        if isinstance(which, int):
            if 1 <= which <= len(tops):
                sec = tops[which - 1]
        else:
            q = str(which).lower()
            sec = next((s for s in tops if q in s.title.lower()), None)
        if sec is None:
            return (f"Δεν βρέθηκε κεφάλαιο «{which}». Διαθέσιμα: "
                    + "; ".join(f"{i}. {s.title[:40]}" for i, s in enumerate(tops, 1))[:600])

        sel = [c for c in doc.chunks
               if c.last_page >= sec.start_page and c.first_page <= sec.end_page]
        if not sel:
            return f"Το κεφάλαιο «{sec.title}» δεν έχει κείμενο (σ.{sec.start_page}-{sec.end_page})."

        log.info(f"DocAnalyst: chapter '{sec.title}' -> {len(sel)} chunks")
        cache_file, cache = self._note_cache(doc)
        notes = self._map_chunks(sel, cache_file, cache, "chapter", every=5)
        if not notes:
            # The marker goes first: every failure must be visible to a
            # reader skimming and to a script checking the first byte.
            return ("❌ Κανένα από τα κομμάτια δεν διαβάστηκε — δεν παρήχθη "
                    "ανάλυση. Έλεγξε ότι τρέχει ο llama-server.")

        style = ("Explain it thoroughly, as if teaching someone: the ideas, how "
                 "they connect, and the concrete examples the text gives."
                 if detailed else "Summarise it tightly.")
        # 6000, not 3000: the real reduce prompt for this chapter needed ~2900
        # tokens of preamble alone, so 3000 returned a summary cut off in the
        # middle of a clause under a confident header.
        body = self.consult(
            f"{style} {CITE_RULE} {QUOTE_RULE} {QUOTE_RULE} Use ONLY these notes. Never repeat "
            f"the same sentence — if you have nothing further to add, stop. "
            f"Write the whole answer in {OUTPUT_LANGUAGE}.\n\n"
            + "\n\n".join(notes), max_tokens=6000)

        head = (f"# {sec.title}\n*σ.{sec.start_page}-{sec.end_page} · "
                f"{len(sel)} κομμάτια*\n\n")
        if len(notes) < len(sel):
            head += (f"⚠️ {len(sel) - len(notes)} από {len(sel)} κομμάτια δεν "
                     f"διαβάστηκαν — η περίληψη είναι ελλιπής.\n")
        return self._finalise(body, head, self._pages_of(sel),
                              [(c.first_page, c.last_page) for c in sel], doc)

    # ---------------------------------------------------------------- #
    def analyze(self, path: str, max_chunks: int = 0) -> str:
        """Full map-reduce read: key topics + summary, with page references."""
        doc = self.load(path)
        if doc.needs_ocr:
            return (f"⚠️ Το «{doc.title}» δεν έχει κείμενο που να διαβάζεται "
                    f"({len(doc.pages)} σελίδες, σχεδόν μηδέν χαρακτήρες). "
                    f"Είναι σκαναρισμένο — χρειάζεται OCR πρώτα. Δεν θα σου "
                    f"δώσω περίληψη από κενές σελίδες.")
        if not doc.chunks:
            return f"Δεν βρέθηκε κείμενο στο {doc.title}."

        chunks = doc.chunks[:max_chunks] if max_chunks else doc.chunks
        log.info(f"DocAnalyst: map over {len(chunks)} chunks")

        # MAP — one pass per chunk, cached to disk so a 1500-page run survives a
        # crash and a second question never repeats two hours of inference.
        cache_file, cache = self._note_cache(doc)
        # Notes are keyed on sha1(chunk.text), not on the index — this counter
        # looked up str(c.index) and could therefore never report a hit.
        cached = sum(1 for c in chunks
                     if hashlib.sha1(c.text.encode("utf-8")).hexdigest()[:16] in cache)
        if cached:
            log.info(f"DocAnalyst: reusing {cached}/{len(chunks)} cached summaries")
        notes = self._map_chunks(chunks, cache_file, cache, "map", every=10)

        if not notes:
            return ("❌ Το μοντέλο δεν επέστρεψε τίποτα — δεν παρήχθη "
                    "περίληψη. Έλεγξε ότι τρέχει ο llama-server.")
        # chapter() has warned about unread chunks since it was written; the
        # whole-book path counted nothing, so a summary built from 3 of 20
        # chunks was presented under a header saying "20 κομμάτια".
        unread = len(chunks) - len(notes)

        # REDUCE — merge in batches until it fits in one pass.
        level = 0
        while len(notes) > 12 and level < 4:
            merged: List[str] = []
            for i in range(0, len(notes), 10):
                batch = "\n\n".join(notes[i:i + 10])
                m = self.consult(
                    "Merge these section notes into a tighter set of bullets. "
                    "KEEP every page reference EXACTLY as written — never "
                    "narrow [σ.20-22] to [σ.21], never merge two ranges into "
                    "one. Drop repetition, keep every distinct idea.\n\n" + batch,
                    max_tokens=900)
                # A merge cut off at the token limit loses every note after the
                # cut AND splices the Greek truncation banner into the notes as
                # if it were content. Keeping the original batch is lossless.
                truncated = LLM_TRUNCATED_SUFFIX.strip()[:12] in m
                merged.append(m.strip() if is_usable(m) and not truncated
                              else batch)
            notes, level = merged, level + 1

        final = self.consult(
            "From these notes on the whole document, write:\n"
            "1. **Τι είναι** — 2-3 προτάσεις.\n"
            "2. **Βασικά θέματα** — 5-8 σημεία, το καθένα με παραπομπή [σ.X].\n"
            "3. **Τα σημαντικότερα σημεία** — τι πρέπει οπωσδήποτε να κρατήσει "
            "ο αναγνώστης, και γιατί.\n"
            "4. **Τι ΔΕΝ καλύπτει** — αν φαίνεται από τις σημειώσεις.\n"
            "Γράψε στα ελληνικά. Μην προσθέσεις τίποτα εκτός σημειώσεων.\n\n"
            + "\n\n".join(notes),
            max_tokens=2500)

        header = (f"# {doc.title}\n*{doc.stats()}*\n\n")   # quotes: _finalise
        if unread:
            header += (f"⚠️ {unread} από {len(chunks)} κομμάτια δεν "
                       f"διαβάστηκαν — η περίληψη είναι ελλιπής.\n")
        return self._finalise(final, header, self._pages_of(doc.chunks),
                              [(c.first_page, c.last_page) for c in doc.chunks], doc)

    # ---------------------------------------------------------------- #
    def _retrieve(self, doc: Document, query: str, k: int = 6) -> List[Chunk]:
        """BM25 keyword retrieval — offline, no embedding model needed.

        Stopwords are stripped from the QUERY. Measured why: asking "What
        performance improvement is reported and what caused it?" ranked the
        Conclusions chapter at 12.41 purely on what/is/and/it, while the chunk
        that literally contains "42% improvement in throughput" scored 7.90 and
        never made the cut. Content words must decide the match.
        """
        if not doc.chunks:
            return []
        terms = _content_terms(query)
        if not terms:
            terms = re.findall(r"\w+", query.lower())
        try:
            from rank_bm25 import BM25Okapi
            corpus = [re.findall(r"\w+", c.text.lower()) for c in doc.chunks]
            bm = BM25Okapi(corpus)
            scores = bm.get_scores(terms)
            # BM25 gives a term zero (or negative) weight when it appears in more
            # than half the documents. On a SHORT document — a 12-page scan is
            # only 2 chunks — that silently zeroes every score and the answer
            # becomes "I found nothing" for a question the text clearly answers.
            if max(scores, default=0) <= 0:
                raise ValueError("degenerate BM25 scores on a small corpus")
            order = sorted(range(len(scores)), key=lambda i: -scores[i])
            return [doc.chunks[i] for i in order[:k] if scores[i] > 0]
        except Exception as e:
            log.info(f"BM25 not usable here ({e}); using term-frequency match")
            scored = [(sum(c.text.lower().count(t) for t in terms), c)
                      for c in doc.chunks]
            scored.sort(key=lambda x: -x[0])
            hits = [c for s, c in scored[:k] if s > 0]
            # A short document that mentions none of the terms genuinely has no
            # answer; but if it is small enough to read whole, just read it.
            if not hits and len(doc.chunks) <= k:
                return list(doc.chunks)
            return hits

    def ask(self, path: str, question: str, k: int = 6) -> str:
        """Answer a question about the document, grounded in retrieved pages."""
        doc = self.load(path)
        if doc.needs_ocr:
            return "⚠️ Σκαναρισμένο PDF χωρίς κείμενο — χρειάζεται OCR πρώτα."

        hits = self._retrieve(doc, question, k=k)
        if not hits:
            return (f"Δεν βρήκα σχετικό απόσπασμα για «{question}» μέσα στο "
                    f"«{doc.title}». Ίσως δεν το καλύπτει το κείμενο.")

        context = "\n\n".join(f"[{c.cite}]\n{c.text}" for c in hits)
        answer = self.consult(
            f"Answer the question using ONLY the excerpts below. {CITE_RULE} {QUOTE_RULE} "
            f"If the excerpts do not contain the answer, say so plainly instead "
            f"of guessing. Write the whole answer in {OUTPUT_LANGUAGE}.\n\n"
            f"ΕΡΩΤΗΣΗ: {question}\n\nΑΠΟΣΠΑΣΜΑΤΑ:\n{context}",
            max_tokens=1800)

        if is_llm_error(answer):
            return self._finalise(answer, allowed_pages=self._pages_of(hits),
                                  fed=[(c.first_page, c.last_page) for c in hits], doc=doc)
        answer += f"\n\n*Πηγές: {', '.join(c.cite for c in hits)}*"   # quotes: _finalise
        return self._finalise(answer, allowed_pages=self._pages_of(hits),
                              fed=[(c.first_page, c.last_page) for c in hits], doc=doc)

    def explain(self, path: str, topic: str, depth: str = "detailed") -> str:
        """Teach a topic from the document, in as much depth as it supports."""
        doc = self.load(path)
        if doc.needs_ocr:
            # analyze() and ask() have always refused here; these two did
            # not, so a scan with no text layer produced a confident
            # analysis of almost nothing.
            return ("❌ Σκαναρισμένο PDF χωρίς αναγνώσιμο κείμενο — δεν "
                    "παρήχθη ανάλυση. Χρειάζεται OCR πρώτα.")
        hits = self._retrieve(doc, topic, k=8)
        if not hits:
            return f"Το «{topic}» δεν φαίνεται να καλύπτεται στο «{doc.title}»."
        context = "\n\n".join(f"[{c.cite}]\n{c.text}" for c in hits)
        return self._finalise(self.consult(
            f"Explain «{topic}» to someone learning it, using ONLY these "
            f"excerpts. Structure it: what it is, why it matters, how it works "
            f"step by step, and a concrete example FROM THE TEXT. {CITE_RULE} {QUOTE_RULE} "
            f"Say explicitly if the text leaves something unexplained. "
            f"Write the whole answer in {OUTPUT_LANGUAGE}."
            f"\n\nΑΠΟΣΠΑΣΜΑΤΑ:\n{context}",
            max_tokens=3000), allowed_pages=self._pages_of(hits),
            fed=[(c.first_page, c.last_page) for c in hits], doc=doc)


doc_analyst = DocAnalyst()
