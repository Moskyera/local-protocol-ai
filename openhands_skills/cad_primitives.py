"""
cad_primitives - ΕΠΑΛΗΘΕΥΜΕΝΑ παραμετρικά σχήματα.

ΓΙΑΤΙ ΥΠΑΡΧΕΙ (μετρημένο, όχι υπόθεση):
Το τοπικό 30B δεν αποτυγχάνει επειδή το task είναι "μεγάλο". Απέτυχε ακόμα και
σε ΜΙΑ μεμονωμένη πράξη πάνω σε έτοιμο block. Ο λόγος φαίνεται στον κώδικα που
παρήγαγε για μια κεκλιμένη κοπή:

    .moveTo(-D/2, H).lineTo(-D/2 + cut_len, H).lineTo(-D/2, H).close()

Και τα τρία σημεία στο ΙΔΙΟ ύψος H — τρίγωνο μηδενικού εμβαδού, οπότε η κοπή
δεν αφαιρεί τίποτα (solidity έμεινε 1.0). Το μοντέλο αντιγράφει σωστά τη ΔΟΜΗ
του API αλλά δεν κάνει τη ΧΩΡΙΚΗ ΑΡΙΘΜΗΤΙΚΗ.

Η λύση δεν είναι καλύτερο prompt. Είναι να μη ζητάμε από το μοντέλο γεωμετρία:
εδώ η γεωμετρία είναι γραμμένη και δοκιμασμένη σε Python, και το μοντέλο απλώς
ΔΙΑΛΕΓΕΙ σχήμα και ΠΑΡΑΜΕΤΡΟΥΣ — δουλειά που ένα 30B κάνει αξιόπιστα.

Κάθε primitive επιστρέφει ΕΝΑ κλειστό στερεό και ελέγχεται στα tests.
"""

from __future__ import annotations

import math
from typing import Optional


def _cq():
    import cadquery as cq
    return cq


# --------------------------------------------------------------------------- #
def angled_stand(width: float = 90.0, depth: float = 85.0, height: float = 80.0,
                 angle_deg: float = 62.0, slot_width: float = 14.0,
                 lip_height: float = 10.0, cable_width: float = 20.0,
                 cable_height: float = 16.0):
    """A leaning stand (phone / tablet / sign holder).

    The wedge and the slot are built from an explicit side profile in the YZ
    plane, so the points genuinely differ in Z — this is exactly what the model
    could not get right on its own.
    """
    cq = _cq()
    # SANITY BOUNDS. Measured failure: asked for a stand for a 165 mm phone, the
    # model passed depth=165, height=165 — the PHONE's dimensions, not the
    # stand's — producing a 1038 cm3, 386 g part. A stand only cradles the lower
    # third of a device, so clamp to what is physically sensible. The model is
    # allowed to choose within these limits, not outside them.
    width = max(40.0, min(width, 110.0))
    depth = max(50.0, min(depth, 95.0))
    height = max(40.0, min(height, 90.0))
    slot_width = max(6.0, min(slot_width, 30.0))
    lip_height = max(5.0, min(lip_height, 25.0))

    a = math.radians(max(35.0, min(80.0, angle_deg)))
    lip_t = max(3.0, slot_width * 0.35)

    # Side profile, counter-clockwise in (y, z). Front of the stand is y=0.
    back_z = height
    ramp_run = height / math.tan(a)                 # horizontal travel of the lean
    ramp_run = min(ramp_run, depth * 0.9)
    front_h = max(lip_height + 4.0, height * 0.28)  # vertical front face

    slot_y = depth * 0.45                           # where the slot floor sits
    slot_z = front_h
    ny, nz = -math.sin(a), math.cos(a)              # slot normal (forward/up)
    sy, sz = math.cos(a), math.sin(a)               # up the slope

    p_floor_back = (slot_y, slot_z)
    p_floor_front = (slot_y + slot_width * ny, slot_z + slot_width * nz)
    crest = (slot_y + ramp_run * sy, min(back_z, slot_z + ramp_run * sz))
    lip_in = (p_floor_front[0] + lip_height * sy, p_floor_front[1] + lip_height * sz)
    lip_out = (lip_in[0] + lip_t * ny, lip_in[1] + lip_t * nz)

    profile = [
        (0.0, 0.0), (depth, 0.0), (depth, crest[1]), crest,
        p_floor_back, p_floor_front, lip_in, lip_out, (0.0, front_h),
    ]

    body = (cq.Workplane("YZ").polyline(profile).close()
              .extrude(width).translate((-width / 2.0, 0.0, 0.0)))

    # Cable pass-through: an open-top notch, so it needs no support.
    cw = min(cable_width, width * 0.6)
    ch = min(cable_height, front_h + slot_width)
    notch = (cq.Workplane("XY")
               .box(cw, depth, ch, centered=(True, False, False))
               .translate((0, -1, 0)))
    body = body.cut(notch)

    # HOLLOW THE UNDERSIDE. A solid wedge of this size is ~300-400 g of filament
    # and hours of printing; real stands are shells. The cavity is open at the
    # bottom (it sits on the desk) so it prints with no support, and the walls
    # stay thick enough to be rigid.
    wall = 4.0
    cavity_h = max(0.0, min(front_h - wall, height * 0.55))
    if cavity_h > 3.0 and width > 2 * wall + 8 and depth > 2 * wall + 8:
        cavity = (cq.Workplane("XY")
                    .box(width - 2 * wall, depth - 2 * wall, cavity_h,
                         centered=(True, False, False))
                    .translate((0, wall, -0.5)))
        body = body.cut(cavity)
    return body


