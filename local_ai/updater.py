"""Check whether a newer Local Protocol AI has been released, and show what changed.

Runs on every startup, so three properties matter more than features:

  1. It NEVER blocks the boot. Every network call is bounded and every failure
     is swallowed into "could not check" — a machine with no internet, or
     GitHub having a bad day, must not stop the stack from starting.
  2. It NEVER lies. If it cannot reach the release feed it says so, rather
     than printing "you are up to date", which is the same class of bug this
     project spent a long time removing from its own agents.
  3. It asks GitHub at most once an hour, cached on disk, because the launcher
     may be run several times in a row while debugging something else.

Public API:

    check(repo="owner/name", current="1.2.0") -> Update | None
    render(update) -> str        # the table shown at startup

No third-party dependencies: urllib only, so it works before pip install.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

__all__ = ["Update", "check", "render", "current_version",
           "default_repo", "VERSION_FILE"]

#: Where the running version is recorded. One line, e.g. "1.4.0".
VERSION_FILE = Path(__file__).resolve().parent.parent / "VERSION"

#: Cache of the last successful check, so repeated launches stay silent.
CACHE_FILE = Path(
    os.getenv("LOCAL_AI_UPDATE_CACHE",
              Path(__file__).resolve().parent.parent / ".update_cache.json"))

#: How long a successful check stays fresh.
CACHE_SECONDS = int(os.getenv("LOCAL_AI_UPDATE_INTERVAL", "3600"))

#: Bounded so a hanging endpoint cannot delay startup.
TIMEOUT = float(os.getenv("LOCAL_AI_UPDATE_TIMEOUT", "4"))

#: Empty on purpose. With no git remote and no LOCAL_AI_REPO there is
#: nothing authoritative to check against, and guessing a repo name only
#: produces a 404 warning about the guess. Silence is the honest answer.
DEFAULT_REPO = ""

_SEMVER = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")


@dataclass
class Update:
    """A newer release than the one running."""

    current: str
    latest: str
    published: str = ""
    url: str = ""
    #: One entry per release between current and latest, newest first.
    releases: List[dict] = field(default_factory=list)
    #: Set when the check could not be completed. `latest` is then meaningless.
    error: str = ""

    @property
    def available(self) -> bool:
        return bool(self.latest) and not self.error and _newer(self.latest, self.current)


def _parse(v: str):
    """(major, minor, patch) or None. Anything unparseable sorts as unknown."""
    m = _SEMVER.match((v or "").strip())
    return tuple(int(g) for g in m.groups()) if m else None


def _newer(candidate: str, than: str) -> bool:
    a, b = _parse(candidate), _parse(than)
    if a is None or b is None:
        # Never claim an update on a version we cannot read. Saying nothing is
        # correct; guessing would put a false banner in front of every boot.
        return False
    return a > b


def current_version(default: str = "0.0.0") -> str:
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip() or default
    except Exception:
        return default


def default_repo() -> str:
    """Which GitHub repo to check, in order of authority.

    Reading the git remote means a plain `git clone` is configured correctly
    with no setup at all, and a fork checks its own releases rather than
    silently offering someone else's. LOCAL_AI_REPO overrides for anyone
    running from a tarball or a mirror.
    """
    env = os.getenv("LOCAL_AI_REPO", "").strip()
    if env:
        return env

    try:
        import subprocess
        root = Path(__file__).resolve().parent.parent
        url = subprocess.run(
            ["git", "-C", str(root), "config", "--get", "remote.origin.url"],
            capture_output=True, text=True, timeout=5).stdout.strip()
        m = re.search(r"[:/]([\w.-]+)/([\w.-]+?)(?:\.git)?$", url)
        if m:
            return f"{m.group(1)}/{m.group(2)}"
    except Exception:
        pass

    return DEFAULT_REPO


def _read_cache() -> Optional[dict]:
    try:
        d = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        if time.time() - float(d.get("checked_at", 0)) < CACHE_SECONDS:
            return d
    except Exception:
        pass
    return None


def _write_cache(payload: dict) -> None:
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(payload, checked_at=time.time())
        CACHE_FILE.write_text(json.dumps(payload), encoding="utf-8")
    except Exception:
        pass          # a cache that cannot be written is not worth a failure


def _fetch(url: str) -> list:
    req = urllib.request.Request(
        url, headers={"Accept": "application/vnd.github+json",
                      "User-Agent": "local-ai-updater"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        data = json.loads(r.read().decode("utf-8", "replace"))
    return data if isinstance(data, list) else [data]


def update_check_enabled() -> bool:
    """Off in private mode (lpai_private sets LOCAL_AI_UPDATE_CHECK=0): even
    a GET to GitHub tells GitHub the machine is running this."""
    return os.getenv("LOCAL_AI_UPDATE_CHECK", "1").strip().lower() not in ("0", "false", "no", "off")


def check(repo: str, current: Optional[str] = None, *,
          force: bool = False) -> Optional[Update]:
    """Is there a newer release than `current`?

    Returns None when the running version is the newest — the common case, and
    the one that must print nothing. Returns an Update with `.error` set when
    the check could not be made, so the caller can say "could not check"
    instead of "up to date".
    """
    if not repo:
        return None       # unconfigured: nothing to check, so say nothing

    current = current or current_version()

    if not force:
        cached = _read_cache()
        if cached and cached.get("repo") == repo:
            if cached.get("error"):
                return None          # a stale failure is not worth re-reporting
            if not _newer(cached.get("latest", ""), current):
                return None
            return Update(current=current, latest=cached.get("latest", ""),
                          published=cached.get("published", ""),
                          url=cached.get("url", ""),
                          releases=cached.get("releases", []))

    try:
        raw = _fetch(f"https://api.github.com/repos/{repo}/releases?per_page=20")
    except urllib.error.HTTPError as e:
        return Update(current=current, latest="", error=f"HTTP {e.code}")
    except Exception as e:
        return Update(current=current, latest="", error=type(e).__name__)

    rels = [r for r in raw
            if isinstance(r, dict) and not r.get("draft") and not r.get("prerelease")]
    if not rels:
        _write_cache({"repo": repo, "latest": current, "releases": []})
        return None

    newest = rels[0]
    latest = str(newest.get("tag_name", "")).lstrip("v")

    # Everything strictly between what is running and what is newest, so a user
    # who skipped three releases sees all three rather than only the last.
    between = [
        {"version": str(r.get("tag_name", "")).lstrip("v"),
         "published": str(r.get("published_at", ""))[:10],
         "notes": str(r.get("body") or "").strip(),
         "url": str(r.get("html_url", ""))}
        for r in rels
        if _newer(str(r.get("tag_name", "")).lstrip("v"), current)
    ]

    _write_cache({"repo": repo, "latest": latest,
                  "published": str(newest.get("published_at", ""))[:10],
                  "url": str(newest.get("html_url", "")),
                  "releases": between})

    if not _newer(latest, current):
        return None
    return Update(current=current, latest=latest,
                  published=str(newest.get("published_at", ""))[:10],
                  url=str(newest.get("html_url", "")), releases=between)


# --------------------------------------------------------------------------- #
# Rendering                                                                    #
# --------------------------------------------------------------------------- #

#: A startup banner has to fit on the screen above everything else the boot
#: prints. Rendering four releases of six unabridged bullets each produced an
#: 80-line wall that nobody would read. These caps are deliberately tight, and
#: whatever they cut is COUNTED and reported rather than silently dropped.
MAX_RELEASES = 3
MAX_BULLETS = 3
MAX_BULLET = 120        # ~2 wrapped lines at the default width


def _bullets(notes: str, limit: Optional[int] = None) -> List[str]:
    """The changelog lines worth showing, from a release body.

    Release bodies carry headings, a contributors list and a compare link.
    Only the actual change lines are useful in a startup banner.
    """
    # GitHub's generated bodies open with an HTML comment naming the config
    # file that produced them. It is not a change, and it was the first line
    # shown in the banner.
    notes = re.sub(r"<!--.*?-->", "", notes or "", flags=re.S)

    # Everything after a contributors or changelog heading is credits and
    # links, not changes — so STOP there rather than filtering line by line.
    # Filtering only the heading left the "- @someone" entries beneath it.
    stop = re.search(r"^#{1,6}\s*(new contributors|full changelog)",
                     notes, re.I | re.M)
    if stop:
        notes = notes[:stop.start()]

    out = []
    for raw in notes.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "<!--", "-->")):
            continue
        if line.lower().startswith(("**full changelog", "full changelog",
                                    "new contributors", "what's changed")):
            continue
        if re.fullmatch(r"[-*+]?\s*@[\w-]+", line):
            continue
        line = re.sub(r"^[-*+]\s+", "", line)
        line = re.sub(r"\s+by\s+@\S+\s+in\s+https?://\S+$", "", line)

        # Collapse markdown links to their text BEFORE removing bare URLs.
        # The other order strips the target first and leaves the wreckage
        # behind: "[#14220](https://…)" became the literal "[\#14220](".
        line = re.sub(r"\[([^\]]*)\]\([^)]*\)", lambda m: m.group(1), line)
        line = re.sub(r"https?://\S+", "", line)

        # Release bodies are rendered HTML as often as markdown, and a raw
        # <span class="title-ref"> in a terminal banner is just noise.
        line = re.sub(r"<[^>]{1,200}>", "", line)
        line = re.sub(r"\*\*(.+?)\*\*", lambda m: m.group(1), line)
        line = re.sub(r"[`*_]", "", line)
        line = re.sub(r"\\(.)", lambda m: m.group(1), line)   # \# -> #
        line = re.sub(r"\s{2,}", " ", line).strip(" .,;:")

        if len(line) < 3:
            continue
        if len(line) > MAX_BULLET:
            line = line[:MAX_BULLET].rsplit(" ", 1)[0] + " …"
        out.append(line)
        if limit is not None and len(out) >= limit:
            break
    return out


def render(update: Optional[Update], width: int = 74) -> str:
    """The table shown at startup. Empty string when there is nothing to say."""
    if update is None:
        return ""

    bar = "─" * width
    w = width - 1

    if update.error:
        return "\n".join([
            f"┌{bar}┐",
            _cell("⚠  Could not check for updates", w),
            _cell(f"   {update.error} — this is NOT a statement that you are", w),
            _cell("   up to date, only that the check did not complete.", w),
            f"└{bar}┘",
        ])

    lines = [f"┌{bar}┐",
             _cell(f"🆕  Local Protocol AI {update.latest} is available", w),
             _cell(f"    you are running {update.current}"
                   f"   ·   released {update.published or 'recently'}", w),
             f"├{bar}┤"]

    for rel in update.releases[:MAX_RELEASES]:
        lines.append(_cell(f"  {rel['version']}  ({rel['published']})", w))
        pts = _bullets(rel["notes"])
        if not pts:
            lines.append(_cell("    (no release notes)", w))
        for point in pts[:MAX_BULLETS]:
            chunks = _wrap(point, width - 10)
            for n, chunk in enumerate(chunks):
                lines.append(_cell(("    • " if n == 0 else "      ") + chunk, w))
        # Say what was cut. A banner that quietly shows three of eleven changes
        # reads as "that's all of them", which is the exact failure this
        # project has been removing everywhere else.
        if len(pts) > MAX_BULLETS:
            lines.append(_cell(f"    … {len(pts) - MAX_BULLETS} more change(s) "
                               f"in this release", w))
        lines.append(_cell("", w))

    if len(update.releases) > MAX_RELEASES:
        lines.append(_cell(f"  … and {len(update.releases) - MAX_RELEASES} "
                           f"earlier release(s) not shown", w))

    if update.url:
        lines.append(f"├{bar}┤")
        lines.append(_cell(f"  {update.url}", w))
    lines.append(f"└{bar}┘")
    return "\n".join(lines)


def _dw(text: str) -> int:
    """Display width in terminal columns. len() is not it.

    Two rules, both learned from the banner rendering visibly crooked:

      * An emoji with default emoji presentation (U+1F300 and above) takes two
        columns, and len() says one.
      * A symbol like U+26A0 WARNING SIGN does NOT. It is East-Asian-Neutral
        and terminals render it in one column unless it is followed by
        U+FE0F, the variation selector that requests emoji presentation.
        Counting the whole 0x2600-0x27BF block as wide made every line
        carrying it one column short.
    """
    import unicodedata
    w = 0
    for ch in text:
        cp = ord(ch)
        if ch == "️":
            w += 1            # VS16 widens the character before it
            continue
        if unicodedata.combining(ch):
            continue
        if unicodedata.east_asian_width(ch) in ("W", "F"):
            w += 2
        elif 0x1F300 <= cp <= 0x1FAFF:
            w += 2            # emoji presentation by default
        else:
            w += 1
    return w


def _cell(text: str, width: int) -> str:
    """One boxed line, padded to `width` display columns."""
    pad = max(0, width - _dw(text))
    return f"│ {text}{' ' * pad}│"


def _wrap(text: str, width: int) -> List[str]:
    words, line, out = text.split(), "", []
    for w in words:
        if len(line) + len(w) + 1 > width:
            if line:
                out.append(line)
            line = w[:width]
        else:
            line = f"{line} {w}".strip()
    if line:
        out.append(line)
    return out or [""]


if __name__ == "__main__":       # pragma: no cover - manual use
    import sys
    repo = sys.argv[1] if len(sys.argv) > 1 else os.getenv("LOCAL_AI_REPO", "")
    if not repo:
        print("usage: python -m local_ai.updater <owner/repo> [current-version]")
        raise SystemExit(2)
    cur = sys.argv[2] if len(sys.argv) > 2 else current_version()
    banner = render(check(repo, cur, force=True))
    print(banner or f"Local Protocol AI {cur} — up to date.")
