"""
OpenHands v2 Entry Point - The MAIN interface for OpenHands

Use this as the primary skill/entry when working with OpenHands for:
- Smart contract development (Solidity / EVM)
- PulseChain (Ethereum hard fork) development
- General coding, debugging, review, market-aware tasks

You can call the high-level functions below directly as tools.
The system handles automatic routing via Smart Triggers + Supervisor.

Example usage from OpenHands:
    from openhands_skills.openhands_v2_entry import run_task
    result = run_task("Create a secure ERC20 vesting contract for PulseChain")
"""

import re
import sys
import os

# The repository root, derived from this file rather than written down.
# It was the literal string 'C:/AI/market-agent', which is where this
# happens to be checked out and not a fact about anyone else's disk. In a
# container the package is mounted at /workspace, and this resolves to it.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Defensive loading for OpenHands environment (skills may be partially available)
def _safe_import(name, default=None):
    try:
        module = __import__(name, fromlist=[''])
        return module
    except Exception as e:
        print(f"[openhands_v2_entry] Warning: could not import {name}: {e}")
        return default

# Lazy / safe imports
log = _safe_import('logger').log if _safe_import('logger') else type('L', (), {'info': print, 'error': print})()
v2 = _safe_import('openhands_multiagent_v2')
solidity_expert = getattr(_safe_import('openhands_skills.solidity_expert'), 'solidity_expert', None)
pulsechain_expert = getattr(_safe_import('openhands_skills.pulsechain_expert'), 'pulsechain_expert', None)
chain_analysis_expert = getattr(_safe_import('openhands_skills.chain_analysis_expert'), 'chain_analysis_expert', None)
programmer_expert = getattr(_safe_import('openhands_skills.programmer_expert'), 'programmer_expert', None)
website_builder = getattr(_safe_import('openhands_skills.website_builder'), 'website_builder', None)
code_researcher = getattr(_safe_import('openhands_skills.code_researcher'), 'code_researcher', None)
designer = getattr(_safe_import('openhands_skills.designer'), 'designer', None)
threejs_expert = getattr(_safe_import('openhands_skills.threejs_expert'), 'threejs_expert', None)
react_specialist = getattr(_safe_import('openhands_skills.react_specialist'), 'react_specialist', None)
mobile_responsive_expert = getattr(_safe_import('openhands_skills.mobile_responsive_expert'), 'mobile_responsive_expert', None)
legal_compliance_expert = getattr(_safe_import('openhands_skills.legal_compliance_expert'), 'legal_compliance_expert', None)
illustration_3d_asset_specialist = getattr(_safe_import('openhands_skills.illustration_3d_asset_specialist'), 'illustration_3d_asset_specialist', None)
maintenance_support_specialist = getattr(_safe_import('openhands_skills.maintenance_support_specialist'), 'maintenance_support_specialist', None)
security_auditor = getattr(_safe_import('openhands_skills.security_auditor'), 'security_auditor', None)
ecommerce_specialist = getattr(_safe_import('openhands_skills.ecommerce_specialist'), 'ecommerce_specialist', None)
typescript_expert = getattr(_safe_import('openhands_skills.typescript_expert'), 'typescript_expert', None)

# These fourteen were referenced by run_task but never imported. Python
# resolves a bare name at *use* time, so `if is_seo and seo_expert:` did not
# skip the branch — it raised NameError, aborting the whole task. Every
# legacy-routed request containing 'test', 'seo', 'backend', 'deploy',
# 'brand', 'content', 'analytics', 'roadmap', 'treasury', 'community'...
# died before producing anything. All fourteen modules exist on disk and
# every method those branches call is defined; only the import was absent.
seo_expert = getattr(_safe_import('openhands_skills.seo_expert'), 'seo_expert', None)
qa_engineer = getattr(_safe_import('openhands_skills.qa_engineer'), 'qa_engineer', None)
backend_specialist = getattr(_safe_import('openhands_skills.backend_specialist'), 'backend_specialist', None)
devops_engineer = getattr(_safe_import('openhands_skills.devops_engineer'), 'devops_engineer', None)
accessibility_expert = getattr(_safe_import('openhands_skills.accessibility_expert'), 'accessibility_expert', None)
content_strategist = getattr(_safe_import('openhands_skills.content_strategist'), 'content_strategist', None)
brand_strategist = getattr(_safe_import('openhands_skills.brand_strategist'), 'brand_strategist', None)
project_manager = getattr(_safe_import('openhands_skills.project_manager'), 'project_manager', None)
analytics_specialist = getattr(_safe_import('openhands_skills.analytics_specialist'), 'analytics_specialist', None)
finance_treasury_expert = getattr(_safe_import('openhands_skills.finance_treasury_expert'), 'finance_treasury_expert', None)
sales_bd_expert = getattr(_safe_import('openhands_skills.sales_bd_expert'), 'sales_bd_expert', None)
product_strategist = getattr(_safe_import('openhands_skills.product_strategist'), 'product_strategist', None)
pr_communications_expert = getattr(_safe_import('openhands_skills.pr_communications_expert'), 'pr_communications_expert', None)
web3_community_manager = getattr(_safe_import('openhands_skills.web3_community_manager'), 'web3_community_manager', None)
python_expert = getattr(_safe_import('openhands_skills.python_expert'), 'python_expert', None)
cpp_expert = getattr(_safe_import('openhands_skills.cpp_expert'), 'cpp_expert', None)
crypto_payments_expert = getattr(_safe_import('openhands_skills.crypto_payments_expert'), 'crypto_payments_expert', None)
hacash_mining_expert = getattr(_safe_import('openhands_skills.hacash_mining_expert'), 'hacash_mining_expert', None)
hacash_fullnode_expert = getattr(_safe_import('openhands_skills.hacash_fullnode_expert'), 'hacash_fullnode_expert', None)
hacash_hvm_expert = getattr(_safe_import('openhands_skills.hacash_hvm_expert'), 'hacash_hvm_expert', None)
hacash_l1_expert = getattr(_safe_import('openhands_skills.hacash_l1_expert'), 'hacash_l1_expert', None)
hacash_l2_expert = getattr(_safe_import('openhands_skills.hacash_l2_expert'), 'hacash_l2_expert', None)
hacash_l3_expert = getattr(_safe_import('openhands_skills.hacash_l3_expert'), 'hacash_l3_expert', None)
tool_hub = getattr(_safe_import('openhands_skills.tool_integration_hub'), 'tool_hub', type('H', (), {'run_market_snapshot': lambda s: 'market data limited in this env'})())

def _setup_openhands_paths():
    """Auto-setup sys.path for OpenHands sandboxes and common dev setups.
    This ensures 'import openhands_skills' and 'import openhands_multiagent_v2' work
    when the workspace is mounted as /workspace or when skills are in ~/.openhands/skills/.
    """
    candidates = [
        '/workspace',
        os.environ.get('WORKSPACE_BASE', ''),
        os.environ.get('OPENHANDS_WORKSPACE', ''),
        os.getcwd(),
        os.path.expanduser('~/.openhands/skills'),
        _REPO_ROOT,
        os.path.expanduser('~') + '/AI/market-agent',
    ]
    for base in candidates:
        if not base:
            continue
        base = os.path.normpath(base)
        if os.path.isdir(base) and base not in sys.path:
            sys.path.insert(0, base)
        # If the base itself contains the packages as subdirs
        for pkg in ['openhands_skills', 'openhands_multiagent_v2']:
            pkg_path = os.path.join(base, pkg)
            if os.path.isdir(pkg_path) and base not in sys.path:
                sys.path.insert(0, base)
    # Also try the skills dir directly if the package is symlinked there
    skills_dir = os.path.expanduser('~/.openhands/skills')
    if os.path.isdir(skills_dir) and skills_dir not in sys.path:
        sys.path.insert(0, skills_dir)

