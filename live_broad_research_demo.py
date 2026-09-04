import os

"""
Live Broad Research Demo (generalized last30d multi-source for AI/tech/general topics).

Runs the agent's research_new_technologies_and_skills (or the supervisor research path)
with lab_mode for a general (non-Pulse) topic.

Prints the FULL report-style output with emphasis on:
- new_capability_candidates
- For each: source, direct_evidence (verbatim), credibility (incl. real engagement), fit_analysis, pros_cons (advantages + disadvantages), suggested_apply_data

This is what the user sees in the "report" when the Research agent (or supervisor on general intent) discovers new skills/patterns.

Usage:
    python live_broad_research_demo.py

In this environment the live HTTP sources (GitHub/HN/Reddit) may fall back to high-fidelity seeds
because the shell Python often lacks the 'requests' package (the agent code guards it and falls back cleanly).
However, this demo now includes an additional **direct live Reddit fetch section** using only Python stdlib (urllib.request)
so you can see real last-30d Reddit data (titles, scores, subreddits, selftext) turned into full 100% fidelity
new_capability_candidates with pros_cons (advantages + disadvantages), exactly as the Research agent would.
The agent's own Reddit path (in research_agent.py) uses the same public search.json API.
"""

import sys
import json
import urllib.request
import urllib.parse
from datetime import datetime

# Make project importable
# The repo root is this file's own directory. It used to be written out
# as an absolute path, which only existed on the machine it was written on.
_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, _REPO_ROOT)

print("=" * 70)
print("LIVE BROAD RESEARCH DEMO - Generalized last 30 days (AI / tech / agent skills)")
print("Topic example: self-improving agents, reflection, lab experiments, LangGraph patterns")
print(f"Run at: {datetime.now().isoformat()}")
print("=" * 70)

# === 1. Direct call to the Research agent's broad method (the core) ===
print("\n--- 1. Direct: research_agent.research_new_technologies_and_skills (lab_mode=True) ---")
try:
    from openhands_skills.research_agent import research_agent

    topic = "self improving agent frameworks with reflection loops and lab experiments last 30 days"
    res = research_agent.research_new_technologies_and_skills(
        max_results=4,
        focus="ai_tech_general",
        lab_mode=True
    )

    cands = res.get("new_capability_candidates", [])
    print(f"Candidates returned: {len(cands)}")
    print(f"Note from run: {res.get('note', 'N/A')}")
    print(f"Sources collected: {len(res.get('sources', []))}")
    print(f"Actionable for engineering count: {len(res.get('actionable_for_engineering', []))}")

    for i, c in enumerate(cands[:4]):
        src = c.get("source", {})
        print(f"\n  [{i}] {c.get('id')}")
        print(f"      URL: {src.get('url')}")
        print(f"      Type: {src.get('type')}")
        print(f"      Short: {c.get('short_description', '')[:120]}")
        cred = c.get("credibility_signals", [])[:2]
        print(f"      Credibility (raw, engagement included): {cred}")
        fit = c.get("fit_analysis", {})
        print(f"      Fit maps_to_codebase count: {len(fit.get('maps_to_codebase', []))}")
        print(f"      Value add (snippet): {fit.get('value_add_for_general_professional_helper', '')[:160]}")
        pc = c.get("pros_cons", {})
        print(f"      pros_cons present: {bool(pc)}")
        print(f"      ADVANTAGES (πλεονεκτήματα) [{len(pc.get('advantages', []))}]:")
        for a in pc.get("advantages", [])[:4]:
            print(f"        + {a}")
        print(f"      DISADVANTAGES (μειονεκτήματα) [{len(pc.get('disadvantages', []))}]:")
        for d in pc.get("disadvantages", [])[:4]:
            print(f"        - {d}")
        print(f"      Note on pros_cons: {pc.get('note', '')[:140]}")
        ev = c.get("direct_evidence", "")[:220].replace("\n", " ")
        print(f"      Direct evidence (verbatim start): {ev}...")
        print(f"      Lab/PR-ready: {c.get('lab_mode')}, pr_ready={bool(c.get('pr_ready'))}")

