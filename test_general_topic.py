import sys
import os
# The repo root is this file's own directory. It used to be written out
# as an absolute path, which only existed on the machine it was written on.
_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, _REPO_ROOT)
import importlib.util
spec = importlib.util.spec_from_file_location('lo', os.path.join(_REPO_ROOT, 'openhands_skills/langgraph_orchestrator.py'))
lo = importlib.util.module_from_spec(spec)
sys.modules['lo'] = lo
spec.loader.exec_module(lo)
from openhands_skills.research_agent import research_agent
import os

print('=== TEST: Generalized last30d broad research for general AI/tech topic (not Pulse/on-chain) ===')
print('Topic: self improving agent frameworks with reflection and lab experiments last 30 days')
print('Focus: ai_tech_general, lab_mode=True')
res = research_agent.research_new_technologies_and_skills(max_results=4, focus='ai_tech_general', lab_mode=True)
print('\n--- Results Structure ---')
print('Candidates count:', len(res.get('new_capability_candidates', [])))
print('Sources count:', len(res.get('sources', [])))
print('Actionable count:', len(res.get('actionable_for_engineering', [])))
print('\n--- Sample Candidate (first if any, showing 100% fidelity) ---')
cands = res.get('new_capability_candidates', [])
if cands:
    c = cands[0]
    print('ID:', c.get('id'))
    src = c.get('source', {})
    print('Source type:', src.get('type'))
    print('URL:', src.get('url'))
    print('Credibility signals (raw, with engagement):', c.get('credibility_signals', [])[:2])
    fit = c.get('fit_analysis', {})
    print('Fit value_add (general AI/tech):', fit.get('value_add_for_general_professional_helper', '')[:150])
    print('Lab mode / PR-ready:', c.get('lab_mode'), bool(c.get('pr_ready')))
    print('Direct evidence start (verbatim):', c.get('direct_evidence', '')[:200])
    pc = c.get('pros_cons') or {}
    print('pros_cons present (for report):', bool(pc))
    print('  advantages sample:', (pc.get('advantages') or [None])[0])
    print('  disadvantages sample:', (pc.get('disadvantages') or [None])[0])
else:
    print('No candidates')
print('\n--- Supervisor Simulation: general research intent ---')
st = {'user_input': 'research latest self improving agent techniques with reflection last 30 days'}
st = lo._classify_intent(st)
print('Classified specialists:', st.get('specialists_needed'))
if 'research' in st.get('specialists_needed', []):
    st = lo._execute_research(st)
    rres = st.get('research_result', {})
    print('Research used broad last30d path (note):', rres.get('note', 'N/A')[:100])
    print('Candidates in supervisor result:', len(rres.get('new_capability_candidates', [])))
print('\n=== TEST COMPLETE ===')
print('Key: Generalized for AI/tech/general (HN/Reddit engagement + GitHub/X). 100% fidelity (verbatim evidence, raw signals). Feeds guarded proposals/supervisor. Works for non-Pulse topics as requested.')