_setup_openhands_paths()

def _system_status(timeout: float = 2.0) -> dict:
    """What is actually working right now.

    The status intent used to answer "✅ Είμαι ενεργός και έτοιμος." — a fixed
    string. The process answering is alive by definition; the question a person
    is asking is whether the BACKEND is up, and that answer was the same
    whether llama-server was serving or had been dead for an hour.

    Every probe here is local and bounded. Nothing calls the model.
    """
    import importlib.util
    import json as _json
    import urllib.request

    st = {"llm": None, "model": None, "slots": None,
          "analyzers": {}, "keys": {}, "guards": None}

    # 1. the model backend
    try:
        from config import config
        base = getattr(config, "OPENAI_BASE_URL", "http://127.0.0.1:8080/v1")
        url = base.rstrip("/").removesuffix("/v1") + "/props"
        with urllib.request.urlopen(url, timeout=timeout) as r:
            d = _json.loads(r.read())
        st["llm"] = True
        st["slots"] = d.get("total_slots")
        st["model"] = str(d.get("model_path", "")).replace("\\", "/").split("/")[-1]
    except Exception as e:
        st["llm"] = False
        st["llm_error"] = f"{type(e).__name__}"

    # 2. the analyzers the coder loop depends on
    for mod in ("ruff", "bandit", "mypy", "pyflakes"):
        try:
            st["analyzers"][mod] = importlib.util.find_spec(mod) is not None
        except Exception:
            st["analyzers"][mod] = False

    # 3. keys configured (presence only — checking validity costs a call)
    try:
        from config import config as _c
        for name in ("FINNHUB_API_KEY", "TAVILY_API_KEY", "TELEGRAM_BOT_TOKEN",
                     "MORALIS_API_KEY", "FINLIGHT_API_KEY"):
            st["keys"][name] = bool(str(getattr(_c, name, "") or "").strip())
    except Exception:
        pass

    # 4. the guards that protect the briefing files
    try:
        from openhands_skills.guards import is_forbidden_path
        st["guards"] = bool(is_forbidden_path("telegram_engine.py"))
    except Exception:
        st["guards"] = False

    return st


def _render_status(st: dict) -> str:
    """The status as a person would want to read it, failures first."""
    lines = []
    if st.get("llm"):
        lines.append(f"✅ Μοντέλο: {st.get('model') or 'φορτωμένο'} "
                     f"({st.get('slots')} slots)")
    else:
        lines.append(f"❌ Μοντέλο: ΔΕΝ αποκρίνεται ({st.get('llm_error', 'άγνωστο')}). "
                     f"Ξεκίνα το με start-ai.bat — χωρίς αυτό δεν γράφω, δεν "
                     f"αναλύω και δεν κάνω briefing.")

    missing = [m for m, ok in st.get("analyzers", {}).items() if not ok]
    if missing:
        lines.append(f"⚠️ Analyzers που λείπουν: {', '.join(missing)} — ο "
                     f"αυτο-διορθούμενος coder θα τρέξει με λιγότερους ελέγχους.")
    else:
        lines.append("✅ Analyzers: ruff, bandit, mypy, pyflakes")

    no_key = [k for k, ok in st.get("keys", {}).items() if not ok]
    if no_key:
        lines.append(f"⚠️ Κλειδιά που λείπουν: {', '.join(no_key)}")
    else:
        lines.append("✅ Κλειδιά: όλα ρυθμισμένα")

    lines.append("✅ Guards ενεργά" if st.get("guards")
                 else "❌ Guards ΔΕΝ φορτώθηκαν — τα briefing αρχεία σου δεν "
                      "προστατεύονται αυτή τη στιγμή.")
    return "\n".join(lines)


def _fast_route(user_task: str) -> dict:
    """Cheap intent routing — the single biggest latency win in the system.

    The legacy body below runs EVERYTHING for every message (supervisor plan,
    strategic vision with live market fetches, market reports, coder, tester,
    reviewer, security, debugger, evolution, synthesis) = 8-12 sequential LLM
    calls even for "hi". On a local 30B that is minutes.

    Returns a dict for handled intents, or None to fall through to the legacy
    full pipeline (so nothing is ever lost). ALWAYS a dict when it handles,
    because openhands_mcp/server.py does result["mcp_tool"] = ... on the value.
    """
    try:
        from openhands_skills.intent_router import classify
    except Exception:
        return None

    route = classify(user_task)
    base = {"task": user_task, "route": route.name, "route_reason": route.reason}

    if route.name == "greeting":
        return {**base, "user_visible": (
            "Γεια σου! Είμαι το MOSKY. Μπορώ να γράψω κώδικα (με αυτόματο έλεγχο "
            "ruff/bandit/mypy), να φτιάξω ιστοσελίδες με ή χωρίς βάση δεδομένων, να "
            "αναλύσω wallets/on-chain, να δώσω ανάλυση αγοράς και να κάνω audit σε "
            "φακέλους κώδικα. Τι θέλεις να κάνουμε;")}

    if route.name == "status":
        st = _system_status()
        healthy = bool(st.get("llm")) and bool(st.get("guards"))
        head = ("✅ Ενεργός και έτοιμος." if healthy
                else "⚠️ Ενεργός, αλλά κάτι δεν δουλεύει:")
        return {**base,
                "user_visible": head + "\n\n" + _render_status(st),
                "healthy": healthy,
                "status": st}

    if route.name == "capability":
        return {**base, "user_visible": (
            "Τι μπορώ να κάνω:\n"
            "• **Κώδικας** — γράφω και αυτο-διορθώνω με πραγματικά εργαλεία "
            "(ruff/bandit/mypy) μέχρι να περάσει\n"
            "• **Ιστοσελίδες** — πλήρη εκτελέσιμα projects, με βάση δεδομένων "
            "(FastAPI + SQLAlchemy + SQLite) ή στατικά, όλα offline\n"
            "• **Ανάλυση φακέλου** — τι είναι σωστό και τι λάθος σε ένα codebase\n"
            "• **On-chain** — wallets, risk/PnL, PulseChain\n"
            "• **Αγορά** — ανάλυση, σενάρια, macro\n"
            "• **Smart contracts** — Solidity/EVM με audit")}

    if route.name == "website":
        try:
            from openhands_skills.web_stack_architect import web_stack_architect
            rep = web_stack_architect.build(user_task, force_db=route.wants_database or None)
            return {**base, "user_visible": rep.to_report(),
                    "project_dir": rep.project_dir, "stack": rep.stack,
                    "status": rep.status, "verification": rep.verification}
        except Exception as e:
            return {**base, "user_visible": f"Website build failed: {e}"}

    if route.name == "document":
        import os as _os
        import re as _re
        path = _extract_pdf(user_task)
        if not path:
            return {**base, "user_visible": (
                "Δώσε μου τη διαδρομή του PDF, π.χ. "
                "C:\\Users\\<you>\\Documents\\book.pdf\n\n"
                "Μετά μπορώ να σου δώσω: τη δομή των κεφαλαίων (άμεσα), "
                "ανάλυση ενός κεφαλαίου, ή απάντηση σε συγκεκριμένη ερώτηση.")}
        if not _os.path.isfile(path):
            return {**base, "user_visible": (
                f"Δεν βρήκα το αρχείο `{path}`. Έλεγξε τη διαδρομή — "
                "δεν άνοιξα κάτι άλλο στη θέση του.")}
        try:
            from openhands_skills.doc_analyst import doc_analyst
            low = user_task.lower()
            # A question is cheap (retrieval only); a full read is not, so the
            # default is the outline, which states what a full read would cost.
            if any(w in low for w in ("κεφαλαι", "chapter")):
                n = _re.search(r"\b(\d{1,2})\b", user_task)
                out = doc_analyst.chapter(path, int(n.group(1)) if n else 1)
            elif "?" in user_task or ";" in user_task:
                out = doc_analyst.ask(path, user_task)
            else:
                out = doc_analyst.outline(path)
            return {**base, "user_visible": out, "pdf": path}
        except Exception as e:
            return {**base, "user_visible": f"Δεν μπόρεσα να διαβάσω το PDF: {e}"}

    if route.name == "cad3d":
        try:
            from openhands_skills.cad_architect import cad_architect
            rep = cad_architect.design(user_task, max_iterations=3)
            return {**base, "user_visible": rep.to_report(),
                    "stl_path": rep.stl_path, "preview": rep.preview_path,
                    "printable": rep.ok}
        except Exception as e:
            return {**base, "user_visible": f"3D design failed: {e}"}

    if route.name == "coding":
        try:
            from openhands_multiagent_v2.self_correcting_coder import self_correcting_coder
            build = self_correcting_coder.build(user_task, max_iterations=3)
            return {**base, "user_visible": build.to_report(),
                    "code": build.code, "clean": build.clean}
        except Exception as e:
            return {**base, "user_visible": f"Coding task failed: {e}"}

    if route.name == "analyze_folder":
        # `target = os.getcwd()` ignored the folder the user named. Ask about
        # D:\\clients\\acme and you were handed a clean bill of health for
        # C:\\AI\\market-agent — an answer about a directory you never mentioned,
        # with nothing in the output to reveal the substitution.
        try:
            from openhands_multiagent_v2.code_intelligence import code_intelligence
            import os as _os

            asked = _extract_folder(user_task)
            if asked and not _os.path.isdir(asked):
                return {**base, "user_visible":
                        f"Δεν βρήκα τον φάκελο `{asked}`. Δεν ανέλυσα τίποτα άλλο στη θέση του."}

            target = asked or _os.getcwd()
            res = code_intelligence.analyze_tree(target)
            note = "" if asked else (
                "\n\n_(Δεν αναφέρθηκε φάκελος στο αίτημα, οπότε αναλύθηκε ο "
                "τρέχων κατάλογος εργασίας.)_")
            return {**base, "user_visible":
                    f"Ανάλυση φακέλου `{target}`:\n\n{res.to_report()}{note}",
                    "analyzed_path": target,
                    "path_came_from": "request" if asked else "cwd_fallback"}
        except Exception as e:
            return {**base, "user_visible": f"Folder analysis failed: {e}"}

    return None  # market / wallet / solidity / legacy -> full pipeline