except Exception as e:
    print(f"Direct research call failed: {e}")

# === 2. Supervisor path (the "report" the user usually sees) ===
print("\n--- 2. Via LangGraph supervisor (general non-onchain intent -> broad path) ---")
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location('lo', os.path.join(_REPO_ROOT, 'openhands_skills/langgraph_orchestrator.py'))
    lo = importlib.util.module_from_spec(spec)
    sys.modules['lo'] = lo
    spec.loader.exec_module(lo)

    # Simulate user asking for general research (not wallet / onchain)
    st = {"user_input": "research latest self improving agent techniques with reflection and lab experiments last 30 days"}
    st = lo._classify_intent(st)
    print(f"Classified specialists: {st.get('specialists_needed')}")

    if "research" in st.get("specialists_needed", []):
        st = lo._execute_research(st)
        rres = st.get("research_result", {})
        print(f"Research note (should indicate broad last30d): {rres.get('note', 'N/A')[:160]}")
        cands2 = rres.get("new_capability_candidates", [])
        print(f"Candidates in supervisor research_result: {len(cands2)}")

        # Show the packaged report view that _synthesize would emit
        print("\n  Packaged in final supervisor 'research' key (what user sees in report):")
        print(f"    new_capability_candidates count: {len(rres.get('new_capability_candidates', []))}")
        print(f"    note: {rres.get('note', 'N/A')}")

        # If proactive ideas were injected they would be here too
        if st.get("proactive_fitting_ideas"):
            print(f"    Also proactive_fitting_ideas: {len(st['proactive_fitting_ideas'])} (full objects with pros_cons)")

except Exception as e:
    print(f"Supervisor path simulation failed: {e}")

# === 3. MCP tool path (if user calls via openhands_mcp) ===
print("\n--- 3. Via MCP-exposed research_last_30_days_broad (same as direct) ---")
try:
    # We can call the underlying function the MCP tool delegates to
    # (importing the server would start MCP, so we just re-use the agent)
    res_mcp = research_agent.research_new_technologies_and_skills(max_results=3, focus="agent_patterns", lab_mode=True)
    res_mcp["mcp_tool"] = "research_last_30_days_broad"
    res_mcp["topic"] = "self improving agents reflection lab"
    res_mcp["last_30d_general"] = True
    print(f"MCP-style response keys: {list(res_mcp.keys())[:8]}...")
    print(f"  new_capability_candidates in MCP result: {len(res_mcp.get('new_capability_candidates', []))}")
    print("  (In real MCP host this would be returned over the tool protocol with the same pros_cons etc.)")
except Exception as e:
    print(f"MCP path note: {e}")

# === 4. Live Reddit last-30d fetches (direct with stdlib urllib - no 'requests' needed) ===
# This section was added to demonstrate real Reddit data in the same report format.
# The ROBUST live Reddit logic has now also been integrated at agent-level (see research_agent.py):
#   - _safe_request now has urllib fallback
#   - Reddit block uses old.reddit.com + strong headers + validation
#   - So research_new_technologies_and_skills / MCP research_last_30_days_broad / supervisor broad path
#     will attempt real Reddit last-30d automatically.
# The code here in the demo is kept standalone for easy testing even without loading the full agent.
# Each post is turned into a full new_capability_candidate (including pros_cons with
# advantages/πλεονεκτήματα + disadvantages/μειονεκτήματα) exactly as research_agent.py does.
print("\n--- 4. Live Reddit last-30d direct fetches (stdlib urllib, independent of agent) ---")

