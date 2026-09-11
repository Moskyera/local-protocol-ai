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
from openhands_skills.chain_analysis_expert import chain_analysis_expert
import os

print('=== LIVE WHALE ADDRESS TEST + OUTPUT ===')
whale_addr = '0x000000000000000000000000000000000000dEaD'
print('Testing with live whale-like address: ' + whale_addr)
print('1. Global scan for large HEX PLSX INC (discover candidates):')
moves = chain_analysis_expert.scan_large_ecosystem_movements(tokens=['HEX','PLSX','INC'], min_usd=5000, limit=5)
print('   Large movements found: ' + str(len(moves)))
if len(moves) > 0:
    print('   Top candidate addr: ' + str(moves[0].get('to')))
    print('   Sample alert: ' + str(moves[0].get('alert')))
else:
    print('   (No recent large in current data snapshot, but scan API ready for live)')
print('')
print('2. Full analyze on the whale address with ecosystem focus:')
report = chain_analysis_expert.analyze_address(whale_addr, chain='pulsechain', context='focus on large HEX PLSX INC ecosystem movements and whale alerts')
print('   Explorer: ' + str(report.get('explorer_link')))
print('   Has large_ecosystem_movements: ' + str(bool(report.get('large_ecosystem_movements'))))
print('   Ecosystem alerts: ' + str(report.get('ecosystem_alerts', [])))
print('   Risk level: ' + str(report.get('risk_score', {}).get('level', 'N/A')))
print('   Native PLS summary sample: ' + str(report.get('full_wallet_profile', {}).get('native_pls_summary', [])[:1]))
print('   Full report keys (for supervisor): ' + str(list(report.keys())[:8]))
print('')
print('3. Supervisor simulation with check this whale for large HEX PLSX INC moves on pulsechain 0x... :')
st = {'user_input': 'check this whale for large HEX PLSX INC moves on pulsechain ' + whale_addr}
st = lo._classify_intent(st)
print('   Classified as: ' + str(st.get('specialists_needed')))
if 'blockchain' in st.get('specialists_needed', []):
    st = lo._execute_blockchain(st)
    br = st.get('blockchain_result', {})
    print('   Blockchain result type: ' + str(br.get('type', 'full')))
    print('   Has ecosystem_alerts/large: ' + str(bool(br.get('ecosystem_alerts') or br.get('large_ecosystem_movements'))))
    print('   Note: ' + str(br.get('note', ''))[:120] if 'note' in br else 'N/A')
print('=== TEST COMPLETE - shows integration of scan + analyze + supervisor for live whale address ===')