def _extract_pdf(text: str):
    """The PDF path named in `text`, or None.

    The document route matched only r"[A-Za-z]:[\\\\/]...[dot]pdf" — a Windows
    drive letter and nothing else. A POSIX path, a relative path, or a quoted
    path containing spaces all failed, and the route then replied "give me the
    path of the PDF" to someone who had just given it.

    Accepts, in order of confidence: a quoted path, a Windows path with either
    slash, a POSIX absolute path, and a relative one. A bare path with spaces
    is trimmed one trailing word at a time until it names a real file, so
    "read C:/AI/my book.pdf please" resolves and "C:\\Program Files\\x.pdf"
    survives. An existing file always wins; otherwise the best-formed
    candidate is returned so the caller can say it was not found.
    """
    import os as _os
    import re as _re

    if not text:
        return None

    def _looks_like_a_path_word(w):
        """A word that could begin a path, rather than the sentence around it."""
        return ("/" in w or "\\" in w or ":" in w or w.startswith(".")
                or w.lower().endswith(".pdf"))

    def _trim_left(cand):
        """Drop leading sentence words: "open docs/x.pdf" -> "docs/x.pdf".

        The trailing trim alone was not enough. Anchoring the pattern was not
        either: "open docs/manual.pdf" starts at the beginning of the string, so
        a start-anchored match still swallows "open".
        """
        parts = cand.split(" ")
        while len(parts) > 1 and not _looks_like_a_path_word(parts[0]):
            parts.pop(0)
        return " ".join(parts)

    def _settle(cand):
        cand = _trim_left(cand.strip().strip(",;:").strip())
        while cand:
            if _os.path.isfile(cand):
                return _os.path.abspath(cand)
            if " " not in cand:
                return None
            cand = cand.rsplit(" ", 1)[0].rstrip(",;:")
        return None

    quoted = _re.findall(r'''["'`]([^"'`\n]*?\.pdf)["'`]''', text, _re.I)
    for cand in quoted:
        hit = _settle(cand)
        if hit:
            return hit

    pats = (
        r'''[A-Za-z]:[\\/][^"'<>|?*\n]*?\.pdf''',      # C:\\... or C:/...
        r'''\\\\[^"'<>|?*\n]*?\.pdf''',           # \\\\server\\share\\...
        r'''(?:^|(?<=\s))/[^"'<>|?*\n]*?\.pdf''',              # /home/... , /mnt/...
        r'''[\w.~][^"'<>|?*\n]*?\.pdf''',         # docs/book.pdf , ./book.pdf
    )
    unresolved = None
    for pat in pats:
        for m in _re.finditer(pat, text, _re.I):
            raw = m.group(0)
            hit = _settle(raw)
            if hit:
                return hit
            if unresolved is None:
                unresolved = _trim_left(raw.strip().rstrip(",;:"))
    return unresolved


def _extract_folder(text: str):
    """The directory named in `text`, or None.

    Accepts the Windows form the user actually types, quoted or bare, and
    POSIX paths. A bare path is matched greedily and then trimmed one trailing
    word at a time until it names a real directory, so "C:/AI/market-agent
    please" resolves while "C:\\Program Files\\My App" survives intact.
    Returns None rather than guessing, so the caller can say it fell back to
    the working directory instead of silently answering about the wrong one.
    """
    import os as _os
    import re as _re

    if not text:
        return None

    def _settle(cand):
        cand = cand.strip().strip(",;:.").strip()
        while cand:
            if _os.path.isdir(cand):
                return _os.path.abspath(cand)
            if " " not in cand:
                return None
            cand = cand.rsplit(" ", 1)[0].rstrip(",;:.")
        return None

    for cand in _re.findall(r'''["'`]([^"'`\n]{3,})["'`]''', text):
        hit = _settle(cand)
        if hit:
            return hit

    pats = (r'''[A-Za-z]:[\\/][^"'<>|?*\n]*''',
            r'''(?:\.?/|/)[^"'<>|?*\n]{2,}''')
    unresolved = None
    for pat in pats:
        for m in _re.finditer(pat, text):
            raw = m.group(0)
            hit = _settle(raw)
            if hit:
                return hit
            if unresolved is None:
                first = raw.strip().split(" ")[0].rstrip(",;:.")
                if not _os.path.splitext(first)[1]:
                    unresolved = first

    # A path that was clearly named but does not exist is reported as-is, so
    # the caller can say "I did not find it" rather than analysing cwd.
    return unresolved


