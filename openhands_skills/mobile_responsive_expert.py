"""
Mobile & Responsive Expert Skill for OpenHands
Specialist for making websites shine on phones and tablets.
Focus: Responsive strategies, touch interactions, mobile performance, different screen sizes, thumb zones, PWA, real-device testing mindset.
"""

from logger import log
from typing import Dict, Any

try:
    from openhands_skills.code_researcher import code_researcher
except Exception:
    code_researcher = None


from openhands_skills.expert_base import ExpertSkill


class MobileResponsiveExpert(ExpertSkill):
    def __init__(self):
        self.focus = "Websites that feel native and excellent on mobile (where most users actually experience them)."

    def make_responsive(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """Senior mobile web specialist deliverable: complete responsive + mobile strategy with real-device focus."""
        log.info(f"MobileResponsiveExpert: Optimizing for mobile: {task[:60]}")
        context = context or {}

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(task + " mobile first responsive", "mobile web 2026 best practices")
            except Exception:
                pass

        result = {
            "task": task,
            "core_principles": self._core_principles(),
            "breakpoints_and_fluid": self._breakpoints(),
            "touch_and_gestures": self.touch_gesture_specs(),
            "performance_budget": self.mobile_performance_budget(),
            "device_testing_checklist": self.device_testing_checklist(),
            "pwa_and_install": "Provide web app manifest + service worker for offline + install prompt on Chrome/Safari.",
            "research": research[:1200] if research else "Real mobile web expertise (2026)."
        }

        print("📱 MobileResponsiveExpert: Senior mobile strategy delivered.")
        result["expert_analysis"] = self.consult(
            task, context,
            extra_system="You are a senior front-end engineer expert in responsive and mobile-first UX and performance.")
        self.mark_analysis(result)
        return result

    def _core_principles(self) -> list:
        return [
            "Design for 375px (iPhone) first — everything else is enhancement",
            "Touch targets minimum 44-48px with proper spacing",
            "Thumb zone: put primary actions in the comfortable bottom area",
            "Fluid everything (typography, spacing, layout) using clamp() + container queries",
            "Performance first on mobile: 3G/4G simulation, real device profiling"
        ]

    def touch_gesture_specs(self) -> Dict[str, str]:
        return {
            "tap": "44x44 minimum, 200ms visual feedback, no 300ms delay",
            "swipe": "Horizontal for carousels, vertical for pull-to-refresh (with proper thresholds)",
            "long_press": "Use for context menus (with haptic if possible)",
            "css_tips": "-webkit-tap-highlight-color: transparent; touch-action: manipulation;"
        }

    def mobile_performance_budget(self) -> Dict[str, str]:
        return {
            "lighthouse_mobile": "Performance ≥ 90, Accessibility ≥ 95, Best Practices 95+",
            "initial_js": "< 180-220kb gzipped (including React + Tailwind + Framer)",
            "images": "Use AVIF/WebP, responsive images with srcset, lazy loading",
            "3d": "Disable or heavily degrade below 640px unless user explicitly enables",
            "real_devices": "Test on iPhone 15/16 + Pixel 8/9 + one mid-range Android (3G throttling)"
        }

    def device_testing_checklist(self) -> list:
        return [
            "iPhone 15/16 (latest iOS) - notch, dynamic island, safe areas",
            "Pixel 8/9 or Samsung Galaxy (mid-range Android) - 3G simulation",
            "One older device (e.g. iPhone 12 or Galaxy S21) for performance baseline",
            "Landscape + portrait on all",
            "One-handed use test (thumb reach)"
        ]

    def _breakpoints(self) -> str:
        return """
Recommended approach:
- Base: 320px-639px (phones) — design everything here first
- sm: 640px+
- md: 768px+
- lg+: desktop

Use container queries for component-level responsiveness.
"""

    # GOD-TIER DEEP METHODS
    def god_tier_make_responsive(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """GOD-LIKE: Mobile-first at the level of native apps. Real device obsession, touch, PWA, 3D degradation, a11y, payments on thumb."""
        log.info(f"MobileResponsiveExpert (GOD TIER): God-like mobile strategy for: {task[:60]}")
        base = self.make_responsive(task, context)

        god = {
            **base,
            "god_tier_additions": {
                "thumb_zone_religion": "Primary CTAs, payment confirm, 3D toggle, explorer refresh — all comfortably in the bottom 55-60% on 375px. Never fight the thumb.",
                "3d_on_mobile": "Default: beautiful static or low-poly hero. Explicit 'Load rich 3D' opt-in with clear perf warning. Auto-detect low-end via simple benchmark or user setting. Always provide reduced-motion path.",
                "payments_on_thumb": "Stripe card / crypto connect flows must be one-thumb operable. Large hit areas, clear loading + success states that don't require scrolling.",
                "hacash_mobile": "Mining dashboards, channel lists, diamond viewers must be delightful on phones (most real users). Tables become cards or virtualized lists. Live updates via pull-to-refresh or explicit button (the dashboard pattern).",
                "real_device_gates": self.device_testing_checklist(),
                "pwa_god": "Full manifest + offline shell for explorers + service worker that caches critical RPC responses + 3D assets. Install prompt on second visit. Feels like a real app.",
                "a11y_non_negotiable": "WCAG 2.2 AA minimum, AAA where cheap (contrast, focus). Reduced motion everywhere. Screen reader labels for all 3D controls and charts."
            },
            "handoffs": "designer.god_tier for tokens + mobile UX checklist, threejs.god_tier for degradation, react for component implementation, website_builder.god_tier for the overall shell + 3D + payment integration.",
            "god_tier_level": "If the experience is worse on a mid-range Android than on a MacBook, it is not god-tier. Most of the world uses phones."
        }
        print("📱 MobileResponsiveExpert (GOD TIER): God-like mobile strategy delivered.")
        return god

    def god_tier_mobile_production_checklist(self) -> Dict[str, Any]:
        """The exhaustive real-world checklist a 10x mobile web specialist ships with every project."""
        return {
            "testing_matrix": "iPhone 15/16 Pro, iPhone SE, Pixel 8/9, Samsung A5x / S23 mid, one very low-end Android. 3G/4G + WiFi. Portrait primary.",
            "perf": self.mobile_performance_budget(),
            "touch_gestures": self.touch_gesture_specs(),
            "3d_payments_a11y": "All covered in god_tier_make_responsive + coordination with the other god_tier specialists.",
            "pwa_offline": "Critical for explorers and dashboards."
        }

# Register
mobile_responsive_expert = MobileResponsiveExpert()
print("📱 MobileResponsiveExpert (GOD TIER) registered. Ready for sub_type='mobile'. Thumb-zone, 3D degradation, PWA, real-device, Hacash-on-phone god level.")