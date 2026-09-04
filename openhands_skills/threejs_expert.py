"""
ThreeJS Expert Skill for OpenHands
Deep specialist for Three.js, WebGL, 3D on the web.
Focus: Advanced scenes, performance optimization (especially mobile), interactions, lighting, post-processing, model loading.
"""

from logger import log
from typing import Dict, Any

try:
    from openhands_skills.code_researcher import code_researcher
except Exception:
    code_researcher = None


from openhands_skills.expert_base import ExpertSkill


class ThreeJSExpert(ExpertSkill):
    def __init__(self):
        self.focus = "High-quality, performant 3D experiences that work great on desktop and degrade gracefully on mobile."

    def create_threejs_scene(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """Senior 3D web engineer output: full scene spec + optimized code + mobile degradation strategy."""
        log.info(f"ThreeJSExpert: Creating 3D scene for: {task[:60]}")
        context = context or {}

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(task + " three.js performance", "three.js 2026 best practices")
            except Exception:
                pass

        result = {
            "task": task,
            "recommended_stack": "@react-three/fiber + @react-three/drei + three (React) | pure three.js + GSAP + postprocessing (vanilla)",
            "scene_concept": self._scene_ideas(task),
            "technical_spec": {
                "renderer": "WebGLRenderer with alpha + antialias, powerPreference: 'high-performance'",
                "camera": "PerspectiveCamera with fov 42-55, near 0.1, far 1000",
                "lighting": "1 ambient + 1-2 directional + optional environment map (HDR)",
                "post_processing": "UnrealBloomPass + SMAAPass for premium feel (desktop only)",
                "controls": "OrbitControls or custom GSAP-driven for hero moments"
            },
            "performance_audit": self.performance_audit_for_mobile(),
            "mobile_degradation_strategy": self._mobile_degradation_strategy(),
            "production_code": self._production_ready_code(),
            "research": research[:1400] if research else "Follow drei + fiber patterns + real device profiling."
        }

        print("🧊 ThreeJSExpert: Senior 3D web spec delivered (with mobile optimization).")
        result["expert_analysis"] = self.consult(
            task, context,
            extra_system="You are a senior WebGL/Three.js engineer expert in real-time 3D and GPU performance.")
        self.mark_analysis(result)
        return result

    def performance_audit_for_mobile(self) -> Dict[str, Any]:
        """What a real Three.js performance engineer would check on phones."""
        return {
            "target_fps": "58-60 on iPhone 15/16, 45+ on mid-range Android",
            "draw_calls": "Keep under 25-30 on mobile",
            "triangles": "Max 80k-120k on high-end, 25k-40k on mid-range",
            "textures": "Use Basis or KTX2, max 2-3 textures, power-of-two",
            "dpr": "window.devicePixelRatio capped at 1.5 (or 1.0 on low-end)",
            "tools": "Use three.js inspector + Chrome Performance + real device + WebGL report"
        }

    def _mobile_degradation_strategy(self) -> str:
        return """
Professional mobile 3D strategy:
- Desktop: full quality + post-processing + high DPR
- Tablet: medium quality, disable bloom, cap DPR 1.5
- Phone: static hero image or very low-poly + simple lighting + toggle "Enable 3D" 
- Always provide graceful fallback + performance toggle in settings
- Profile on real devices (not emulator) with 3G/4G throttling
"""

    def _production_ready_code(self) -> str:
        return """// Senior-level React + R3F production skeleton (with mobile awareness)
import { Canvas } from '@react-three/fiber'
import { OrbitControls, Environment } from '@react-three/drei'
import { useMemo } from 'react'

function Scene({ quality = 'high' }) {
  const dpr = useMemo(() => Math.min(window.devicePixelRatio, quality === 'high' ? 1.8 : 1.0), [quality])
  
  return (
    <>
      <ambientLight intensity={quality === 'high' ? 0.6 : 0.8} />
      <directionalLight position={[5, 10, 5]} intensity={1.2} castShadow={quality === 'high'} />
      <mesh>
        <torusGeometry args={[1.3, 0.45, quality === 'high' ? 32 : 16, 64]} />
        <meshStandardMaterial color="#67e8f9" metalness={0.65} roughness={0.25} />
      </mesh>
      {quality === 'high' && <Environment preset="city" />}
    </>
  )
}

<Canvas 
  camera={{ position: [0, 0, 7.5], fov: 48 }} 
  dpr={dpr}
  style={{ background: 'transparent' }}
  gl={{ alpha: true, antialias: quality === 'high', powerPreference: 'high-performance' }}
>
  <Scene quality={isMobile ? 'low' : 'high'} />
  <OrbitControls enablePan={false} enableZoom={!isMobile} />
</Canvas>
"""

    def _scene_ideas(self, task: str) -> list:
        return [
            "Clean product hero with subtle rotation + environment map",
            "Interactive particles that react to scroll/mouse (but low count on mobile)",
            "Abstract geometric background that responds to user movement",
            "Simple model viewer with orbit controls + nice lighting"
        ]

    def _performance_tips(self) -> list:
        return [
            "Always use instancing for repeated geometry",
            "Bake lighting when possible",
            "Use LOD (Level of Detail)",
            "Cap pixel ratio: Math.min(window.devicePixelRatio, 1.5) or lower on mobile",
            "Dispose geometries and materials on unmount",
            "Test on mid-range Android phones"
        ]

    def _basic_skeleton(self) -> str:
        return """// React + @react-three/fiber example (recommended)
import { Canvas } from '@react-three/fiber'
import { OrbitControls, Stars } from '@react-three/drei'

function Scene() {
  return (
    <>
      <ambientLight intensity={0.6} />
      <pointLight position={[10, 10, 10]} />
      <mesh>
        <torusGeometry args={[1.2, 0.4, 16, 64]} />
        <meshStandardMaterial color="#67e8f9" metalness={0.6} roughness={0.3} />
      </mesh>
      <Stars />
    </>
  )
}

<Canvas camera={{ position: [0, 0, 7], fov: 45 }} style={{ background: 'transparent' }}>
  <Scene />
  <OrbitControls enablePan={false} enableZoom={false} />
</Canvas>
"""

    # GOD-TIER DEEP METHODS
    def god_tier_create_threejs_scene(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """GOD-LIKE: Production 3D at institutional level — perf budgets, fallbacks, WASM integration, Hacash-specific viz, handoffs."""
        log.info(f"ThreeJSExpert (GOD TIER): God-like 3D scene for: {task[:60]}")
        base = self.create_threejs_scene(task, context)

        god = {
            **base,
            "god_tier_additions": {
                "strict_budgets": self.performance_audit_for_mobile(),
                "wasm_integration": "For live data-driven 3D (e.g. hashrate affecting particle count/color, diamond value changing geometry or emissive, channel health driving animation speed): expose clean API from WASM (via programmer + cpp-expert) and feed into R3F scene with useFrame. Never block the render thread.",
                "hacash_viz_examples": [
                    "Rotating premium HACD diamond with live on-chain attributes (color shifts on ownership/peg events)",
                    "Hashrate 'terrain' or instanced GPU cards that pulse with real pool shares",
                    "L2 channel state machine: elegant 3D pipes or orbs that open/close/settle with L1 finality",
                    "Peg flow visualization (BTC → Hacash) with volume particles"
                ],
                "production_pipeline": "drei + fiber for React. GLTF + KTX2 pipeline. Post-processing (bloom, SMAA) desktop only via feature flag. Full dispose on unmount. Error boundary + fallback static image in the React tree.",
                "testing": "Screenshot + perf regression on CI for key scenes (desktop + simulated mobile). Real device manual sign-off for any new 3D hero."
            },
            "mobile_god_strategy": self._mobile_degradation_strategy(),
            "handoffs": "website_builder.god_tier_3d_performance_and_fallback_strategy, react_specialist for island integration, programmer for WASM heavy math, hacash_* experts for the data semantics, mobile for the overall responsive container.",
            "god_tier_level": "3D is never an afterthought. It must enhance trust and delight without compromising the core experience on the devices real users actually have."
        }
        print("🧊 ThreeJSExpert (GOD TIER): God-like 3D scene + pipeline delivered.")
        return god

    def god_tier_threejs_production_pipeline(self) -> Dict[str, Any]:
        """Full production checklist for shipping Three.js in client work."""
        return {
            "assets": "GLTF + Draco + KTX2. Basis for textures. Optimize in Blender + gltf-transform.",
            "code": "Use the _production_ready_code pattern + extend with R3F best practices. Lazy load the entire Canvas island.",
            "perf_enforcement": "Hard caps in code + CI. Real device matrix sign-off before merge.",
            "integration_with_payments_hacash": "3D reacts to price/amount (WASM) or on-chain state (RPC). Subtle, beautiful, never distracting from the money flow."
        }

# Register
threejs_expert = ThreeJSExpert()
print("🧊 ThreeJSExpert (GOD TIER) registered. Ready for sub_type='threejs'. Institutional 3D with mobile god-tier perf, WASM data binding, Hacash viz.")