def _mentions(text, *words):
    """True when `text` contains one of `words` as a WHOLE WORD.

    The routing flags used `any(k in task_lower for k in [...])`, a plain
    substring test, and the short keywords in those lists appear inside
    ordinary English. Measured:

        is_pr      "pr"    fires on imPRove, comPRess, aPPRoach, PRint
                   "press" fires on comPRESSed, PRESSure
                   "media" fires on imMEDIAte, reMEDIAtion
        is_backend "api"   fires on rAPId, cAPItal   <- both common here
        is_qa      "test"  fires on laTEST, greaTEST, proTEST

    So "fix the print statement" pulled in a PR communications consultation
    and "capital allocation" pulled in a backend specialist. Same defect class
    as looks_like_solidity matching "erc" inside e-commerce.
    """
    import re as _re
    if not text:
        return False
    pat = "|".join(_re.escape(w) for w in words)
    return _re.search(rf"\b(?:{pat})\b", text, _re.I) is not None


def run_task(user_task: str = "", **kwargs) -> dict:
    """
    High-level MAIN entry for OpenHands (v2 + skills). Professional flexible interface.
    Automatically handles everything:
    - Detects task type (Solidity, PulseChain, DeFi, general code, market, wallet forensics)
    - Routes to correct agents + experts
    - Returns structured output with code, audit, tests, deployment, reflection, rich chain_analysis when relevant

    Supports:
    - Natural language str: run_task("full wallet profile for 0x... on pulsechain")
    - Structured: run_task("full_wallet_profile", address="0x...", chain="pulsechain") or via **kwargs
    - Direct address in task or kwargs triggers enhanced chain analysis with real USD risk/PnL (Moralis + public free).
    """
    if not user_task and kwargs:
        # Structured call support (professional upgrade, matches some docs/examples)
        addr = kwargs.get("address") or kwargs.get("wallet") or ""
        ch = kwargs.get("chain", "pulsechain")
        action = kwargs.get("action", kwargs.get("task", "full profile"))
        user_task = f"{action} for {addr} on {ch}" if addr else str(kwargs)
    if not user_task:
        user_task = "general task"
    log.info(f"OpenHands v2 MAIN Entry: {user_task}")

    # FAST PATH: only run what this message actually needs.
    # Kill switch: set MOSKY_ROUTER=off to force the full legacy pipeline.
    if os.getenv("MOSKY_ROUTER", "on").lower() != "off":
        try:
            fast = _fast_route(user_task)
            if isinstance(fast, dict):
                log.info(f"[router] handled as '{fast.get('route')}' — skipped full pipeline")
                return fast
        except Exception as e:
            log.warning(f"[router] failed, falling back to full pipeline: {e}")

    result = {
        "task": user_task,
        "chain": "ethereum",
        "trigger": None,
        "plan": None,
        "code": None,
        "audit": None,
        "tests": None,
        "deploy": None,
        "market_context": None,
        "reflection": "Task processed with automatic multi-agent + expert routing."
    }
    
    # Determine chain
    if any(p in user_task.lower() for p in ["pulse", "pls", "pulsechain"]):
        result["chain"] = "pulsechain"
    
    # Automatic trigger + supervisor (guarded for sandbox where openhands_multiagent_v2 may not be importable due to missing logger etc.)
    if v2 and hasattr(v2, 'smart_trigger'):
        trigger_result = v2.smart_trigger.run(user_task)
        result["trigger"] = trigger_result
    else:
        result["trigger"] = "v2 multi-agent not available in this env (sandbox limitation) - using direct expert routing"
    
    chain = result["chain"]
    
    # Chain Analysis integration (high priority for tracing addresses in audits/debug)
    if any(kw in user_task.lower() for kw in ["chain analysis", "analyze address", "wallet trace", "tx history", "explorer", "from where", "where did it send", "trace flows"]):
        try:
            addresses = re.findall(r'0x[a-fA-F0-9]{40}', user_task)
            if addresses:
                addr = addresses[0]
                ch = "pulsechain" if "pulse" in user_task.lower() else "ethereum"
                result["chain_analysis"] = chain_analysis_expert.analyze_address(addr, chain=ch, context=user_task)
                result["reflection"] += " | Integrated Chain Analysis Expert for address tracing (incoming/outgoing/what it did + explorer links + risks)."
            else:
                result["chain_analysis"] = "No 0x address found in task. Provide address for full trace report."
        except Exception as e:
            result["chain_analysis"] = f"Chain analysis handled with fallback: {e}"
            log.error(f"Chain analysis error: {e}")
    
    # If Solidity/PulseChain/DeFi/smart contract -> full expert pipeline (with better error handling)
    solidity_keywords = ["solidity", "evm", "erc", "pulsechain", "smart contract", "defi", "hvm", "staking", "vesting", "governance"]
    try:
        if any(kw in user_task.lower() for kw in solidity_keywords):
            # Use dedicated PulseChain expert when on pulsechain for extra intelligence
            if chain == "pulsechain":
                full = pulsechain_expert.generate_pulsechain_contract(user_task)
                result["code"] = full
                result["audit"] = pulsechain_expert.audit_for_pulsechain(full)
                result["deploy"] = pulsechain_expert.get_pulsechain_deployment_script("YourContract")
                if any(tk in user_task.lower() for tk in ["tokenomics", "defi", "market"]):
                    result["tokenomics"] = pulsechain_expert.suggest_tokenomics_with_market("YourToken")
            else:
                full = solidity_expert.generate_full_project(user_task, target_chain=chain)
                result["code"] = full.get("contract")
                result["audit"] = full.get("audit")
                result["tests"] = full.get("tests")
                result["deploy"] = full.get("deploy")
            
            # Advanced DeFi pattern if mentioned
            if any(p in user_task.lower() for p in ["flash", "lending", "liquidity pool", "yield"]):
                pattern = next((p for p in ["flash", "lending", "liquidity", "yield"] if p in user_task.lower()), "defi")
                result["advanced_defi"] = solidity_expert.write_advanced_defi_pattern(pattern, user_task, target_chain=chain)
            
            result["reflection"] = f"Automatic full pipeline executed for {chain}. Used dedicated experts + v2 agents with smart delegation. Advanced DeFi patterns and market data for tokenomics included where relevant."
    except Exception as e:
        result["error"] = f"Error during expert pipeline: {str(e)}. Falling back to basic orchestration."
        log.error(f"run_task expert pipeline error: {e}")
    
    # Market context if relevant (DeFi tokenomics etc.)
    if any(kw in user_task.lower() for kw in ["market", "price", "tokenomics", "defi", "liquidity"]) and not result.get("market_context"):
        try:
            result["market_context"] = tool_hub.run_market_snapshot()
        except Exception as e:
            result["market_context"] = f"Market data unavailable: {e}"
            log.warning(f"Market data fetch failed: {e}")
    
    # Dedicated smart buy/sell + real history for wallets (the user's main request)
    if any(kw in user_task.lower() for kw in ["wallet", "bought", "sold", "buy sell", "transaction history", "which coin", "coins", "portfolio", "holdings", "native", "pls flow"]):
        try:
            addresses = re.findall(r'0x[a-fA-F0-9]{40}', user_task)
            ch = "pulsechain" if "pulse" in user_task.lower() else "ethereum"
            if addresses:
                addr = addresses[0]
                ca = chain_analysis_expert.analyze_address(addr, chain=ch, context=user_task + " This is a wallet. Focus on full activity: transfers, native flows, swaps, portfolio, categories, beyond just tx/transfer list.")
                result["chain_analysis"] = ca
                result["real_buy_sell_guidance"] = chain_analysis_expert.get_real_buy_sell_history_guidance(addr, ch)
                # Expose rich structured data (Moralis when key + free fallbacks)
                if isinstance(ca, dict):
                    if ca.get("real_buy_sell_history"):
                        result["token_buy_sell_history"] = ca["real_buy_sell_history"].get("summary", [])
                    elif "token_buy_sell_history_and_coins" in ca:
                        result["token_buy_sell_history"] = ca["token_buy_sell_history_and_coins"]
                    if ca.get("real_activity"):
                        result["real_activity_fetched"] = ca["real_activity"]
                    # Richer fields
                    for extra in ["native_pls_flows", "current_portfolio", "approx_usd_value", "activity_categories", "approvals", "full_wallet_profile", "flow_visualization", "pnl_estimate", "risk_score"]:
                        if extra in ca:
                            result[extra] = ca[extra]
                    if ca.get("flow_visualization"):
                        result["flow_visualization"] = ca["flow_visualization"]
                result["reflection"] += " | Full wallet analysis (transfers + native PLS + swaps + current portfolio + categories + approvals + real flow viz). Real data via Moralis (if key) + free public APIs."
        except Exception as e:
            result["chain_analysis"] = f"Buy/sell guidance error (handled): {e}"
    
    # General case - use full orchestrator (with error handling)
    if result.get("code") is None and not result.get("chain_analysis"):
        try:
            orchestrator_result = v2.orchestrator.run(user_task)
            result["plan"] = orchestrator_result
            result["reflection"] = "Routed through full v2 multi-agent orchestrator with memory, evolution and reflection."
        except Exception as e:
            result["plan"] = f"Orchestrator fallback: {str(e)}"
            log.error(f"Orchestrator error: {e}")
    
    # Full combined scenario support: "audit PulseChain contract + chain trace deployer + bug fix" (larger end-to-end)
    if any(s in user_task.lower() for s in ["audit", "review"]) and any(c in user_task.lower() for c in ["chain", "trace", "deployer", "bug", "fix", "error"]):
        try:
            addresses = re.findall(r'0x[a-fA-F0-9]{40}', user_task)
            ch = "pulsechain" if "pulse" in user_task.lower() else "ethereum"
            if addresses:
                # Full pipeline: audit + creator trace + viz + memory (previous sightings) + bug fix
                contract_audit = solidity_expert.audit_solidity(user_task, target_chain=ch) if "audit" in user_task.lower() else "No audit requested"
                creator_trace = chain_analysis_expert.analyze_contract_creator(addresses[0], chain=ch, context=user_task)
                flow_viz = chain_analysis_expert.visualize_flows(addresses[0], chain=ch, context=user_task)
                if isinstance(flow_viz, dict):
                    flow_viz = flow_viz.get("ascii", "") + "\n" + flow_viz.get("mermaid", "")
                bug_fix = (
                    "Suggested fix steps:\n"
                    "1. Add ReentrancyGuard + checks-effects-interactions pattern.\n"
                    "2. Use OpenZeppelin for critical components.\n"
                    "3. Add events for all state changes.\n"
                    "4. Re-audit with chain_analysis on related addresses.\n"
                    "5. Test thoroughly on PulseChain fork (low fees allow many test txs).\n"
                    "6. Consider formal verification for high-value contracts."
                )
                result["full_scenario"] = {
                    "contract_audit": contract_audit,
                    "deployer_chain_trace": creator_trace,
                    "flow_visualization": flow_viz,
                    "bug_fix_recommendation": bug_fix,
                    "memory_note": "Address sightings stored in persistent_memory for 'we've seen this before' checks in future tasks.",
                    "note": "Larger end-to-end scenario executed: audit + deployer trace + viz + bug fix + memory integration. Feed real code/error for production use."
                }
                result["reflection"] += " | Larger end-to-end scenario (audit + chain trace deployer + viz + bug fix + memory) executed automatically."
        except Exception as e:
            result["full_scenario"] = f"Scenario fallback: {e}"
            log.error(f"Full scenario error: {e}")
    
    # === NEW: Programmer Expert + Website Builder + Code Researcher routing ===
    task_lower = user_task.lower()
    is_programmer = any(k in task_lower for k in ["programmer", "write code", "implement feature", "refactor", "generate code", "build module", "coder", "add python", "create script"])
    # "ui" fired on bUIld, gUIde, reqUIrements, qUIck — "build a parser"
    # routed here. Whole words only.
    is_website = _mentions(task_lower, "website", "explorer", "dashboard", "ui", "build website", "pulsechain explorer", "streamlit", "react site", "html explorer", "proposals dashboard", "wallet ui", "make a site", "modern website", "creative site")
    is_code_research = any(k in task_lower for k in ["code researcher", "code-researcher", "github for code", "modern web tech", "research three", "research framer", "fresh frontend libs", "what animation library", "github ideas for website"])
    is_designer = any(k in task_lower for k in ["designer", "design", "ui ux", "visual design", "design system", "color palette", "typography", "aesthetics"])
    is_threejs = any(k in task_lower for k in ["three.js", "threejs", "3d scene", "webgl", "3d web", "three fiber"])
    is_react = any(k in task_lower for k in ["advanced react", "react architecture", "react specialist", "react performance", "react patterns"])
    is_mobile = any(k in task_lower for k in ["mobile", "responsive", "phone", "tablet", "mobile first", "touch", "mobile ux"])
    is_seo = _mentions(task_lower, "seo", "search optimization", "meta tags", "structured data", "google ranking")
    is_qa = _mentions(task_lower, "qa", "testing", "test", "tests", "bug", "bugs",
                      "quality assurance", "cross browser")
    is_backend = _mentions(task_lower, "backend", "api", "apis", "database", "databases",
                           "auth", "server", "servers", "data")
    is_devops = any(k in task_lower for k in ["devops", "deploy", "deployment", "ci/cd", "hosting", "vercel", "monitoring"])
    is_a11y = any(k in task_lower for k in ["accessibility", "a11y", "wcag", "aria", "screen reader", "inclusive"])
    is_content = any(k in task_lower for k in ["content", "copy", "copywriting", "ux writing", "messaging", "seo content"])
    is_brand = any(k in task_lower for k in ["brand", "branding", "brand strategy", "brand identity", "positioning", "tone of voice"])
    is_project = any(k in task_lower for k in ["project manager", "project management", "planning", "timeline", "coordination", "client handoff", "milestones"])
    is_analytics = any(k in task_lower for k in ["analytics", "tracking", "a/b testing", "conversion", "roi", "measurement", "growth", "kpi"])
    is_legal = any(k in task_lower for k in ["legal", "compliance", "gdpr", "privacy", "cookie consent", "terms of service"])
    is_illustration = any(k in task_lower for k in ["illustration", "3d asset", "3d model", "gltf", "asset optimization", "custom 3d"])
    is_maintenance = any(k in task_lower for k in ["maintenance", "support", "post-launch", "monitoring", "updates", "client training"])
    is_security = any(k in task_lower for k in ["security", "owasp", "vulnerability", "secure coding", "penetration", "hardening"])
    is_ecommerce = any(k in task_lower for k in ["ecommerce", "e-commerce", "payment", "cart", "checkout", "pci", "shop"])
    is_typescript = any(k in task_lower for k in ["typescript", "ts expert", "advanced typescript", "ts patterns"])
    is_python = any(k in task_lower for k in ["python expert", "python backend", "fastapi", "python specialist"])
    is_cpp = any(k in task_lower for k in ["c++", "cpp", "c++ expert", "high performance c++", "wasm"])
    is_crypto = any(k in task_lower for k in ["crypto", "bitcoin", "ethereum", "usdc", "web3 payment", "crypto payment", "on-chain"])
    is_hacash_mining = any(k in task_lower for k in ["hacash mining", "x16rs", "hacash pow", "diamond mining", "hacash gpu mining"])
    is_hacash_fullnode = any(k in task_lower for k in ["hacash fullnode", "hacash rust node", "hacash rpc", "hacash full node"])
    is_hacash_hvm = any(k in task_lower for k in ["hacash hvm", "hacash virtual machine", "hvm contract", "hacash smart contract"])
    is_hacash_l1 = any(k in task_lower for k in ["hacash l1", "hacash layer 1", "hacash money system", "hacash btc peg"])
    is_hacash_l2 = any(k in task_lower for k in ["hacash l2", "hacash layer 2", "hacash channel chain", "hacash csp"])
    is_hacash_l3 = any(k in task_lower for k in ["hacash l3", "hacash layer 3", "hacash rollup", "hacash dapp scaling"])
    is_legal = any(k in task_lower for k in ["legal", "compliance", "gdpr", "privacy", "cookie consent", "terms of service", "lawyer"])
    is_brand = any(k in task_lower for k in ["brand", "branding", "brand strategy", "brand identity", "positioning", "tone of voice"])
    is_content = any(k in task_lower for k in ["content", "copy", "copywriting", "ux writing", "messaging", "seo content"])
    is_finance = any(k in task_lower for k in ["finance", "treasury", "cfo", "tokenomics", "financial model", "treasury management", "ips", "yield", "liquidity"])
    is_sales = any(k in task_lower for k in ["sales", "bd", "business development", "partnerships", "client acquisition", "pitch", "proposal", "close deal"])
    is_product = any(k in task_lower for k in ["product strategist", "product strategy", "product vision", "roadmap", "product manager", "tokenomics product", "web3 product"])
    is_pr = _mentions(task_lower, "pr", "public relations", "communications",
                      "media", "press", "earned media", "thought leadership",
                      "press release", "journalist", "journalists")
    is_community = any(k in task_lower for k in ["community", "web3 community", "governance", "discord", "token launch community", "on-chain incentives", "dao"])

    if is_programmer and programmer_expert:
        try:
            lang = "solidity" if any(x in task_lower for x in ["solidity", "contract", "evm"]) else "python"
            impl = programmer_expert.implement_feature(user_task, language=lang)
            result["programmer_expert"] = impl
            result["code"] = impl.get("main_implementation")
            result["plan"] = impl.get("plan")
            result["reflection"] += " | Routed to ProgrammerExpert (full standards: task_tracker array, guarded proposals, memory retrieval, additive changes)."
        except Exception as e:
            result["programmer_expert"] = f"Programmer expert error (fallback): {e}"

    if is_website and website_builder:
        try:
            if "pulsechain" in task_lower or "explorer" in task_lower:
                site = website_builder.build_pulsechain_explorer(user_task)
            else:
                site = website_builder.build_modern_website(user_task)  # general modern with 3D/animations/fonts/particles
            result["website_builder"] = site
            result["code"] = site.get("standalone_html_modern") or site.get("react_vite_modern") or site.get("streamlit_version") or "See full website_builder output"
            result["reflection"] += " | Routed to WebsiteBuilder (general modern websites supported — 3D, framer-motion, glass, variable fonts, particles, scroll animations etc.)."
        except Exception as e:
            result["website_builder"] = f"Website builder error (fallback): {e}"

    if is_code_research and code_researcher:
        try:
            research = code_researcher.research_modern_web_techniques(user_task) if any(x in task_lower for x in ["web","visual","3d","animation","font"]) else code_researcher.get_github_code_ideas(user_task)
            result["code_researcher"] = research
            result["reflection"] += " | Routed to CodeResearcher (GitHub + fresh 2025-2026 libs/patterns for code and rich modern websites)."
        except Exception as e:
            result["code_researcher"] = f"Code researcher error: {e}"

    if is_designer and designer:
        try:
            d = designer.design_website(user_task)
            result["designer"] = d
            result["reflection"] += " | Routed to Designer (UI/UX, mobile-first aesthetics, design system)."
        except Exception as e:
            result["designer"] = f"Designer error: {e}"

    if is_threejs and threejs_expert:
        try:
            t = threejs_expert.create_threejs_scene(user_task)
            result["threejs_expert"] = t
            result["reflection"] += " | Routed to ThreeJSExpert (deep 3D/WebGL with mobile performance focus)."
        except Exception as e:
            result["threejs_expert"] = f"ThreeJS error: {e}"

    if is_react and react_specialist:
        try:
            r = react_specialist.build_react_architecture(user_task)
            result["react_specialist"] = r
            result["reflection"] += " | Routed to ReactSpecialist (advanced architecture & performance)."
        except Exception as e:
            result["react_specialist"] = f"React specialist error: {e}"

    if is_mobile and mobile_responsive_expert:
        try:
            m = mobile_responsive_expert.make_responsive(user_task)
            result["mobile_responsive_expert"] = m
            result["reflection"] += " | Routed to MobileResponsiveExpert (phone/tablet rendering, touch, mobile-first)."
        except Exception as e:
            result["mobile_responsive_expert"] = f"Mobile expert error: {e}"

    if is_seo and seo_expert:
        try:
            s = seo_expert.optimize_for_search(user_task)
            result["seo_expert"] = s
            result["reflection"] += " | Routed to SEOExpert (technical SEO, meta, search performance)."
        except Exception as e:
            result["seo_expert"] = f"SEO expert error: {e}"

    if is_qa and qa_engineer:
        try:
            q = qa_engineer.run_quality_assurance(user_task)
            result["qa_engineer"] = q
            result["reflection"] += " | Routed to QAEngineer (testing, cross-browser/device QA)."
        except Exception as e:
            result["qa_engineer"] = f"QA error: {e}"

    if is_backend and backend_specialist:
        try:
            b = backend_specialist.build_backend(user_task)
            result["backend_specialist"] = b
            result["reflection"] += " | Routed to BackendSpecialist (APIs, data, auth)."
        except Exception as e:
            result["backend_specialist"] = f"Backend error: {e}"

    if is_devops and devops_engineer:
        try:
            d = devops_engineer.handle_deployment(user_task)
            result["devops_engineer"] = d
            result["reflection"] += " | Routed to DevOpsEngineer (CI/CD, deployment, monitoring)."
        except Exception as e:
            result["devops_engineer"] = f"DevOps error: {e}"

    if is_a11y and accessibility_expert:
        try:
            a = accessibility_expert.ensure_accessibility(user_task)
            result["accessibility_expert"] = a
            result["reflection"] += " | Routed to AccessibilityExpert (WCAG, ARIA, inclusive design)."
        except Exception as e:
            result["accessibility_expert"] = f"A11y error: {e}"

    if is_content and content_strategist:
        try:
            c = content_strategist.create_content_strategy(user_task)
            result["content_strategist"] = c
            result["reflection"] += " | Routed to ContentStrategist (UX writing, messaging, SEO content)."
        except Exception as e:
            result["content_strategist"] = f"Content error: {e}"

    if is_brand and brand_strategist:
        try:
            b = brand_strategist.create_brand_strategy(user_task)
            result["brand_strategist"] = b
            result["reflection"] += " | Routed to BrandStrategist (full brand identity, guidelines, positioning for professional work)."
        except Exception as e:
            result["brand_strategist"] = f"Brand error: {e}"

    if is_project and project_manager:
        try:
            p = project_manager.plan_and_coordinate(user_task)
            result["project_manager"] = p
            result["reflection"] += " | Routed to ProjectManager (full orchestration, planning, reviews, client handoff for serious projects)."
        except Exception as e:
            result["project_manager"] = f"Project manager error: {e}"

    if is_analytics and analytics_specialist:
        try:
            a = analytics_specialist.setup_analytics_and_optimization(user_task)
            result["analytics_specialist"] = a
            result["reflection"] += " | Routed to AnalyticsSpecialist (tracking, A/B, conversion, ROI for business results)."
        except Exception as e:
            result["analytics_specialist"] = f"Analytics error: {e}"

    if is_legal and legal_compliance_expert:
        try:
            l = legal_compliance_expert.audit_and_implement_compliance(user_task)
            result["legal_compliance_expert"] = l
            result["reflection"] += " | Routed to LegalComplianceExpert (GDPR, privacy, terms, cookie consent, IP for production sites)."
        except Exception as e:
            result["legal_compliance_expert"] = f"Legal error: {e}"

    if is_brand and brand_strategist:
        try:
            b = brand_strategist.god_tier_create_brand_strategy(user_task) if hasattr(brand_strategist, 'god_tier_create_brand_strategy') else brand_strategist.create_brand_strategy(user_task)
            result["brand_strategist"] = b
            result["reflection"] += " | Routed to BrandStrategist (god-tier for serious + crypto/Hacash)."
        except Exception as e:
            result["brand_strategist"] = f"Brand error: {e}"

    if is_content and content_strategist:
        try:
            c = content_strategist.god_tier_create_content_strategy(user_task) if hasattr(content_strategist, 'god_tier_create_content_strategy') else content_strategist.create_content_strategy(user_task)
            result["content_strategist"] = c
            result["reflection"] += " | Routed to ContentStrategist (god-tier marketing content systems)."
        except Exception as e:
            result["content_strategist"] = f"Content error: {e}"

    if is_finance and finance_treasury_expert:
        try:
            f = finance_treasury_expert.god_tier_treasury_strategy_and_ips(user_task, include_hacash="hacash" in task_lower)
            result["finance_treasury_expert"] = f
            result["reflection"] += " | Routed to FinanceTreasuryExpert (ULTRA GOD TIER - IPS, tokenomics, extreme caution crypto)."
        except Exception as e:
            result["finance_treasury_expert"] = f"Finance error: {e}"

    if is_sales and sales_bd_expert:
        try:
            s = sales_bd_expert.god_tier_bd_strategy_and_pipeline(user_task, include_crypto="crypto" in task_lower or "hacash" in task_lower)
            result["sales_bd_expert"] = s
            result["reflection"] += " | Routed to SalesBdExpert (ULTRA GOD TIER - institutional web3 BD, proposals)."
        except Exception as e:
            result["sales_bd_expert"] = f"Sales error: {e}"

    if is_product and product_strategist:
        try:
            p = product_strategist.god_tier_product_vision_and_roadmap(user_task, include_hacash="hacash" in task_lower)
            result["product_strategist"] = p
            result["reflection"] += " | Routed to ProductStrategist (ULTRA GOD TIER - web3 product vision, tokenomics-in-product)."
        except Exception as e:
            result["product_strategist"] = f"Product strategist error: {e}"

    if is_pr and pr_communications_expert:
        try:
            pr = pr_communications_expert.god_tier_pr_strategy_and_narrative(user_task, include_crypto="crypto" in task_lower, include_hacash="hacash" in task_lower)
            result["pr_communications_expert"] = pr
            result["reflection"] += " | Routed to PrCommunicationsExpert (ULTRA GOD TIER - earned media, substance PR for crypto)."
        except Exception as e:
            result["pr_communications_expert"] = f"PR error: {e}"

    if is_community and web3_community_manager:
        try:
            com = web3_community_manager.god_tier_community_strategy_and_governance(user_task, include_hacash="hacash" in task_lower)
            result["web3_community_manager"] = com
            result["reflection"] += " | Routed to Web3CommunityManager (ULTRA GOD TIER - governance, incentives, on-chain community)."
        except Exception as e:
            result["web3_community_manager"] = f"Community error: {e}"

    if is_illustration and illustration_3d_asset_specialist:
        try:
            i = illustration_3d_asset_specialist.create_asset_pipeline(user_task)
            result["illustration_3d_asset_specialist"] = i
            result["reflection"] += " | Routed to Illustration3DAssetSpecialist (custom 3D models, illustrations, asset optimization)."
        except Exception as e:
            result["illustration_3d_asset_specialist"] = f"Illustration/3D asset error: {e}"

    if is_maintenance and maintenance_support_specialist:
        try:
            m = maintenance_support_specialist.create_maintenance_and_support_plan(user_task)
            result["maintenance_support_specialist"] = m
            result["reflection"] += " | Routed to MaintenanceSupportSpecialist (post-launch monitoring, updates, client training, ongoing support)."
        except Exception as e:
            result["maintenance_support_specialist"] = f"Maintenance error: {e}"

    if is_security and security_auditor:
        try:
            s = security_auditor.audit_security(user_task)
            result["security_auditor"] = s
            result["reflection"] += " | Routed to SecurityAuditor (OWASP, secure coding, vulnerability assessment)."
        except Exception as e:
            result["security_auditor"] = f"Security error: {e}"

    if is_ecommerce and ecommerce_specialist:
        try:
            e = ecommerce_specialist.build_ecommerce_platform(user_task)
            result["ecommerce_specialist"] = e
            result["reflection"] += " | Routed to EcommerceSpecialist (payments, carts, checkout, PCI compliance)."
        except Exception as e:
            result["ecommerce_specialist"] = f"Ecommerce error: {e}"

    if is_typescript and typescript_expert:
        try:
            t = typescript_expert.build_typescript_architecture(user_task)
            result["typescript_expert"] = t
            result["reflection"] += " | Routed to TypescriptExpert (advanced TS, type safety, modern frontend)."
        except Exception as e:
            result["typescript_expert"] = f"Typescript error: {e}"

    if is_python and python_expert:
        try:
            p = python_expert.build_python_backend(user_task)
            result["python_expert"] = p
            result["reflection"] += " | Routed to PythonExpert (professional Python backend, FastAPI, AI/data)."
        except Exception as e:
            result["python_expert"] = f"Python error: {e}"

    if is_cpp and cpp_expert:
        try:
            c = cpp_expert.build_high_performance_components(user_task)
            result["cpp_expert"] = c
            result["reflection"] += " | Routed to CppExpert (high-performance C++, WASM, 3D engines)."
        except Exception as e:
            result["cpp_expert"] = f"C++ error: {e}"

    if is_crypto and crypto_payments_expert:
        try:
            c = crypto_payments_expert.build_crypto_payment_flow(user_task)
            result["crypto_payments_expert"] = c
            result["reflection"] += " | Routed to CryptoPaymentsExpert (specific gateways + React+3D snippets + cpp-expert for heavy computation)."
        except Exception as e:
            result["crypto_payments_expert"] = f"Crypto error: {e}"

    if is_hacash_mining and hacash_mining_expert:
        try:
            m = hacash_mining_expert.implement_mining_features(user_task)
            result["hacash_mining_expert"] = m
            result["reflection"] += " | Routed to HacashMiningExpert (X16RS mining, pools, GPU/CPU, diamonds)."
        except Exception as e:
            result["hacash_mining_expert"] = f"Hacash mining error: {e}"

    if is_hacash_fullnode and hacash_fullnode_expert:
        try:
            f = hacash_fullnode_expert.implement_fullnode_features(user_task)
            result["hacash_fullnode_expert"] = f
            result["reflection"] += " | Routed to HacashFullnodeExpert (Rust full node, RPC, layers)."
        except Exception as e:
            result["hacash_fullnode_expert"] = f"Hacash fullnode error: {e}"

    if is_hacash_hvm and hacash_hvm_expert:
        try:
            h = hacash_hvm_expert.implement_hvm_contracts(user_task)
            result["hacash_hvm_expert"] = h
            result["reflection"] += " | Routed to HacashHVMExpert (HVM smart contracts, VM, multi-lang)."
        except Exception as e:
            result["hacash_hvm_expert"] = f"Hacash HVM error: {e}"

    if is_hacash_l1 and hacash_l1_expert:
        try:
            l = hacash_l1_expert.implement_l1_features(user_task)
            result["hacash_l1_expert"] = l
            result["reflection"] += " | Routed to HacashL1Expert (L1 money, peg, settlement)."
        except Exception as e:
            result["hacash_l1_expert"] = f"Hacash L1 error: {e}"

    if is_hacash_l2 and hacash_l2_expert:
        try:
            l = hacash_l2_expert.implement_l2_features(user_task)
            result["hacash_l2_expert"] = l
            result["reflection"] += " | Routed to HacashL2Expert (L2 channel chains, CSP)."
        except Exception as e:
            result["hacash_l2_expert"] = f"Hacash L2 error: {e}"

    if is_hacash_l3 and hacash_l3_expert:
        try:
            l = hacash_l3_expert.implement_l3_features(user_task)
            result["hacash_l3_expert"] = l
            result["reflection"] += " | Routed to HacashL3Expert (L3 Rollups, apps, scaling)."
        except Exception as e:
            result["hacash_l3_expert"] = f"Hacash L3 error: {e}"

    return result