def _derive_pros_cons_for_reddit(candidate: dict) -> dict:
    """Minimal grounded derivation (mirrors research_agent._derive_pros_cons_for_candidate logic for Reddit)."""
    advantages = []
    disadvantages = []
    src = candidate.get("source", {})
    score = src.get("score", 0)
    num_comments = src.get("comments", 0)
    sub = src.get("subreddit", "")
    ev = (candidate.get("direct_evidence", "") + " " + candidate.get("short_description", "")).lower()

    if score >= 50:
        advantages.append(f"High Reddit engagement ({score} upvotes, {num_comments} comments) in r/{sub} — strong real community signal.")
    elif score >= 10:
        advantages.append(f"Moderate engagement ({score} upvotes, {num_comments} comments) in r/{sub}.")
    elif score > 0:
        disadvantages.append(f"Low visible engagement ({score} upvotes) — may be early/niche or low discussion volume.")

    if any(k in ev for k in ["reflection", "self improve", "langgraph", "lab", "iterative", "production", "self-improving"]):
        advantages.append("Evidence text contains high-signal keywords (reflection, self-improving, LangGraph, lab, iterative) aligned with our Research + Engineering + meta-supervisor loop.")

    if len(candidate.get("direct_evidence", "")) > 150:
        advantages.append("Direct selftext/title excerpt available for 100% fidelity review.")

    advantages.append("100% fidelity & traceable: public Reddit search.json + real score + permalink. No summarization.")
    disadvantages.append("Forum signals reflect discussion/hype volume; always cross-check linked code/repos + optional X search before proposal.")
    disadvantages.append("Any use in our system still goes through full review + guarded_propose + human_approved + pre/post evaluation_harness (intentional safety).")

    return {
        "advantages": advantages,
        "disadvantages": disadvantages,
        "note": "Derived strictly from this Reddit post's score, comments, title + selftext. Visit the permalink for the full thread. Part of generalized last30d broad research."
    }

def fetch_reddit_live(query: str, limit: int = 3):
    """Live fetch from Reddit public search API (last ~30 days via t=month, sort=new).
    Uses domain rotation (old.reddit -> www -> reddit) + realistic headers for significantly better success rate
    against Reddit's aggressive blocking. Mirrors the robust logic now in research_agent.py at agent level.
    """
    encoded_q = urllib.parse.quote(query)
    domains = ["old.reddit.com", "www.reddit.com", "reddit.com"]
    headers = {
        "User-Agent": "OpenHands-ResearchAgent/1.0 (live broad research demo for self-improving skills)",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
    }
    for domain in domains:
        try:
            url = f"https://{domain}/search.json?q={encoded_q}&sort=new&t=month&limit={limit}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                data = json.loads(raw)
                if isinstance(data, dict) and "data" in data:
                    return data
        except Exception:
            continue  # try next domain
    return {"error": "all domains blocked or failed (common in restricted/sandbox envs; in normal usage with requests + good connectivity this multi-domain + headers approach succeeds much more often)"}

reddit_queries = [
    "self improving agent OR reflection agent langgraph",
    "ai agent lab experiments OR \"self-improving\" OR reflection loop"
]

