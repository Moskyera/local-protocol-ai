"""
OpenHands Multi-Agent v2 Package
Ready for integration with OpenHands / custom LLM agents for development tasks
(e.g. smart contracts on EVM, HVM, research, coding, debugging).

Main exports:
- advanced_supervisor
- smart_trigger
- orchestrator
- strategic_oracle
- hyper_evolver
- The individual agents (coder, tester, etc.)
"""

from .advanced_supervisor import advanced_supervisor
from .smart_trigger_system import smart_trigger
from .multi_agent_orchestrator_v2 import orchestrator
from .strategic_oracle import strategic_oracle
from .hyper_evolution_agent import hyper_evolver

# Individual agents for direct use
from .market_analyst_agent_v2 import market_analyst
from .coder_agent_v2 import coder
from .tester_agent_v2 import tester
from .reviewer_agent_v2 import reviewer
from .debugger_agent_v2 import debugger
from .security_agent_v2 import security
from .code_intelligence import code_intelligence
from .self_correcting_coder import self_correcting_coder

# Solidity expert for EVM / Smart Contracts development (main focus for future OpenHands use)
from openhands_skills.solidity_expert import solidity_expert
from openhands_skills.pulsechain_expert import pulsechain_expert
from openhands_skills.chain_analysis_expert import chain_analysis_expert

__all__ = [
    "advanced_supervisor",
    "smart_trigger",
    "orchestrator",
    "strategic_oracle",
    "hyper_evolver",
    "market_analyst",
    "coder",
    "tester",
    "reviewer",
    "debugger",
    "security",
    "code_intelligence",
    "self_correcting_coder",
    "solidity_expert",
    "pulsechain_expert",
    "chain_analysis_expert",
]