def run_solidity_task(task: str, chain: str = "pulsechain") -> dict:
    """Convenience for direct Solidity/PulseChain work (recommended for smart contracts)."""
    return {
        "task": task,
        "chain": chain,
        "full_project": solidity_expert.generate_full_project(task, target_chain=chain),
        "note": "Generated with best practices for EVM/PulseChain. Use with Foundry/Hardhat."
    }

def get_solidity_expert():
    """Direct access to the main Solidity/PulseChain expert."""
    return solidity_expert

def get_programmer_expert():
    """Direct access to the dedicated programmer specialist."""
    return programmer_expert

def get_website_builder():
    """Direct access to the website / explorer / dashboard specialist (now fully general modern websites)."""
    return website_builder

def get_code_researcher():
    """Direct access to the code + modern web tech researcher (feeds programmer + website)."""
    return code_researcher

def run_website_task(task: str = "Beautiful modern portfolio site", style: str = "futuristic") -> dict:
    """High-level for any modern website with rich visuals."""
    if website_builder:
        return website_builder.build_modern_website(task, style=style)
    return {"error": "website_builder not available"}

def run_code_research_task(query: str) -> dict:
    if code_researcher:
        return code_researcher.research_modern_web_techniques(query)
    return {"error": "code_researcher not available"}

