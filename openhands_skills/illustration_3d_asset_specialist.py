"""
Illustration & 3D Asset Specialist Skill for OpenHands
Professional 3D Asset & Illustration Specialist.
Focus: Creation, optimization, texturing, rigging, and web-optimized delivery of 3D models, illustrations, icons, and visual assets for modern websites (especially Three.js / React / mobile).
Critical for high-quality visual work without killing performance.
"""

from logger import log
from typing import Dict, Any

try:
    from openhands_skills.code_researcher import code_researcher
except Exception:
    code_researcher = None

try:
    from persistent_memory import persistent_memory
except Exception:
    persistent_memory = None


from openhands_skills.expert_base import ExpertSkill


class Illustration3DAssetSpecialist(ExpertSkill):
    """
    Senior 3D Asset & Illustration Specialist.
    Delivers production-ready, performance-optimized visual assets tailored for web (desktop + mobile).
    Works hand-in-hand with threejs-expert, website-builder, and brand-strategist.
    """

    def __init__(self):
        self.focus = "Creating and optimizing beautiful, lightweight 3D models and illustrations that elevate professional websites without compromising speed or quality."

    def create_asset_pipeline(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """Main professional entry: Complete asset strategy + creation guidelines + optimized deliverables for the project."""
        log.info(f"Illustration3DAssetSpecialist: Creating asset pipeline for: {task[:60]}")
        context = context or {}

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(task + " 3D assets web optimization 2026", "professional 3D asset pipeline for web")
            except Exception:
                pass

        result = {
            "task": task,
            "asset_strategy": self.asset_strategy(task),
            "creation_pipeline": self.creation_pipeline(),
            "optimization_standards": self.optimization_standards(),
            "delivery_formats": self.delivery_formats(),
            "integration_notes": self.integration_notes(),
            "mobile_considerations": self.mobile_considerations(),
            "research": research[:1200] if research else "2026 web 3D asset best practices (glTF, Draco, KTX2, LOD, texture baking)."
        }

        if persistent_memory:
            try:
                persistent_memory.store_learning("assets:3d", f"{task} | professional 3D/illustration asset system")
            except Exception:
                pass

        print("🎨 Illustration3DAssetSpecialist: Complete professional asset pipeline delivered.")
        result["expert_analysis"] = self.consult(
            task, context, extra_system="You are a senior 3D/visual asset specialist focused on performance-first production assets.")
        self.mark_analysis(result)
        return result

    def asset_strategy(self, project: str) -> dict:
        """An asset plan for THIS project.

        Returned the same four lines for everything — "1-2 high-impact 3D
        models (torus, abstract product, environment)" was proposed for a
        medical clinic and a DeFi protocol alike, byte for byte.
        """
        return self.analyse(
            "Plan the visual assets for this specific project: what to make, in "
            "what style, at what fidelity, and what NOT to make. Give a concrete "
            "payload budget and say which assets are load-bearing versus "
            "decorative. If 3D would be wrong for this project, say so.",
            {"project": project},
            reference={"general_3d_guidance": {
                "style_direction": "Consistent with brand guidelines. Clean, premium, modern. Avoid overly complex geometry unless justified.",
                "hero_assets": "1-2 high-impact 3D models with subtle animation.",
                "supporting_assets": "Icons, decorative elements, product variants as low-poly or baked textures.",
                "performance_budget": "Total 3D payload < 2-3MB gzipped for mobile hero; use progressive loading.",
            }},
            max_tokens=1200,
        )

    def creation_pipeline(self) -> list:
        return [
            "Concept & reference (align with brand-strategist)",
            "Modeling in Blender / Cinema 4D (keep topology clean)",
            "UV unwrapping + texturing (PBR or stylized)",
            "Rigging / animation if interactive",
            "Export: glTF 2.0 + Draco compression + KTX2 textures",
            "LOD generation (3-4 levels)",
            "Web testing in target environments (Three.js / R3F)"
        ]

    def optimization_standards(self) -> Dict[str, str]:
        return {
            "geometry": "Draco compression, merge meshes where possible, remove hidden faces",
            "textures": "KTX2 + Basis, power-of-two sizes, max 2k for hero, 512-1k for supporting",
            "materials": "Bake lighting where possible, use shared materials, avoid complex shaders on mobile",
            "animation": "Bake to sparse keyframes or morph targets; limit bone count",
            "delivery": "Progressive loading, CDN, cache headers, lazy-load non-critical assets"
        }

    def delivery_formats(self) -> list:
        return [
            "glTF (.glb) - primary for Three.js",
            "USDZ - for AR quick look on iOS",
            "PNG/JPG fallbacks + Lottie for 2D illustrations",
            "Optimized SVG for icons (with brand colors as CSS variables)"
        ]

    def integration_notes(self) -> str:
        return """Integration with threejs-expert / react-specialist / website-builder:
- Provide asset URLs + metadata (poly count, texture size, animation clips)
- Supply recommended Three.js material + lighting setup
- Include mobile fallback image + "load 3D" button
- Document interaction controls and performance toggles
"""

    def mobile_considerations(self) -> list:
        return [
            "Auto-detect device and serve lower LOD + baked lighting",
            "Disable shadows, post-processing, or high-res textures below 768px",
            "Provide static hero image that matches the 3D look",
            "Test on real mid-range Android (throttled CPU/GPU)"
        ]

# Register
illustration_3d_asset_specialist = Illustration3DAssetSpecialist()
print("🎨 Illustration3DAssetSpecialist registered. Ready for sub_type='illustration'. Professional visual assets for real projects.")