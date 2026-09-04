"""
CadArchitect - φτιάχνει ΕΚΤΥΠΩΣΙΜΑ 3D μοντέλα από περιγραφή.

ΠΩΣ ΔΟΥΛΕΥΕΙ ΠΡΑΓΜΑΤΙΚΑ: δεν "παράγει mesh" ένα μοντέλο εικόνας. Το LLM γράφει
ΠΑΡΑΜΕΤΡΙΚΟ CAD κώδικα (CadQuery), ο κώδικας ΕΚΤΕΛΕΙΤΑΙ, βγαίνει STL, και το STL
ελέγχεται ΑΝΤΙΚΕΙΜΕΝΙΚΑ (print_check: watertight, manifold, όγκος, διαστάσεις).
Αν κοπεί κάπου, τα ΑΚΡΙΒΗ σφάλματα γυρίζουν πίσω στο μοντέλο και ξαναδοκιμάζει.

ΓΙΑΤΙ ΕΤΣΙ: ένα LLM γράφει CAD κώδικα που μοιάζει σωστός αλλά βγάζει σπασμένο ή
κενό στερεό. Χωρίς εκτέλεση + έλεγχο mesh, θα έπαιρνες αρχεία που δεν τυπώνονται
ποτέ. Ίδιο μοτίβο με το HTTP smoke test των ιστοσελίδων.

ΤΙ ΔΟΥΛΕΥΕΙ ΚΑΛΑ: λειτουργικά/παραμετρικά αντικείμενα με διαστάσεις — βάσεις,
στηρίγματα, κουτιά, αντάπτορες, θήκες, ανταλλακτικά, οργανωτές.
ΤΙ ΟΧΙ: οργανικά/καλλιτεχνικά (φιγούρες, γλυπτά) — εκεί κατέβασε έτοιμο μοντέλο.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

try:
    from logger import log
except Exception:  # pragma: no cover
    import logging
    log = logging.getLogger("cad_architect")

from openhands_skills.expert_base import ExpertSkill
from openhands_skills.agent_metrics import track as _track
from openhands_skills import safe_paths as sp
from openhands_skills.print_check import check_stl, check_plausible, PrintReport

_PY = sys.executable

# A sibling of the repository by default, for the same reason as the generated
# sites: an absolute C:\AI path is this machine's layout, not everyone's.
MODELS_ROOT = Path(
    os.getenv("MOSKY_MODELS_ROOT")
    or (Path(__file__).resolve().parent.parent.parent / "generated_models")
).resolve()

_SYSTEM = (
    "You are a mechanical designer who writes CadQuery 2.x Python scripts for "
    "3D printing.\n"
    "HARD RULES — the script is executed, so it must run exactly as written:\n"
    "1. `import cadquery as cq` and assign the final solid to a variable named "
    "`result`.\n"
    "2. Do NOT call show_object, do NOT export, do NOT print — the harness "
    "exports the STL itself.\n"
    "3. All units are millimetres.\n"
    "4. Produce ONE closed, watertight solid. Avoid zero-thickness faces and "
    "avoid boolean operations that leave coincident faces.\n"
    "5. Keep every wall at least 1.2 mm thick so a 0.4 mm nozzle can print it.\n"
    "6. Design it to print WITHOUT supports where possible: put the flat face "
    "down, keep overhangs under ~45 degrees, add fillets/chamfers instead of "
    "sharp overhangs.\n"
    "7. Put the dimensions in named variables at the top so the part stays "
    "parametric.\n"
    "\n"
    "METHOD — follow this order, it is what stops the part collapsing into a "
    "flat plate:\n"
    "  a) Start from a SOLID BLOCK big enough to contain the whole part.\n"
    "  b) CUT features out of it (slots, holes, angles) instead of trying to "
    "add thin pieces together.\n"
    "  c) Union only when a feature genuinely sticks out.\n"
    "Building by stacking thin extrusions is what produces disconnected plates. "
    "Cut-from-solid keeps it one body.\n"
    "\n"
    "WORKED EXAMPLE — an angled stand, note the cut-from-solid approach:\n"
    "```python\n"
    "import cadquery as cq\n"
    "import math\n"
    "W, D, H = 90.0, 85.0, 80.0     # overall block\n"
    "ANGLE = 62.0                    # lean from horizontal\n"
    "SLOT_W = 14.0                   # phone thickness + clearance\n"
    "LIP = 9.0\n"
    "# a) solid block\n"
    "result = cq.Workplane('XY').box(W, D, H, centered=(True, True, False))\n"
    "# b) cut the big back wedge away so the front face leans back\n"
    "cut_len = H / math.tan(math.radians(ANGLE)) + D\n"
    "result = result.cut(\n"
    "    cq.Workplane('XZ').workplane(offset=W)\n"
    "      .moveTo(-D / 2, LIP).lineTo(-D / 2 + cut_len, H)\n"
    "      .lineTo(-D / 2, H).close().extrude(2 * W))\n"
    "# c) cut the phone slot INTO the leaning face\n"
    "result = result.cut(\n"
    "    cq.Workplane('XY').workplane(offset=LIP)\n"
    "      .box(SLOT_W, D, H, centered=(True, True, False))\n"
    "      .rotate((0, 0, 0), (1, 0, 0), 90 - ANGLE))\n"
    "```\n"
    "Return ONLY the Python code in a single fenced block."
)

_RUNNER = r'''
import sys, traceback
sys.path.insert(0, r"{workdir}")
try:
    import cadquery as cq
    ns = {{}}
    with open(r"{script}", "r", encoding="utf-8") as f:
        code = f.read()
    exec(compile(code, "model.py", "exec"), ns)
    result = ns.get("result")
    if result is None:
        print("HARNESS_ERROR: the script did not define a variable named `result`")
        sys.exit(2)
    cq.exporters.export(result, r"{stl}")
    print("HARNESS_OK")
except Exception:
    print("HARNESS_ERROR:")
    traceback.print_exc()
    sys.exit(3)
'''


@dataclass
class CadReport:
    prompt: str
    name: str
    out_dir: str = ""
    stl_path: str = ""
    code: str = ""
    attempts: int = 0
    ok: bool = False
    print_report: Optional[PrintReport] = None
    errors: List[str] = field(default_factory=list)
    mismatches: List[str] = field(default_factory=list)
    preview_path: str = ""

    def to_report(self) -> str:
        head = "✅ MODEL READY" if self.ok else "⚠️ MODEL NOT USABLE"
        lines = [f"{head}  ({self.attempts} attempt(s))", f"Request: {self.prompt}"]
        if self.stl_path:
            lines.append(f"STL: {self.stl_path}")
        if self.print_report:
            lines.append("")
            lines.append(self.print_report.to_report())
        for m in self.mismatches:
            lines.append(f"  MISMATCH: {m}")
        for e in self.errors[-2:]:
            lines.append(f"  error: {e[:300]}")
        if self.ok:
            if self.preview_path and not self.preview_path.startswith("("):
                lines.append(f"Preview: {self.preview_path}")
            lines += ["", "Next: open the STL in your slicer, or view it with:",
                      f'  {_PY} -c "import trimesh;trimesh.load(r\'{self.stl_path}\').show()"']
        return "\n".join(lines)


class CadArchitect(ExpertSkill):
    ROLE = "cad_architect"
    EXPERTISE = ("a mechanical designer who writes parametric CadQuery scripts "
                 "for FDM 3D printing")
    DEFAULT_TEMPERATURE = 0.15
    DEFAULT_MAX_TOKENS = 4000

    # ------------------------------------------------------------------ #
    @staticmethod
    def _slug(text: str) -> str:
        s = re.sub(r"[^a-z0-9]+", "-", (text or "part").lower()).strip("-")[:40]
        return s if sp.valid_slug(s) else "part"

    def _out_dir(self, name: str) -> Path:
        MODELS_ROOT.mkdir(parents=True, exist_ok=True)
        base = MODELS_ROOT / name
        if base.exists() and any(base.iterdir()):
            for n in range(2, 100):
                cand = MODELS_ROOT / f"{name}-{n}"
                if not cand.exists() or not any(cand.iterdir()):
                    base = cand
                    break
        base.mkdir(parents=True, exist_ok=True)
        return base

    def _run_cad(self, code: str, out: Path) -> tuple:
        """Execute the CadQuery script and export an STL. Returns (ok, stl, err)."""
        script = out / "model.py"
        stl = out / "model.stl"
        script.write_text(code, encoding="utf-8")
        runner = out / "_run.py"
        runner.write_text(
            _RUNNER.format(workdir=str(out), script=str(script), stl=str(stl)),
            encoding="utf-8")
        try:
            p = subprocess.run([_PY, str(runner)], capture_output=True,
                               text=True, timeout=300)
        except subprocess.TimeoutExpired:
            return False, "", "CAD script timed out after 300s (probably an infinite loop or a runaway boolean)"
        except Exception as e:
            return False, "", f"could not run CAD script: {e}"
        finally:
            try:
                runner.unlink()
            except Exception:
                pass

        outtxt = (p.stdout or "") + (p.stderr or "")
        if "HARNESS_OK" in outtxt and stl.exists():
            return True, str(stl), ""
        return False, "", outtxt.strip()[-1500:]

    # ------------------------------------------------------------------ #
    def design_from_primitive(self, prompt: str, *, name: str = "") -> Optional[CadReport]:
        """Pick a VERIFIED primitive and let the model choose only the numbers.

        Measured reason this exists: asked to write a single wedge cut, the local
        model emitted `.moveTo(-D/2, H).lineTo(-D/2+cut_len, H).lineTo(-D/2, H)`
        — three points at the SAME height, a zero-area triangle that cuts
        nothing. It reproduces the API shape but not the spatial arithmetic.
        Choosing a shape and filling in dimensions is a task it does reliably;
        deriving geometry is not. The geometry lives in cad_primitives, tested.

        Returns None when no primitive fits, so the caller can fall back.
        """
        import json as _json
        from openhands_skills.cad_primitives import PRIMITIVES, describe

        raw = self.consult(
            "Choose the ONE shape that best fits the request and fill in its "
            "numbers. Reply with ONLY a JSON object:\n"
            '{"primitive": "<name>", "params": {"<param>": <number>, ...}, '
            '"why": "<one line>"}\n'
            'If NOTHING fits, reply exactly {"primitive": null}.\n\n'
            f"Available shapes:\n{describe()}\n\nRequest: {prompt}",
            extra_system=("You select parametric CAD shapes. You never write "
                          "geometry code. Use millimetres."),
            max_tokens=700)

        m = re.search(r"\{.*\}", raw or "", re.DOTALL)
        if not m:
            return None
        try:
            choice = _json.loads(m.group(0))
        except Exception:
            return None

        pname = choice.get("primitive")
        if not pname or pname not in PRIMITIVES:
            return None

        fn = PRIMITIVES[pname]
        import inspect
        allowed = set(inspect.signature(fn).parameters)
        params = {k: v for k, v in (choice.get("params") or {}).items()
                  if k in allowed and isinstance(v, (int, float))}

        out = self._out_dir(self._slug(name or prompt))
        rep = CadReport(prompt=prompt, name=out.name, out_dir=str(out), attempts=1)
        try:
            import cadquery as cq
            solid = fn(**params)
            stl = str(out / "model.stl")
            cq.exporters.export(solid, stl)
            (out / "model.py").write_text(
                "# Generated from a verified primitive — geometry is not\n"
                "# model-written, only the parameters are.\n"
                "from openhands_skills.cad_primitives import "
                f"{pname}\n\nresult = {pname}(**{params!r})\n", encoding="utf-8")
        except Exception as e:
            rep.errors.append(f"{type(e).__name__}: {e}")
            return rep

        rep.stl_path = stl
        rep.print_report = check_stl(stl, allow_multibody=False)
        rep.mismatches = check_plausible(prompt, rep.print_report) if rep.print_report.ok else []
        rep.code = f"{pname}({', '.join(f'{k}={v}' for k, v in params.items())})"
        if rep.print_report.ok and not rep.mismatches:
            rep.ok = True
            rep.preview_path = self.render_preview(stl)
        return rep

    def design(self, prompt: str, *, name: str = "", max_iterations: int = 3,
               bed_x: float = None, bed_y: float = None, bed_z: float = None) -> CadReport:
        """Design a printable part from a description, verifying every attempt."""
        # Try the verified-primitive route FIRST. It succeeds on the common
        # shapes precisely because the model never touches the geometry.
        try:
            quick = self.design_from_primitive(prompt, name=name)
            if quick is not None and quick.ok:
                log.info("CadArchitect: satisfied from a verified primitive")
                return quick
        except Exception as e:
            log.warning(f"primitive route failed, falling back to freeform: {e}")

        name = self._slug(name or prompt)
        out = self._out_dir(name)
        rep = CadReport(prompt=prompt, name=name, out_dir=str(out))
        _m = _track("cad_architect", task=prompt[:120])
        _run = _m.__enter__()
        log.info(f"CadArchitect: designing '{prompt[:60]}' -> {out}")

        ask = (f"Design this part as a CadQuery script:\n\n{prompt}\n\n"
               f"It must fit within a {bed_x or 220:.0f} x {bed_y or 220:.0f} x "
               f"{bed_z or 250:.0f} mm print volume.")
        code = ""

        for attempt in range(1, max_iterations + 1):
            rep.attempts = attempt
            raw = self.complete_cad(ask if attempt == 1 else ask)
            code = self.extract_code(raw)
            if not code.strip():
                rep.errors.append("model returned no code")
                continue
            rep.code = code

            ok, stl, err = self._run_cad(code, out)
            if not ok:
                rep.errors.append(err)
                log.warning(f"CadArchitect attempt {attempt}: script failed")
                ask = (f"The CadQuery script below FAILED to execute. Fix it and "
                       f"return the complete corrected script.\n\n"
                       f"### Error\n{err}\n\n### Script\n{code}\n\n"
                       f"Original request: {prompt}")
                continue

            # allow_multibody=False is deliberate. A designed part must come out
            # as ONE connected solid. Measured failure: a phone-stand prompt
            # produced 4 disconnected flat plates floating in space — every plate
            # was individually watertight, so it passed as "printable" while being
            # completely useless. Loose bodies are a hard failure here.
            pr = check_stl(stl, bed_x=bed_x, bed_y=bed_y, bed_z=bed_z,
                           allow_multibody=False)
            rep.stl_path, rep.print_report = stl, pr

            # Printable is NOT the same as correct. A 3 mm flat plate passes every
            # geometric test while completely failing a request for a clip that
            # holds 5 mm cables, so also check the result against the dimensions
            # the user actually asked for.
            mismatches = check_plausible(prompt, pr) if pr.ok else []
            rep.mismatches = mismatches

            if pr.ok and not mismatches:
                rep.ok = True
                rep.preview_path = self.render_preview(stl)
                _run.note(ok=True, attempts=attempt,
                          dims=pr.facts.get("dimensions_mm"))
                _m.__exit__(None, None, None)
                log.info(f"CadArchitect: printable model on attempt {attempt}")
                return rep

            # Ran, but either unprintable or clearly not the requested shape.
            findings = "\n".join(pr.blocking + mismatches)
            rep.errors.append(findings)
            log.warning(f"CadArchitect attempt {attempt}: mesh not printable")
            ask = (f"The CadQuery script ran, but the resulting mesh is NOT "
                   f"printable. Fix the geometry and return the complete "
                   f"corrected script.\n\n### Problems\n{findings}\n\n"
                   f"### Measured\n{pr.to_report()}\n\n### Script\n{code}\n\n"
                   f"Original request: {prompt}")

        _run.note(ok=False, attempts=rep.attempts,
                  reason=(rep.mismatches or rep.errors or ["unknown"])[-1][:150])
        _m.__exit__(None, None, None)
        return rep

    @staticmethod
    def render_preview(stl_path: str, out_png: str = "") -> str:
        """Render 3 orthographic-ish views to a PNG so the shape can be judged.

        Printability checks prove the mesh is valid; only looking at it tells you
        whether it is the thing you asked for. Uses matplotlib (Agg) so it works
        headless, with no GPU and no display.
        """
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from mpl_toolkits.mplot3d.art3d import Poly3DCollection
            import trimesh
        except Exception as e:
            return f"(preview unavailable: {e})"
        try:
            m = trimesh.load(stl_path, force="mesh")
            out_png = out_png or str(Path(stl_path).with_name("preview.png"))
            fig = plt.figure(figsize=(11, 4.2))
            for i, (el, az, title) in enumerate(
                    [(25, 45, "iso"), (0, 0, "front"), (90, 0, "top")], 1):
                ax = fig.add_subplot(1, 3, i, projection="3d")
                ax.add_collection3d(Poly3DCollection(
                    m.vertices[m.faces], facecolor="#4a90d9",
                    edgecolor="#1a3a5a", linewidths=0.15, alpha=0.95))
                b = m.bounds
                c = (b[0] + b[1]) / 2
                r = (b[1] - b[0]).max() / 2 * 1.1
                ax.set_xlim(c[0]-r, c[0]+r); ax.set_ylim(c[1]-r, c[1]+r)
                ax.set_zlim(c[2]-r, c[2]+r)
                ax.view_init(elev=el, azim=az)
                ax.set_box_aspect((1, 1, 1)); ax.set_axis_off()
                ax.set_title(f"{title}  ({m.extents[0]:.0f}x{m.extents[1]:.0f}x"
                             f"{m.extents[2]:.0f} mm)", fontsize=9)
            plt.tight_layout()
            plt.savefig(out_png, dpi=110, bbox_inches="tight", facecolor="white")
            plt.close(fig)
            return out_png
        except Exception as e:
            return f"(preview failed: {e})"

    def complete_cad(self, user_prompt: str) -> str:
        """LLM call with the CAD system prompt."""
        return self.consult(user_prompt, extra_system=_SYSTEM, max_tokens=4000)

    @staticmethod
    def extract_code(text: str) -> str:
        m = re.search(r"```(?:python|py)?\s*\n(.*?)```", text or "", re.DOTALL)
        return (m.group(1) if m else (text or "")).strip()


cad_architect = CadArchitect()