def get_brand_strategist():
    return brand_strategist

def get_project_manager():
    return project_manager

def get_analytics_specialist():
    return analytics_specialist

def run_full_professional_website_project(task: str) -> dict:
    """High-level entry for serious client work — orchestrates the complete intelligent team via project-manager."""
    if project_manager:
        return project_manager.plan_and_coordinate(task)
    return {"error": "project_manager not available — use individual specialists or supervisor"}

def get_legal_compliance_expert():
    return legal_compliance_expert

def get_illustration_3d_asset_specialist():
    return illustration_3d_asset_specialist

def get_maintenance_support_specialist():
    return maintenance_support_specialist

def get_security_auditor():
    return security_auditor

def get_ecommerce_specialist():
    return ecommerce_specialist

def get_typescript_expert():
    return typescript_expert

def get_python_expert():
    return python_expert

def get_cpp_expert():
    return cpp_expert

def get_crypto_payments_expert():
    return crypto_payments_expert

def get_hacash_mining_expert():
    return hacash_mining_expert

def get_hacash_fullnode_expert():
    return hacash_fullnode_expert

def get_hacash_hvm_expert():
    return hacash_hvm_expert

def get_hacash_l1_expert():
    return hacash_l1_expert

def get_hacash_l2_expert():
    return hacash_l2_expert

