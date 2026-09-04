"""
safe_paths - path jail για ό,τι γράφει ο agent στον δίσκο.

ΓΙΑΤΙ ΞΕΧΩΡΙΣΤΟ MODULE: το `guards.is_forbidden_path` είναι substring blacklist —
επιστρέφει False για C:/Windows/System32/... και ταυτόχρονα false-positive σε κάθε
νόμιμο slug που τυχαίνει να περιέχει "briefing". Δεν είναι jail.

Η σωστή προσέγγιση είναι CONTAINMENT: κάνε resolve() και απαίτησε το target να
βρίσκεται ΜΕΣΑ στο PROJECTS_ROOT. Επειδή το PROJECTS_ROOT είναι εντελώς εκτός του
market-agent, τα απαγορευμένα αρχεία (telegram_engine.py, master_market_brain.py,
τα 6 briefing engines, send_*.bat) είναι απροσπέλαστα εξ ορισμού.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# Generated sites live OUTSIDE this repository, on purpose: the agents write
# arbitrary code into them, and that code must never be able to reach the
# briefing engines, the launchers or the .env sitting next to them.
#
# The default is a SIBLING of the repository rather than an absolute path, so
# a clone at D:\projects\local-ai writes to D:\projects\generated_sites instead
# of to whatever C:\AI happens to be on someone else's machine.
_REPO_ROOT = Path(__file__).resolve().parent.parent

PROJECTS_ROOT = Path(
    os.getenv("MOSKY_SITES_ROOT") or (_REPO_ROOT.parent / "generated_sites")
).resolve()

# Containment, not a name match. The old check looked for the literal string
# "market-agent" in the path, which silently stopped protecting anything the
# moment the directory was renamed or cloned under another name.
if PROJECTS_ROOT == _REPO_ROOT or _REPO_ROOT in PROJECTS_ROOT.parents:
    raise RuntimeError(
        f"MOSKY_SITES_ROOT ({PROJECTS_ROOT}) is inside the repository "
        f"({_REPO_ROOT}). It must be disjoint, so generated code can never "
        f"touch the engines, the launchers or your .env."
    )

SLUG_RE = re.compile(r"^[a-z][a-z0-9-]{1,40}$")
IDENT_RE = re.compile(r"^[a-z][a-z0-9_]{0,30}$")

# Windows eats these: a file named NUL silently writes to the null device and
# looks like it succeeded.
_RESERVED = {
    "con", "prn", "aux", "nul", "clock$",
    *{f"com{i}" for i in range(1, 10)},
    *{f"lpt{i}" for i in range(1, 10)},
}


class UnsafePath(ValueError):
    """Raised when a requested path escapes the jail or is invalid on Windows."""


def valid_slug(slug: str) -> bool:
    return bool(SLUG_RE.match(slug or ""))


def valid_identifier(name: str) -> bool:
    """For table/column/module names — these flow into file paths and SQL."""
    return bool(IDENT_RE.match(name or "")) and (name or "").lower() not in _RESERVED


def _reject_component(part: str) -> None:
    low = part.lower()
    stem = low.split(".")[0]
    if stem in _RESERVED:
        raise UnsafePath(f"reserved Windows device name: {part!r}")
    if part != part.strip() or part.endswith("."):
        raise UnsafePath(f"trailing dot/space in path component: {part!r}")
    if ":" in part:
        raise UnsafePath(f"alternate data stream / drive spec in component: {part!r}")


def safe_join(root: Path, rel: str) -> Path:
    """Resolve `rel` under `root` and prove containment, or raise.

    Resolution happens BEFORE the comparison so '..', symlinks and NTFS
    junctions cannot escape.
    """
    rel = (rel or "").replace("\\", "/").strip()
    if not rel:
        raise UnsafePath("empty relative path")
    if rel.startswith("/") or re.match(r"^[a-zA-Z]:", rel) or rel.startswith("//"):
        raise UnsafePath(f"absolute/UNC path not allowed: {rel!r}")

    for part in rel.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            raise UnsafePath("parent traversal ('..') not allowed")
        _reject_component(part)

    root = Path(root).resolve()
    target = (root / rel).resolve()
    try:
        if os.path.commonpath([str(target), str(root)]) != str(root):
            raise UnsafePath(f"path escapes project root: {target}")
    except ValueError:  # different drives
        raise UnsafePath(f"path on a different drive than the project root: {target}")
    return target


def project_dir(slug: str, overwrite: bool = False) -> Path:
    """Pick the output directory for a site, never clobbering existing work.

    With overwrite=False (default) an existing non-empty dir yields slug-2,
    slug-3, ... so the user's previous project survives.
    """
    if not valid_slug(slug):
        raise UnsafePath(f"invalid project slug: {slug!r} (want ^[a-z][a-z0-9-]{{1,40}}$)")
    PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)

    base = PROJECTS_ROOT / slug
    if overwrite or not base.exists() or not any(base.iterdir()):
        base.mkdir(parents=True, exist_ok=True)
        return base

    for n in range(2, 100):
        cand = PROJECTS_ROOT / f"{slug}-{n}"
        if not cand.exists() or not any(cand.iterdir()):
            cand.mkdir(parents=True, exist_ok=True)
            return cand
    raise UnsafePath(f"too many existing projects named {slug!r}")


def write_file(root: Path, rel: str, content: str) -> Path:
    """Jailed write. Creates parent dirs inside the jail only."""
    target = safe_join(root, rel)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="\n")
    return target


__all__ = [
    "PROJECTS_ROOT", "UnsafePath", "safe_join", "project_dir", "write_file",
    "valid_slug", "valid_identifier",
]
