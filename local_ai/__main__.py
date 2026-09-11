"""``python -m local_ai`` — the startup update check.

The launchers call this before anything heavy starts. It prints the table when
there is something to say, prints NOTHING otherwise, and always exits 0: a
failed update check must never be the reason the stack does not boot.
"""

from __future__ import annotations

import sys

from . import updater

#: Box drawing and emoji, mapped to ASCII of the SAME display width so the
#: table stays square. Used only when stdout cannot encode them — that happens
#: when the launcher's output is piped to a file rather than a console.
_ASCII = {
    "─": "-", "│": "|",
    "┌": "+", "┐": "+", "└": "+", "┘": "+",
    "├": "+", "┤": "+",
    "\U0001f195": "**",   # occupies two columns
    "⚠": "!!",            # likewise
    "•": "*", "…": ".", "·": "-",
}


def to_ascii(text: str) -> str:
    """Same banner, same column widths, characters a code page can print."""
    return "".join(_ASCII.get(ch, ch) for ch in text)


def main(argv=None) -> int:
    import lpai_private
    lpai_private.apply_env()
    from .updater import update_check_enabled
    if not update_check_enabled():
        print("update check off (private mode)")
        return 0
    argv = list(sys.argv[1:] if argv is None else argv)
    repo = argv[0] if argv else updater.default_repo()

    try:
        banner = updater.render(updater.check(repo, updater.current_version()))
    except Exception:
        return 0          # nothing in here is worth blocking a boot for

    if not banner:
        return 0

    try:
        print(banner)
    except UnicodeEncodeError:
        print(to_ascii(banner))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