# --------------------------------------------------------------------------- #
def open_box(width: float = 80.0, depth: float = 60.0, height: float = 40.0,
             wall: float = 3.0, floor: Optional[float] = None):
    """A rectangular tray / open-top box with a solid floor."""
    cq = _cq()
    wall = max(1.2, min(wall, min(width, depth) / 3.0))
    floor = wall if floor is None else max(1.2, floor)
    outer = cq.Workplane("XY").box(width, depth, height, centered=(True, True, False))
    cavity = (cq.Workplane("XY")
                .box(width - 2 * wall, depth - 2 * wall, height,
                     centered=(True, True, False))
                .translate((0, 0, floor)))
    return outer.cut(cavity)


# --------------------------------------------------------------------------- #
def l_bracket(arm_a: float = 60.0, arm_b: float = 60.0, width: float = 40.0,
              thickness: float = 5.0, hole_d: float = 4.5,
              holes_per_arm: int = 2):
    """A right-angle mounting bracket with countersink-free through holes."""
    cq = _cq()
    thickness = max(2.0, thickness)
    base = (cq.Workplane("XY").box(arm_a, width, thickness, centered=(False, True, False)))
    upright = (cq.Workplane("XY").box(thickness, width, arm_b, centered=(False, True, False)))
    part = base.union(upright)

    if hole_d > 0 and holes_per_arm > 0:
        for i in range(holes_per_arm):
            frac = (i + 1) / (holes_per_arm + 1)
            x = thickness + (arm_a - thickness) * frac
            part = part.cut(cq.Workplane("XY").circle(hole_d / 2)
                              .extrude(thickness * 3).translate((x, 0, -thickness)))
            z = thickness + (arm_b - thickness) * frac
            part = part.cut(cq.Workplane("YZ").circle(hole_d / 2)
                              .extrude(thickness * 3).translate((-thickness, 0, z)))
    return part


# --------------------------------------------------------------------------- #
def cable_clip(cable_d: float = 5.0, count: int = 3, width: float = 30.0,
               base_thickness: float = 4.0, screw_d: float = 4.0):
    """A base plate with semicircular cable channels and a screw hole."""
    cq = _cq()
    pitch = cable_d * 1.8
    span = pitch * count
    depth = max(cable_d * 2.2, 14.0)
    height = base_thickness + cable_d * 1.1

    body = cq.Workplane("XY").box(max(width, span + 8), depth, height,
                                  centered=(True, True, False))
    for i in range(count):
        x = -span / 2 + pitch * (i + 0.5)
        body = body.cut(cq.Workplane("XZ").circle(cable_d / 2)
                          .extrude(depth * 2)
                          .translate((x, depth, base_thickness + cable_d / 2)))
    if screw_d > 0:
        body = body.cut(cq.Workplane("XY").circle(screw_d / 2)
                          .extrude(height * 2).translate((0, 0, -1)))
    return body


PRIMITIVES = {
    "angled_stand": angled_stand,   # phone/tablet/sign stand, leaning
    "open_box": open_box,           # tray, organiser, container
    "l_bracket": l_bracket,         # shelf/mount bracket
    "cable_clip": cable_clip,       # cable management
}


def describe() -> str:
    """Catalogue for the model to choose from."""
    import inspect
    out = []
    for name, fn in PRIMITIVES.items():
        sig = inspect.signature(fn)
        params = ", ".join(
            f"{p}={v.default}" for p, v in sig.parameters.items()
            if v.default is not inspect.Parameter.empty)
        doc = (fn.__doc__ or "").strip().splitlines()[0]
        out.append(f"- {name}({params})\n    {doc}")
    return "\n".join(out)


__all__ = ["PRIMITIVES", "describe", "angled_stand", "open_box",
           "l_bracket", "cable_clip"]
