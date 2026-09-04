"""
QA Engineer Skill for OpenHands
Professional Quality Assurance & Testing Specialist.
Focus: Automated testing, cross-browser/device, accessibility testing, performance regression, bug prevention.
"""

from logger import log
from typing import Dict, Any

try:
    from openhands_skills.code_researcher import code_researcher
except Exception:
    code_researcher = None


from openhands_skills.expert_base import ExpertSkill


class QAEngineer(ExpertSkill):
    """
    Senior QA Engineer for websites.
    Ensures production quality across devices, browsers, and user scenarios.
    """

    def __init__(self):
        self.focus = "Delivering bug-free, high-quality websites that work everywhere."

    def run_quality_assurance(self, task: str, context: Dict = None) -> Dict[str, Any]:
        log.info(f"QAEngineer: Running QA for: {task[:60]}")
        context = context or {}

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(task + " testing 2026", "web QA best practices")
            except Exception:
                pass

        result = {
            "task": task,
            "testing_strategy": self.testing_strategy(),
            "automated_test_suite": self.suggested_test_suite(),
            "cross_device_checklist": self.cross_device_checklist(),
            "bug_prevention_tips": self.bug_prevention_tips(),
            "tools_recommendation": "Playwright (E2E + visual), Jest + React Testing Library, Lighthouse CI, axe-core for a11y",
            "research": research[:1100] if research else "Modern web testing with AI-assisted and visual regression."
        }

        print("✅ QAEngineer: Professional QA plan delivered.")
        result["expert_analysis"] = self.consult(
            task, context,
            extra_system="You are a senior QA engineer specialised in test strategy, edge cases and cross-device quality.")
        self.mark_analysis(result)
        return result

    def testing_strategy(self) -> list:
        return [
            "Unit tests for critical components (React Testing Library)",
            "Integration tests for user flows",
            "E2E with Playwright (desktop + mobile emulation)",
            "Visual regression testing (Percy or built-in Playwright)",
            "Performance regression with Lighthouse CI in pipeline",
            "Accessibility audits on every PR (axe + manual screen reader)"
        ]

    def suggested_test_suite(self) -> str:
        return """// Example Playwright E2E test skeleton (add to tests/)
import { test, expect } from '@playwright/test';

test('mobile hero loads and 3D is optional', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('h1')).toContainText('...');
  // Check mobile menu, touch targets, etc.
});
"""

    def cross_device_checklist(self) -> list:
        return [
            "iOS Safari latest + previous",
            "Android Chrome (mid-range device)",
            "Desktop Chrome, Firefox, Safari, Edge",
            "Landscape/portrait on phones",
            "Slow network (3G) + offline scenarios",
            "Reduced motion + high contrast modes"
        ]

    def bug_prevention_tips(self) -> list:
        return [
            "Use feature flags for experimental 3D/animations",
            "Always test with real devices, not just emulators",
            "Monitor console errors and network failures in prod",
            "Add visual regression for key pages"
        ]

# Register
qa_engineer = QAEngineer()
print("✅ QAEngineer registered. Ready for sub_type='qa'.")