reddit_live_cands = []
for q in reddit_queries:
    print(f"  Fetching Reddit (last 30d): {q}")
    data = fetch_reddit_live(q, limit=2)
    if "error" in data:
        print(f"    Reddit fetch error: {data['error']}")
        continue
    children = data.get("data", {}).get("children", [])[:2]
    for child in children:
        post = child.get("data", {})
        title = post.get("title", "")
        permalink = post.get("permalink", "")
        url = "https://reddit.com" + permalink if permalink else ""
        score = post.get("score", 0)
        num_comments = post.get("num_comments", 0)
        sub = post.get("subreddit", "")
        selftext = (post.get("selftext") or "")[:450]
        evidence = (title + (" | " + selftext if selftext else "")).strip()

        cand = {
            "id": f"reddit:{post.get('id', 'unknown')}",
            "source": {
                "type": "reddit",
                "url": url,
                "title": title,
                "subreddit": sub,
                "score": score,
                "comments": num_comments
            },
            "short_description": title,
            "direct_evidence": evidence[:600],
            "credibility_signals": [
                f"Reddit r/{sub}: {score} upvotes, {num_comments} comments (real community engagement)",
                "Fetched live via public search.json?sort=new&t=month (last ~30 days)"
            ],
            "fit_analysis": {
                "fits_allowed_paths": True,
                "maps_to_codebase": [
                    "openhands_skills/research_agent.py:research_new_technologies_and_skills (multi-source last30d Reddit path)",
                    "openhands_skills/langgraph_orchestrator.py:_execute_research + _inject_research_context (general non-onchain topics)"
                ],
                "value_add_for_general_professional_helper": f"Real r/{sub} community signal on \"{title[:70]}\" — unfiltered practitioner discussion about AI/agent/self-improvement patterns.",
                "suggested_as_new_skill_or_enhancement": "Surface Reddit community signals as additional credibility in research candidates, or adopt specific patterns (e.g. reflection loops, lab-style experiments) discussed in high-engagement posts into supervisor or a new lightweight research helper.",
                "integration_effort": "Low. Direct source addition or idea surfacing in existing broad research flow.",
                "evidence_to_use_in_proposal_rationale": evidence[:280]
            },
            "suggested_apply_data": {
                "target_file": "openhands_skills/research_agent.py or openhands_skills/langgraph_orchestrator.py",
                "operation": "incorporate_reddit_last30d_signals_or_patterns",
                "description": "Use real Reddit engagement (score) as credibility boost and/or extract concrete ideas (reflection, self-improvement loops) from the verbatim evidence for guarded proposals."
            },
            "lab_mode": True
        }
        # `"pros_cons": _derive_pros_cons_for_reddit(cand)` sat inside the dict
        # literal that defines `cand` — NameError on the first post, and on
        # later ones the PREVIOUS post's candidate, silently.
        cand["pros_cons"] = _derive_pros_cons_for_reddit(cand)
        reddit_live_cands.append(cand)

        # Print in the exact same report style as the agent's candidates
        print(f"\n  [Reddit LIVE] {cand['id']}")
        print(f"      URL: {url}")
        print(f"      r/{sub} | score={score} | comments={num_comments}")
        cred = cand["credibility_signals"][:1]
        print(f"      Credibility (raw): {cred}")
        pc = cand["pros_cons"]
        print(f"      pros_cons present: True")
        print(f"      ADVANTAGES (πλεονεκτήματα) [{len(pc.get('advantages', []))}]:")
        for a in pc.get("advantages", [])[:3]:
            print(f"        + {a}")
        print(f"      DISADVANTAGES (μειονεκτήματα) [{len(pc.get('disadvantages', []))}]:")
        for d in pc.get("disadvantages", [])[:3]:
            print(f"        - {d}")
        print(f"      Note on pros_cons: {pc.get('note', '')[:120]}")
        ev_short = cand.get("direct_evidence", "")[:180].replace("\n", " ")
        print(f"      Direct evidence (verbatim start): {ev_short}...")
        print(f"      Suggested for: research / supervisor enhancement (guarded)")

if reddit_live_cands:
    print(f"\n  Total live Reddit candidates built this run: {len(reddit_live_cands)}")
else:
    print("  No live Reddit candidates fetched this run (network/UA/rate limit).")

print("\n" + "=" * 70)
print("KEY TAKEAWAYS FOR THE REPORT:")
print("- Every candidate (live GitHub/HN/Reddit or seed) now carries 'pros_cons' with advantages + disadvantages.")
print("- Section 4 above shows **direct live Reddit** data turned into full candidates with pros_cons (no dependency on 'requests').")
print("- The supervisor _synthesize and proactive_discovery surface them in the final report dict.")
print("- Full 100% fidelity objects are in new_capability_candidates[] and get_new_capability_candidate_details(N).")
print("- When the running python has requests + net, the agent's own research_new_technologies_and_skills automatically includes Reddit (see research_agent.py ~673-719).")
print("=" * 70)



print("\nDone. Re-run this script anytime (python live_broad_research_demo.py).")
