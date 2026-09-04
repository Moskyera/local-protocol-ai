"""
pdf_ocr - OCR για σκαναρισμένα PDF (τα βιβλία σου είναι εικόνες).

ΜΕΤΡΗΜΕΝΟ σε αυτό το μηχάνημα (όχι εκτίμηση):
  σειριακά, 1 engine .......... 2.1 δευτ./σελίδα
  4 threads ................... 2.8 δευτ./σελίδα  (ΧΕΙΡΟΤΕΡΑ, 0.7x)
  6 processes ................. 2.4 δευτ./σελίδα  (χωρίς όφελος + 1 σφάλμα)
Ο παραλληλισμός ΔΕΝ βοηθά επειδή το onnxruntime ήδη απασχολεί όλους τους
πυρήνες μέσα στο ίδιο inference· προσθέτοντας workers απλώς ανταγωνίζονται
μεταξύ τους και εμφανίστηκε ONNXRuntimeError. Άρα: σειριακά by default.

Πραγματικός χρόνος: ~2.1 δευτ./σελίδα -> 1500 σελίδες ≈ 52 λεπτά.
Κάθε σελίδα γράφεται στον δίσκο μόλις ολοκληρωθεί, οπότε μια διακοπή στο 80%
δεν πετάει 40 λεπτά δουλειάς και η δεύτερη ανάγνωση είναι ακαριαία (0.01s).

Μηχανή: RapidOCR πάνω σε onnxruntime — pip-only, χωρίς admin install (το
tesseract θέλει εγκατάσταση συστήματος) και χωρίς PyTorch (~2GB, το easyocr).
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional

try:
    from logger import log
except Exception:  # pragma: no cover
    import logging
    log = logging.getLogger("pdf_ocr")

OCR_CACHE = Path(os.getenv("MOSKY_OCR_CACHE",
                           Path(__file__).resolve().parent.parent / "doc_cache" / "ocr"))

#: 200 DPI is the sweet spot measured here: 150 loses small print, 300 doubles
#: the time for no accuracy gain on book scans.
OCR_DPI = int(os.getenv("MOSKY_OCR_DPI", 200))

_ENGINE = None


def _worker_init():
    """One OCR engine per process — loading it costs ~1s, so never per page."""
    global _ENGINE
    from rapidocr_onnxruntime import RapidOCR
    _ENGINE = RapidOCR()


def _ocr_page(args) -> tuple:
    """Render one page to an image and read it. Runs inside a worker process."""
    pdf_path, page_no, dpi = args
    global _ENGINE
    if _ENGINE is None:
        _worker_init()
    try:
        import numpy as np
        import pymupdf as fitz
        with fitz.open(pdf_path) as doc:
            page = doc[page_no - 1]
            pix = page.get_pixmap(dpi=dpi)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n)
            if pix.n == 4:                      # drop alpha, OCR expects RGB
                img = img[:, :, :3]
        res, _ = _ENGINE(img)
        text = "\n".join(r[1] for r in res) if res else ""
        return page_no, text, ""
    except Exception as e:
        return page_no, "", f"{type(e).__name__}: {e}"


def available() -> bool:
    try:
        import rapidocr_onnxruntime  # noqa: F401
        return True
    except Exception:
        return False


def _cache_path(pdf_path: str) -> Path:
    key = hashlib.sha1(
        f"{os.path.abspath(pdf_path)}::{os.path.getmtime(pdf_path)}::{OCR_DPI}"
        .encode()).hexdigest()[:16]
    OCR_CACHE.mkdir(parents=True, exist_ok=True)
    return OCR_CACHE / f"{key}.ocr.json"


def load_cache(pdf_path: str) -> Dict[int, str]:
    f = _cache_path(pdf_path)
    if not f.exists():
        return {}
    try:
        return {int(k): v for k, v in json.loads(f.read_text(encoding="utf-8")).items()}
    except Exception:
        return {}


def ocr_pdf(pdf_path: str, pages: Optional[List[int]] = None,
            workers: int = 0, dpi: int = OCR_DPI,
            progress_every: int = 25) -> Dict[int, str]:
    """OCR a scanned PDF, in parallel, resumable. Returns {page_number: text}.

    Only pages that are not already cached are processed, so calling this again
    after an interruption costs only what is left.
    """
    if not available():
        raise RuntimeError(
            "OCR engine missing. Install it with:\n"
            "  C:\\AI\\ai-env\\Scripts\\python.exe -m pip install rapidocr-onnxruntime")

    import pymupdf as fitz
    with fitz.open(pdf_path) as d:
        total = d.page_count
    pages = pages or list(range(1, total + 1))

    cache = load_cache(pdf_path)
    todo = [p for p in pages if p not in cache]
    if not todo:
        log.info(f"OCR: all {len(pages)} pages already cached")
        return {p: cache[p] for p in pages}

    # Serial by default: measured, extra workers give no speedup and cause
    # ONNXRuntimeError. workers>1 stays available but is not the default.
    workers = workers or 1
    est_min = estimate_minutes(len(todo), workers)
    log.info(f"OCR: {len(todo)} pages to read ({len(cache)} cached), "
             f"~{est_min:.0f} min estimated")

    cache_file = _cache_path(pdf_path)
    done, started, errors = 0, time.time(), 0

    def _flush():
        try:
            cache_file.write_text(
                json.dumps({str(k): v for k, v in cache.items()},
                           ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _record(page_no, text, err, retry_ok=True):
        nonlocal done, errors
        if err and retry_ok:
            # One retry: the observed failures were transient contention, and a
            # silently blank page in the middle of a book is worse than 2s lost.
            page_no, text, err = _ocr_page((str(pdf_path), page_no, dpi))
        if err:
            errors += 1
            log.warning(f"OCR page {page_no}: {err}")
        cache[page_no] = text
        done += 1
        if done % progress_every == 0 or done == len(todo):
            rate = done / max(0.1, time.time() - started)
            left = (len(todo) - done) / max(0.01, rate) / 60
            log.info(f"  OCR {done}/{len(todo)} ({100 * done // len(todo)}%) "
                     f"~{left:.0f} min left")
            _flush()

    if workers > 1:
        try:
            args = [(str(pdf_path), p, dpi) for p in todo]
            with ProcessPoolExecutor(max_workers=workers,
                                     initializer=_worker_init) as ex:
                futures = {ex.submit(_ocr_page, a): a[1] for a in args}
                for fut in as_completed(futures):
                    _record(*fut.result())
        except Exception as e:
            # ProcessPool needs an importable __main__, which does not exist in
            # a REPL, a notebook, or a `python -` invocation. Falling back keeps
            # the feature working instead of losing the whole book.
            log.warning(f"OCR: process pool unavailable ({e}); running serially")
            workers = 1

    if workers == 1:
        _worker_init()
        for p in todo:
            if p in cache:
                continue
            _record(*_ocr_page((str(pdf_path), p, dpi)))

    try:
        cache_file.write_text(json.dumps({str(k): v for k, v in cache.items()},
                                         ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        log.warning(f"OCR cache write failed: {e}")

    got = sum(1 for p in pages if cache.get(p, "").strip())
    log.info(f"OCR done in {(time.time()-started)/60:.1f} min — "
             f"{got}/{len(pages)} pages produced text, {errors} errors")
    return {p: cache.get(p, "") for p in pages}


def estimate_minutes(page_count: int, workers: int = 1) -> float:
    """Measured 2.1 s/page on this machine. Parallelism does not help."""
    return page_count * 2.1 / 60 / max(1, workers)


__all__ = ["ocr_pdf", "available", "load_cache", "estimate_minutes", "OCR_DPI"]
