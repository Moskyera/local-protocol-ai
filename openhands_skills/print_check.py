"""
print_check - ΑΝΤΙΚΕΙΜΕΝΙΚΟΣ έλεγχος αν ένα mesh είναι όντως ΕΚΤΥΠΩΣΙΜΟ.

ΓΙΑΤΙ ΥΠΑΡΧΕΙ: ένα LLM γράφει CAD κώδικα που "φαίνεται" σωστός και παράγει STL
που ανοίγει κανονικά — αλλά ο slicer το απορρίπτει ή η εκτύπωση αποτυγχάνει,
επειδή το mesh δεν είναι watertight, έχει ανεστραμμένα normals, μηδενικό όγκο,
ή δεν χωράει στο bed. Χωρίς αυτόν τον έλεγχο, ο agent θα σου έδινε αρχεία που
μοιάζουν έτοιμα και δεν τυπώνονται ποτέ — το ίδιο λάθος που πιάσαμε στις
ιστοσελίδες με το HTTP smoke test.

Οι έλεγχοι είναι ΝΤΕΤΕΡΜΙΝΙΣΤΙΚΟΙ (trimesh), όχι γνώμη του μοντέλου.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import List, Optional

try:
    from logger import log
except Exception:  # pragma: no cover
    import logging
    log = logging.getLogger("print_check")


# Printer envelope. Defaults are deliberately mid-range so designs stay portable
# until a real printer is chosen. Override per call or via env.
DEFAULT_BED_X = float(os.getenv("PRINTER_BED_X", 220))
DEFAULT_BED_Y = float(os.getenv("PRINTER_BED_Y", 220))
DEFAULT_BED_Z = float(os.getenv("PRINTER_BED_Z", 250))

#: Below this, walls are thinner than a typical 0.4mm nozzle can print reliably.
MIN_WALL_MM = 0.8


@dataclass
class PrintReport:
    ok: bool = False
    blocking: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    facts: dict = field(default_factory=dict)

    def to_report(self) -> str:
        head = "PRINTABLE ✅" if self.ok else "NOT PRINTABLE ❌"
        lines = [head]
        if self.facts:
            f = self.facts
            d = f.get("dimensions_mm")
            if d:
                lines.append(f"  size    : {d[0]:.1f} x {d[1]:.1f} x {d[2]:.1f} mm")
            if f.get("volume_cm3") is not None:
                lines.append(f"  volume  : {f['volume_cm3']:.2f} cm3  (~{f.get('filament_g', 0):.0f} g PLA at 20% infill)")
            lines.append(f"  triangles: {f.get('faces', '?')}  |  solidity: {f.get('solidity')}")
            lines.append(f"  watertight: {f.get('watertight')}  |  bodies: {f.get('bodies')}")
        for b in self.blocking:
            lines.append(f"  BLOCKING: {b}")
        for w in self.warnings:
            lines.append(f"  warning : {w}")
        return "\n".join(lines)


def check_stl(path: str,
              bed_x: float = None, bed_y: float = None, bed_z: float = None,
              allow_multibody: bool = True) -> PrintReport:
    """Validate an STL/3MF/OBJ for printability. Never raises."""
    r = PrintReport()
    bed_x = DEFAULT_BED_X if bed_x is None else bed_x
    bed_y = DEFAULT_BED_Y if bed_y is None else bed_y
    bed_z = DEFAULT_BED_Z if bed_z is None else bed_z

    if not os.path.isfile(path):
        r.blocking.append(f"file not found: {path}")
        return r

    try:
        import trimesh
    except Exception as e:
        r.blocking.append(f"trimesh unavailable: {e}")
        return r

    try:
        mesh = trimesh.load(path, force="mesh")
    except Exception as e:
        r.blocking.append(f"cannot load mesh: {type(e).__name__}: {e}")
        return r

    if mesh is None or getattr(mesh, "is_empty", True) or len(mesh.faces) == 0:
        r.blocking.append("mesh is empty (the CAD script produced no geometry)")
        return r

    ext = mesh.extents  # (x, y, z) bounding box in mm
    try:
        bodies = mesh.body_count
    except Exception:
        bodies = 1

    volume_mm3 = float(abs(mesh.volume)) if mesh.is_volume else 0.0
    r.facts = {
        "dimensions_mm": [float(ext[0]), float(ext[1]), float(ext[2])],
        "volume_cm3": volume_mm3 / 1000.0,
        # PLA ~1.24 g/cm3; 20% infill + walls is roughly 0.3 of solid volume.
        "filament_g": (volume_mm3 / 1000.0) * 1.24 * 0.3,
        "faces": int(len(mesh.faces)),
        "watertight": bool(mesh.is_watertight),
        "bodies": int(bodies),
        # How much of the bounding box is actually material. ~1.0 means the part
        # is still essentially the raw block it started from, i.e. the described
        # shaping (angles, cut-outs, wedges) probably never got applied.
        "solidity": round(volume_mm3 / float(ext[0] * ext[1] * ext[2]), 2)
                    if all(e > 0 for e in ext) else 0.0,
    }

    # ---- blocking: these make a print fail or the slicer refuse ----------
    if not mesh.is_watertight:
        r.blocking.append(
            "mesh is NOT watertight (holes in the surface) — slicers cannot "
            "reliably determine inside vs outside")
    if not mesh.is_winding_consistent:
        r.blocking.append("inconsistent face winding (some normals are flipped)")
    if volume_mm3 <= 0:
        r.blocking.append("zero/negative volume — the solid is degenerate or inside-out")

    if ext[0] > bed_x or ext[1] > bed_y or ext[2] > bed_z:
        r.blocking.append(
            f"does not fit the print bed: needs {ext[0]:.0f}x{ext[1]:.0f}x{ext[2]:.0f} mm, "
            f"bed is {bed_x:.0f}x{bed_y:.0f}x{bed_z:.0f} mm")

    if not allow_multibody and bodies > 1:
        r.blocking.append(f"{bodies} separate bodies — expected a single connected part")

    # ---- warnings: printable, but worth knowing -------------------------
    if min(ext) < MIN_WALL_MM:
        r.warnings.append(
            f"smallest dimension is {min(ext):.2f} mm — thinner than a 0.4 mm "
            f"nozzle prints reliably (min ~{MIN_WALL_MM} mm)")
    if bodies > 1:
        r.warnings.append(f"{bodies} separate bodies — they will print as loose pieces")
    if len(mesh.faces) > 1_000_000:
        r.warnings.append(f"{len(mesh.faces)} triangles — very heavy file, slicing will be slow")
    if r.facts.get("solidity", 0) > 0.9:
        r.warnings.append(
            "solidity > 0.9 — the part is still almost the full bounding block, "
            "so the described cut-outs/angles may not have been applied")
    if volume_mm3 > 0 and (volume_mm3 / 1000.0) > 300:
        r.warnings.append(f"large part (~{volume_mm3/1000:.0f} cm3) — long print, check filament")

    r.ok = not r.blocking
    return r


def check_plausible(prompt: str, report: PrintReport) -> List[str]:
    """Catch models that are PRINTABLE but obviously NOT what was asked for.

    Watertight+fits-the-bed says nothing about correctness: a 3 mm flat plate
    passes every geometric test while completely failing a request for a clip
    that holds 5 mm cables. This compares the millimetre figures the user
    actually wrote against the part that came out.

    Returns a list of human-readable mismatches (empty = nothing suspicious).
    """
    problems: List[str] = []
    dims = (report.facts or {}).get("dimensions_mm")
    if not dims:
        return problems

    # Every "<number> mm" the request mentions — BUT not the ones describing the
    # thing being HELD. "holds a phone 165mm tall" is the phone's size, not a
    # dimension the stand must have. Treating it as a required feature produced a
    # false BLOCKING result on an otherwise correct 90x85x80 mm stand.
    text = prompt or ""
    held = re.compile(
        r"(?:holds?|hold|fits?|fit|for|carries|takes|accepts|houses)\b[^.;]{0,80}?"
        r"(\d+(?:\.\d+)?)\s*mm", re.I)
    held_values = {float(m.group(1)) for m in held.finditer(text)}

    wanted = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*mm", text, re.I)
              if float(x) not in held_values]
    if not wanted:
        return problems

    biggest_feature = max(wanted)
    smallest_dim = min(dims)
    largest_dim = max(dims)

    # A part cannot contain a feature bigger than the part itself.
    if biggest_feature > largest_dim + 0.5:
        problems.append(
            f"the request mentions a {biggest_feature:.0f} mm feature, but the whole "
            f"part is only {largest_dim:.0f} mm at its largest — the feature cannot exist")

    # A hole/slot of diameter D needs the part to be thicker than D in some axis.
    holes = [w for w in wanted if w <= 20]
    if holes and smallest_dim + 0.5 < max(holes):
        problems.append(
            f"the request needs a {max(holes):.0f} mm slot/hole, but the part is only "
            f"{smallest_dim:.1f} mm thick in its thinnest axis — it cannot hold that")

    vol = (report.facts or {}).get("volume_cm3", 0)
    if vol and vol < 0.5 and biggest_feature >= 20:
        problems.append(
            f"only {vol:.2f} cm3 of material for a part described with {biggest_feature:.0f} mm "
            f"features — this looks like a flat plate rather than the described shape")

    return problems


__all__ = ["check_stl", "check_plausible", "PrintReport", "MIN_WALL_MM"]
