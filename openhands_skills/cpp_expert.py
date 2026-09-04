"""
C++ Expert Skill for OpenHands
Professional C++ Specialist for high-performance components.
Focus: High-performance computing, 3D engines and simulations, WASM compilation, low-level optimizations, performance-critical modules that can be called from web (via WASM or native).
For projects where raw speed or complex computations matter (3D, physics, data processing, AI inference).
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


class CppExpert(ExpertSkill):
    """
    Senior C++ Specialist.
    Delivers high-performance, safe, modern C++ (C++17/20/23) components, often for web via Emscripten/WASM or as backend services.
    Works closely with threejs-expert, react, python, and performance needs.
    """

    def __init__(self):
        self.focus = "Building blazing-fast, reliable C++ components that give professional websites a competitive edge in performance and capabilities."

    def build_high_performance_components(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """Main professional entry: High-performance C++ architecture + WASM strategy + integration plan."""
        log.info(f"CppExpert: Building high-performance components for: {task[:60]}")
        context = context or {}

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(task + " c++ web performance 2026", "modern C++ WASM Emscripten best practices high performance computing")
            except Exception:
                pass

        result = {
            "task": task,
            "recommended_approach": "Modern C++ (C++20/23) + Emscripten for WASM, or native backend service",
            "use_cases_for_web": self.use_cases_for_web(),
            "modern_cpp_guidelines": self.modern_cpp_guidelines(),
            "wasm_compilation_strategy": self.wasm_compilation_strategy(),
            "performance_techniques": self.performance_techniques(),
            "integration_with_web_team": self.integration_with_web_team(),
            "payment_heavy_computation_wasm": self.payment_heavy_wasm_example(),  # for crypto/3D payments
            "research": research[:1100] if research else "2026 C++ for web (WASM), performance, safety, and integration patterns."
        }

        if persistent_memory:
            try:
                persistent_memory.store_learning("cpp:performance", f"{task} | professional high-performance C++ components")
            except Exception:
                pass

        print("⚡ CppExpert: Complete professional high-performance C++ plan delivered (with payment WASM).")
        result["expert_analysis"] = self.consult(
            task, context, extra_system="You are a senior C++ engineer expert in high-performance, low-level and WASM/compute-heavy code.")
        self.mark_analysis(result)
        return result

    def payment_heavy_wasm_example(self) -> str:
        """Example C++ code (to be compiled to WASM via Emscripten) for heavy payment logic called from React 3D + crypto checkout.
        E.g. dynamic pricing based on 3D config + risk scoring + gas estimation.
        """
        return """// C++ (modern) - compile with emcc to .wasm + .js glue (see cpp-expert for build command)
// Expose to JS: calculateHeavyPriceAndRisk(basePrice, configJSON, timestamp)

#include <emscripten.h>
#include <string>
#include <cmath>
#include <nlohmann/json.hpp>  // for JSON (or rapidjson)

using json = nlohmann::json;

extern "C" {
  EMSCRIPTEN_KEEPALIVE
  char* calculateHeavyPriceAndRisk(double basePrice, const char* configJSON, long timestamp) {
    json config = json::parse(configJSON);
    
    // Heavy computation: complex pricing model (e.g. material rarity, 3D complexity, market volatility)
    double multiplier = 1.0;
    if (config.contains("material") && config["material"] == "gold") multiplier *= 1.8;
    if (config.contains("complexity")) multiplier *= (1.0 + config["complexity"].get<double>() * 0.15);
    
    // Risk scoring (fraud / volatility) - could load ML model or formula
    double risk = std::min(0.95, std::abs(std::sin(timestamp / 10000.0)) * 0.4 + config.value("complexity", 0.0) * 0.05);
    
    // Gas estimation simulation (real version would call on-chain oracles or formula)
    double gas = 21000 + (config.value("complexity", 1.0) * 15000);
    
    double finalPrice = basePrice * multiplier;
    
    json result = {
      {"finalPrice", finalPrice},
      {"risk", risk},
      {"gas", gas},
      {"timestamp", timestamp}
    };
    
    std::string jsonStr = result.dump();
    char* cstr = (char*)malloc(jsonStr.length() + 1);
    strcpy(cstr, jsonStr.c_str());
    return cstr;  // JS must free
  }
}

// EXACT BUILD COMMAND for the payment WASM (run from the directory with the .cpp file):
// emcc payment_pricing.cpp -o cpp_payment_wasm.js \
//   -s WASM=1 \
//   -s EXPORTED_FUNCTIONS='["_calculateHeavyPriceAndRisk"]' \
//   -s EXPORTED_RUNTIME_METHODS='["ccall","cwrap","UTF8ToString"]' \
//   -s ALLOW_MEMORY_GROWTH=1 \
//   -s INITIAL_MEMORY=16777216 \
//   -O3 -flto \
//   --bind \
//   -I/path/to/nlohmann  # if using json.hpp
//
// Then in React (with the generated .js + .wasm):
// import initWasm, { calculateHeavyPriceAndRisk } from './cpp_payment_wasm.js';
// await initWasm();
// const resultPtr = calculateHeavyPriceAndRisk(base, JSON.stringify(config), Date.now());
// const resultStr = UTF8ToString(resultPtr);
// const result = JSON.parse(resultStr);
// // free(resultPtr) if needed via Module._free if exposed
//
// For production: serve .wasm with correct MIME (application/wasm), use Web Workers for the call to keep 3D smooth.
"""


    def use_cases_for_web(self) -> list:
        return [
            "Complex 3D physics / simulations (faster than JS)",
            "High-fidelity 3D rendering pipelines or custom shaders (WASM)",
            "Heavy data processing / compression / encoding on client or edge",
            "AI inference (ONNX Runtime, custom models) with low latency",
            "Real-time audio/video processing or computer vision"
        ]

    def modern_cpp_guidelines(self) -> list:
        return [
            "Use smart pointers, RAII, move semantics everywhere",
            "Concepts and ranges for cleaner generic code (C++20+)",
            "std::expected or result types for error handling (no exceptions in hot paths)",
            "constexpr where possible for compile-time computation",
            "Strict -Wall -Wextra -Werror + sanitizers (ASan, UBSan) in development"
        ]

    def wasm_compilation_strategy(self) -> Dict[str, str]:
        return {
            "toolchain": "Emscripten (latest) with -O3 -flto, separate memory, SIMD when available",
            "api_surface": "Minimal, well-typed JS<->WASM boundary (use Embind or manual)",
            "memory": "Pre-allocated pools, avoid frequent allocations across boundary",
            "debugging": "Source maps + DWARF for browser debugging",
            "fallback": "Pure JS / WebAssembly fallback for older browsers"
        }

    def performance_techniques(self) -> list:
        return [
            "Profile first (browser profiler + native tools like perf / VTune)",
            "SIMD (AVX / NEON via portable intrinsics or std::simd)",
            "Cache-friendly data layouts (SoA vs AoS)",
            "Threading via Web Workers + Atomics or pthread in WASM",
            "Avoid virtual calls and exceptions in hot loops"
        ]

    def integration_with_web_team(self) -> str:
        return """Integration patterns:
- Expose clean C API or Embind classes consumable from TypeScript
- Provide TypeScript definitions (manually or generated)
- Document memory ownership and lifetime rules
- Performance budgets and benchmarks for the component
- Coordinate with threejs-expert for 3D data exchange (e.g. custom geometry loaders)
- With Python expert for hybrid pipelines (C++ for hot path, Python for orchestration)
"""

# Register
cpp_expert = CppExpert()
print("⚡ CppExpert registered. Ready for sub_type='cpp'. High-performance C++ for serious projects.")