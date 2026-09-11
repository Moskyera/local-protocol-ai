"""`python -m voice_agent [--text] [--no-mcp]`"""

import argparse
import sys

from .agent import Agent


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="voice_agent")
    ap.add_argument("--text", action="store_true", help="keyboard in, text out; no audio devices")
    ap.add_argument("--no-mcp", action="store_true", help="local tools only")
    ap.add_argument("--say", metavar="TEXT", help="speak TEXT once and exit (tests the voice)")
    a = ap.parse_args(argv)

    if a.say:
        from . import brain
        from .tts import Speaker
        Speaker().say(a.say, brain.detect_lang(a.say))
        return 0

    if a.text:
        # no speaker: everything that would have been spoken is printed
        agent = Agent(voice=False, with_mcp=not a.no_mcp,
                      say=lambda text, lang: print(f"{lang}> {text}", flush=True))
        agent.run_text()
    else:
        Agent(voice=True, with_mcp=not a.no_mcp).run_voice()
    return 0


if __name__ == "__main__":
    sys.exit(main())
