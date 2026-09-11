"""Refuse to publish while anything personal, unsafe or unfinished is in the tree.

Run this immediately before creating the public repository:

    python scripts/check_publication_ready.py

It exits non-zero on the first category that fails. Nothing here is advisory:
every check corresponds to something that was actually wrong in this tree
before the first release, found by a thirteen-agent audit on 2026-09-04.

It NEVER prints a secret value. When it finds one it names the file, the line
and the kind, because a checker that leaks what it found is worse than none.

What it CANNOT check, stated plainly rather than left implied:

  * Whether a value in .env was ever pushed somewhere else. Nothing local can
    see that. If a key has ever left this machine, rotate it.
  * Whether the git HISTORY is clean. This looks at the working tree only.
    The plan is a fresh repository with no history, precisely because commit
    #1 of the current one added a .env holding six real credentials, and a
    key removed in a later commit is still served by GitHub forever.
  * Whether the README is TRUE. A person has to read it.
"""

from __future__ import annotations

import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Files that may legitimately sit untracked next to the repo when publishing.
ALLOWED_UNTRACKED: set = set()

GREEN, RED, YELLOW, DIM, OFF = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"


class Report:
    def __init__(self) -> None:
        self.failures: list = []
        self.warnings: list = []

    def ok(self, what: str, detail: str = "") -> None:
        print(f"  {GREEN}pass{OFF}  {what}" + (f"  {DIM}{detail}{OFF}" if detail else ""))

    def fail(self, what: str, detail: str) -> None:
        print(f"  {RED}FAIL{OFF}  {what}")
        for line in str(detail).splitlines():
            print(f"        {line}")
        self.failures.append(what)

    def warn(self, what: str, detail: str = "") -> None:
        print(f"  {YELLOW}warn{OFF}  {what}" + (f"  {DIM}{detail}{OFF}" if detail else ""))
        self.warnings.append(what)


def git(*args) -> str:
    return subprocess.run(["git", "-C", ROOT, *args],
                          capture_output=True, text=True).stdout


def tracked() -> list:
    return [f for f in git("ls-files").splitlines() if f.strip()]


def read(rel: str) -> str:
    try:
        with io.open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


# --------------------------------------------------------------------------- #

def check_the_repository_has_what_a_public_one_needs(r: Report) -> None:
    print("\nWhat a public repository needs")

    files = tracked()

    if "LICENSE" not in files:
        r.fail("LICENSE is tracked",
               "Without one, default copyright applies and nobody may legally\n"
               "use, fork or run it — which defeats the point of publishing.")
    else:
        text = read("LICENSE")
        placeholder = re.search(r"NAME_PENDING|<your name>|YOUR NAME|\bTODO\b", text)
        if placeholder:
            r.fail("LICENSE names a copyright holder",
                   f"still contains the placeholder {placeholder.group(0)!r}")
        else:
            r.ok("LICENSE is tracked and filled in")

    if "README.md" not in files:
        r.fail("README.md is tracked",
               "The landing page. Without it the first thing a visitor sees is\n"
               "a file listing of 300 files.")
    else:
        r.ok("README.md is tracked", f"{len(read('README.md').splitlines())} lines")

    if ".env.example" not in files:
        r.fail(".env.example is tracked",
               "Nobody can configure this without knowing the key names.")
    else:
        r.ok(".env.example is tracked")


def check_no_credentials_leave_the_machine(r: Report) -> None:
    print("\nCredentials")

    if ".env" in tracked():
        r.fail(".env is NOT tracked", "it is in the index — remove it before publishing")
        return
    r.ok(".env is not tracked")

    if subprocess.run(["git", "-C", ROOT, "check-ignore", "-q", ".env"]).returncode != 0:
        r.fail(".env is covered by .gitignore", "it is not, so it can be added by accident")
    else:
        r.ok(".env is covered by .gitignore")

    # Read the real values so the scan looks for THESE secrets, not for a
    # guess at what a secret looks like. Values are never printed.
    # Only the keys that actually carry a credential. .env also holds ordinary
    # configuration — a model name, a base URL, the documented dummy key — and
    # those appear all over the tree by design. Flagging them buries the four
    # values that would matter under forty that do not.
    secretish = re.compile(r"(_TOKEN|_SECRET|_PASSWORD|_API_KEY|_KEY)$|^TELEGRAM_.*_ID$")
    not_secret = {"sk-dummy-local", "local-llm", "dummy", "changeme", "none"}

    real = {}
    for line in read(".env").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip("\"'")
        if not secretish.search(k):
            continue
        if v.lower() in not_secret or v.startswith(("http://", "https://")):
            continue
        if len(v) >= 8:
            real[k] = v

    if not real:
        r.warn("no .env found to scan against",
               "the value scan below cannot run, so it proves nothing")
    else:
        hits = []
        for f in tracked():
            body = read(f)
            for name, value in real.items():
                if value and value in body:
                    hits.append(f"{f}: the value of {name}")
        if hits:
            r.fail("no real credential value appears in a tracked file",
                   "\n".join(hits))
        else:
            r.ok("no real credential value appears in a tracked file",
                 f"{len(real)} values checked across {len(tracked())} files")


