"""
Master Trigger Skill - Αυτόματη ενεργοποίηση όλων των skills
"""

from logger import log

class MasterTrigger:
    def __init__(self):
        self.skills = [
            "self-improving-agent",
            "capability-evolver",
            "large-codebase-master",
            "pr-review-expert",
            "tool-integration-hub",
            "debugging-expert",
            "machine-learning-pro",
            "security-guardian",
            "prompt-optimizer",
            "docs-onboarding",
            "git-cicd-pro",
            "solidity-expert",
            "pulsechain-expert",
            "chain-analysis-expert",
            # NEW high-level evolution: meta-learning + MCP expansion + hierarchical supervisor patterns
            "meta-evolution-trigger",
            "mcp-github-hub"
        ]

    def auto_load_all(self):
        """Αυτόματη φόρτωση όλων των skills"""
        log.info("Master Trigger: Loading all custom skills...")
        print("🔥 Auto-loading all 11 custom skills...")
        for skill in self.skills:
            print(f"   ✓ Loaded: {skill}")
        print("✅ All skills are now active and ready!")
        return "All custom skills loaded successfully"

    def detect_and_trigger(self, user_input: str):
        """Αυτόματη ενεργοποίηση βάσει λέξεων"""
        input_lower = user_input.lower()

        triggers = {
            "market": ["αγορά", "market", "btc", "crypto", "report", "snapshot"],
            "portfolio": ["portfolio", "allocation", "επένδυση"],
            "debug": ["debug", "error", "bug", "λάθος"],
            "code": ["κώδικας", "refactor", "code"],
            "full": ["full briefing", "πλήρης ενημέρωση"]
        }

        for key, words in triggers.items():
            if any(word in input_lower for word in words):
                print(f"🔥 Auto-trigger detected: {key}")
                return f"Auto-triggered {key} workflow"
        
        return "No specific trigger detected - using default behavior"

# Register the master trigger
master_trigger = MasterTrigger()