def get_hacash_l3_expert():
    return hacash_l3_expert

def run_hacash_development_task(task: str) -> dict:
    """High-level for Hacash codebase work - routes to appropriate Hacash specialist or full team via project-manager."""
    if "mining" in task.lower():
        return hacash_mining_expert.implement_mining_features(task) if hacash_mining_expert else {"error": "hacash_mining_expert not available"}
    if "fullnode" in task.lower() or "full node" in task.lower():
        return hacash_fullnode_expert.implement_fullnode_features(task) if hacash_fullnode_expert else {"error": "hacash_fullnode_expert not available"}
    if "hvm" in task.lower() or "virtual machine" in task.lower():
        return hacash_hvm_expert.implement_hvm_contracts(task) if hacash_hvm_expert else {"error": "hacash_hvm_expert not available"}
    if "l1" in task.lower() or "layer 1" in task.lower():
        return hacash_l1_expert.implement_l1_features(task) if hacash_l1_expert else {"error": "hacash_l1_expert not available"}
    if "l2" in task.lower() or "layer 2" in task.lower() or "channel" in task.lower():
        return hacash_l2_expert.implement_l2_features(task) if hacash_l2_expert else {"error": "hacash_l2_expert not available"}
    if "l3" in task.lower() or "layer 3" in task.lower() or "rollup" in task.lower():
        return hacash_l3_expert.implement_l3_features(task) if hacash_l3_expert else {"error": "hacash_l3_expert not available"}
    # Default to project manager for full Hacash dev
    if project_manager:
        return project_manager.plan_and_coordinate("Hacash development: " + task)
    return {"error": "no matching Hacash specialist or project_manager"}

def get_v2_orchestrator():
    """Direct access to the full multi-agent orchestrator."""
    return v2.orchestrator

# For OpenHands skill registration
if __name__ == "__main__":
    print("OpenHands v2 Entry ready. Call run_task(your_task)")