def check_nothing_points_at_the_author(r: Report) -> None:
    print("\nPersonal data")

    patterns = [
        ("this machine's user directory", re.compile(r"C:[\\/]+Users[\\/]+KQHEX", re.I)),
        ("a Telegram chat or channel id",
         re.compile(r"TELEGRAM_(?:CHANNEL|CHAT)_ID\s*[=:]\s*[\"']?(-\d{9,})")),
    ]
    PLACEHOLDER = "-1001234567890"

    for label, pat in patterns:
        hits = []
        for f in tracked():
            for m in pat.finditer(read(f)):
                if m.groups() and m.group(1) == PLACEHOLDER:
                    continue
                hits.append(f)
                break
        if hits:
            r.fail(f"no tracked file contains {label}", "\n".join(sorted(set(hits))))
        else:
            r.ok(f"no tracked file contains {label}")

    email = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
    found = {}
    for f in tracked():
        for addr in email.findall(read(f)):
            if addr.endswith((".invalid", ".example", "example.com")) or "@" not in addr:
                continue
            if addr.startswith(("noreply@", "support@", "info@", "hello@")):
                continue
            found.setdefault(addr, []).append(f)
    if found:
        r.warn(f"{len(found)} email address(es) appear in tracked files",
               "check these are meant to be public: "
               + ", ".join(sorted(found)[:4]))
    else:
        r.ok("no personal email address in tracked files")


def check_nothing_unintended_gets_swept_in(r: Report) -> None:
    print("\nWhat would be committed")

    untracked = [l[3:].strip().strip('"') for l in git("status", "--porcelain", "-uall").splitlines()
                 if l.startswith("??")]
    unexpected = [f for f in untracked if f not in ALLOWED_UNTRACKED]
    if unexpected:
        r.fail(f"{len(unexpected)} untracked file(s) match no .gitignore rule",
               "A `git add .` would publish these:\n"
               + "\n".join(f"  {f}" for f in unexpected[:15])
               + (f"\n  ... and {len(unexpected) - 15} more" if len(unexpected) > 15 else ""))
    else:
        r.ok("nothing untracked would be swept in")

    contradicted = []
    for line in git("ls-files").splitlines():
        if not line.strip():
            continue
        res = subprocess.run(["git", "-C", ROOT, "check-ignore", "--no-index", "-q", line])
        if res.returncode == 0 and line != ".env.example":
            contradicted.append(line)
    if contradicted:
        r.warn(f"{len(contradicted)} tracked file(s) are also listed in .gitignore",
               "the ignore rule has no effect on them; do not carry them into the "
               "fresh repo: " + ", ".join(contradicted[:5]))
    else:
        r.ok("no tracked file contradicts .gitignore")


def check_the_guards_still_hold(r: Report) -> None:
    print("\nStructural guards")
    # the publication guards AND the privacy guards: a wallet address, a
    # memory file or an undocumented external host must never be pushed
    for suite in ("tests/test_publication_safety.py", "tests/test_privacy.py"):
        res = subprocess.run(
            [sys.executable, "-m", "pytest", suite, "-q"],
            cwd=ROOT, capture_output=True, text=True)
        last = [l for l in res.stdout.splitlines() if l.strip()][-1] if res.stdout else ""
        if res.returncode == 0:
            r.ok(suite, last.strip())
        else:
            r.fail(suite, res.stdout[-1500:])


def main() -> int:
    print("=" * 74)
    print("Local Protocol AI — pre-publication check")
    print("=" * 74)

    r = Report()
    check_the_repository_has_what_a_public_one_needs(r)
    check_no_credentials_leave_the_machine(r)
    check_nothing_points_at_the_author(r)
    check_nothing_unintended_gets_swept_in(r)
    check_the_guards_still_hold(r)

    print("\n" + "=" * 74)
    if r.failures:
        print(f"{RED}NOT READY{OFF} — {len(r.failures)} check(s) failed:")
        for f in r.failures:
            print(f"    - {f}")
    else:
        print(f"{GREEN}READY{OFF} — every check passed.")
    if r.warnings:
        print(f"\n{len(r.warnings)} warning(s) — read them, they are not failures:")
        for w in r.warnings:
            print(f"    - {w}")

    print("\nStill NOT covered by this script, and it cannot be:")
    print("  * Whether any key in .env has ever left this machine. Rotate if unsure.")
    print("  * The git HISTORY. This reads the working tree only, which is why the")
    print("    plan is a FRESH repository — commit #1 of this one added a .env.")
    print("  * Whether the README is true. Someone has to read it.")
    print("=" * 74)
    return 1 if r.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
