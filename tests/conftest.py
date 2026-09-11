"""Every test runs in PRIVATE MODE.

A test that reaches the internet is a bug: it was found once (a briefing
test fetched api.tavily.com for real, with the owner's query, every time the
suite ran). With the egress guard installed here, such a test fails loudly
with EgressBlocked instead of quietly leaking. Loopback still works, so
tests that talk to a local llama-server or a fake HTTP server are fine.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["LPAI_PRIVATE"] = "1"
import lpai_private  # noqa: E402

lpai_private.activate()
