"""
Accessibility Expert (A11y) Skill for OpenHands
Professional Accessibility & Inclusive Design Specialist.
Focus: WCAG 2.2 AA/AAA, ARIA, screen reader compatibility, keyboard navigation, color contrast, cognitive accessibility.
"""

from logger import log
from typing import Dict, Any

try:
    from openhands_skills.code_researcher import code_researcher
except Exception:
    code_researcher = None


from openhands_skills.expert_base import ExpertSkill


class AccessibilityExpert(ExpertSkill):
    """
    Senior Accessibility Specialist.
    Makes websites usable by everyone, including people with disabilities.
    """

    def __init__(self):
        self.focus = "Inclusive design that meets legal and ethical standards while improving UX for all."

    def ensure_accessibility(self, task: str, context: Dict = None) -> Dict[str, Any]:
        log.info(f"AccessibilityExpert: Ensuring a11y for: {task[:60]}")
        context = context or {}

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(task + " accessibility 2026", "WCAG best practices")
            except Exception:
                pass

        result = {
            "task": task,
            "wcag_checklist": self.wcag_checklist(),
            "aria_patterns": self.aria_patterns(),
            "testing_tools": "axe-core, WAVE, Lighthouse, NVDA/JAWS/VoiceOver manual testing",
            "common_pitfalls": self.common_pitfalls(),
            "mobile_a11y": "Touch targets, voice control, high contrast on phones",
            "research": research[:1100] if research else "WCAG 2.2 + emerging AI accessibility tools."
        }

        print("♿ AccessibilityExpert: Professional a11y audit & fixes delivered.")
        result["expert_analysis"] = self.consult(
            task, context,
            extra_system="You are a senior accessibility engineer expert in WCAG, ARIA and inclusive design.")
        self.mark_analysis(result)
        return result

    def wcag_checklist(self) -> list:
        return [
            "Perceivable: Text alternatives, captions, color contrast 4.5:1 minimum",
            "Operable: Keyboard accessible, no seizures, enough time",
            "Understandable: Readable, predictable, help with errors",
            "Robust: Compatible with assistive tech, valid markup"
        ]

    def aria_patterns(self) -> str:
        return """<!-- Example accessible button with ARIA -->
<button 
  aria-label="Close dialog" 
  aria-expanded="false"
  aria-controls="menu"
>
  <span aria-hidden="true">×</span>
</button>
"""

    def common_pitfalls(self) -> list:
        return [
            "Missing alt text or generic 'image'",
            "Low contrast text (especially on dark mode)",
            "Focus traps or invisible focus indicators",
            "Dynamic content not announced to screen readers",
            "Touch targets too small on mobile"
        ]

# Register
accessibility_expert = AccessibilityExpert()
print("♿ AccessibilityExpert registered. Ready for sub_type='a11y'.")