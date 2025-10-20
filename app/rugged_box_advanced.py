#!/usr/bin/env python3
"""
Advanced Rugged Box Generator (Updated)
--------------------------------------
Builds a print‑ready rugged enclosure with:
- Real tongue‑and‑groove seal (bottom tongue + lid gasket channel)
- Proper wall shelling (open at top), configurable floor thickness
- Interleaved hinge knuckles (pin-ready) that align between bottom & lid
- Front latch pads + pilot holes (optional separate latch part)
- Internal standoffs (bosses) + optional ribs

CLI Examples:
  python3 rugged_box_advanced.py make_bottom --length 200 --width 150 --height 80 -o bottom.stl
  python3 rugged_box_advanced.py make_lid    --length 200 --width 150 -o lid.stl
  python3 rugged_box_advanced.py make_hinge  -o hinge.stl
  python3 rugged_box_advanced.py make_latch  -o latch.stl

CadQuery 2.x compatible.
"""

import cadquery as cq
import argparse
import sys
import tempfile
import os
from math import floor

CADQUERY_AVAILABLE = True

# ----------------------------
# Utility helpers
# ----------------------------

def rounded_rect(w: float, h: float, r: float) -> cq.Workplane:
    r = max(0.0, min(r, min(w, h) / 2.0 - 0.01))
    if r <= 0:
        return cq.Workplane("XY").rect(w, h)
    return (
        cq.Workplane("XY")
        .rect(w - 2 * r, h)
        .rect(w, h - 2 * r)
        .vertices()
        .fillet(r)
    )


def export_stl_bytes(solid, tol=0.02, ang=0.2) -> bytes:
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        cq.exporters.export(solid, tmp_path, exportType="STL", tolerance=tol, angularTolerance=ang)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ----------------------------
# Core geometry
# ----------------------------

def make_bottom(
    length=200.0,
    width=150.0,
    height=80.0,
    wall_thickness=3.6,
    floor_thickness=6.0,
    corner_radius=8.0,
    tongue_height=3.2,
    tongue_width=2.4,
    hinge_knuckle_d=8.0,
    hinge_knuckle_len=14.0,
    hinge_count=3,
    pin_diameter=3.0,
    latch_pad_w=18.0,
    latch_pad_d=8.0,
    boss_d=6.0,
    boss_h=10.0,
    add_ribs=True,
) -> cq.Workplane:
    """Create the bottom tub with tongue, hinge pads, bosses, and optional ribs."""
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")

    # Outer shell (open at top)
    outer = rounded_rect(length, width, corner_radius).extrude(height)
    tub = outer.faces(">Z").shell(-wall_thickness)  # open top shell

    # Ensure desired floor thickness (shell gives floor == wall_thickness)
    extra_floor = max(0.0, floor_thickness - wall_thickness)
    if extra_floor > 0:
        inner_w = width - 2 * wall_thickness
        inner_l = length - 2 * wall_thickness
        floor_pad = rounded_rect(inner_l, inner_w, max(0, corner_radius - wall_thickness)).extrude(extra_floor)
        tub = tub.union(floor_pad)

    # Add top tongue (continuous lip that mates with lid groove)
    inner_l = length - 2 * wall_thickness
    inner_w = width - 2 * wall_thickness
    tongue_r = max(0, corner_radius - wall_thickness - 0.6)
    tongue = (
        rounded_rect(inner_l - 1.0, inner_w - 1.0, tongue_r)
        .workplane(offset=height - tongue_height)
        .tag("topwp")
        .extrude(tongue_height)
    )
    # Narrow tongue by subtracting an inner offset to create width
    tongue_inner = (
        rounded_rect(inner_l - 1.0 - 2 * tongue_width, inner_w - 1.0 - 2 * tongue_width, max(0, tongue_r - tongue_width))
        .workplane(offset=height - tongue_height)
        .extrude(tongue_height + 0.1)
    )
    tub = tub.union(tongue).cut(tongue_inner)

    # Hinge knuckles (bottom gets outer knuckles when hinge_count is odd: e.g., 3)
    # Back side is +Y
    back_y = width / 2.0
    spacing = (length - 2 * 12.0) / (hinge_count)  # simple spacing with margins
    kn_half = hinge_knuckle_len / 2.0
    start_x = -length / 2.0 + 12.0 + kn_half

    bottom_knuckles = cq.Workplane("XY")
    for i in range(hinge_count):
        # Bottom gets even indices (0,2,4,...) as knuckles; lid will get odd indices
        if i % 2 == 0:
            x = start_x + i * spacing
            k = (
                cq.Workplane("XY")
                .center(x, back_y + wall_thickness / 2.0)
                .cylinder(hinge_knuckle_len, hinge_knuckle_d / 2.0, centered=(True, True, False))
                .translate((0, 0, height - hinge_knuckle_len))
            )
            # Bore the pin hole through knuckle
            k = k.cut(
                cq.Workplane("XY")
                .center(x, back_y + wall_thickness / 2.0)
                .circle(pin_diameter / 2.0)
                .extrude(hinge_knuckle_len + 2.0)
                .translate((0, 0, height - hinge_knuckle_len))
            )
            bottom_knuckles = bottom_knuckles.union(k)

    tub = tub.union(bottom_knuckles)

    # Latch pad at front (+Y opposite side? we used back=+Y, so front=-Y)
    front_y = -width / 2.0
    latch_pad = (
        cq.Workplane("XY")
        .center(0, front_y - wall_thickness / 2.0)
        .box(latch_pad_w, latch_pad_d, 10.0, centered=(True, True, False))
        .translate((0, 0, height - 10.0))
    )
    # Mounting pilot holes M3
    for xo in (-latch_pad_w * 0.3, latch_pad_w * 0.3):
        latch_pad = latch_pad.cut(
            cq.Workplane("XY")
            .center(xo, front_y - wall_thickness / 2.0)
            .circle(1.5)  # ~3mm pilot
            .extrude(latch_pad_d + 2.0)
            .translate((0, 0, height - 9.0))
        )
    tub = tub.union(latch_pad)

    # Internal bosses near corners
    boss_offset_x = (length / 2.0) - (wall_thickness + 12.0)
    boss_offset_y = (width / 2.0) - (wall_thickness + 12.0)

    def boss_at(x, y):
        b = (
            cq.Workplane("XY")
            .center(x, y)
            .circle(boss_d / 2.0)
            .extrude(boss_h)
        )
        # pilot for self‑tapping or M3
        b = b.cut(
            cq.Workplane("XY").center(x, y).circle(1.4).extrude(boss_h)
        )
        return b

    bosses = (
        boss_at( boss_offset_x,  boss_offset_y)
        .union(boss_at(-boss_offset_x,  boss_offset_y))
        .union(boss_at( boss_offset_x, -boss_offset_y))
        .union(boss_at(-boss_offset_x, -boss_offset_y))
    )

    tub = tub.union(bosses.translate((0, 0, floor_thickness)))

    # Optional simple cross ribs
    if add_ribs:
        inner_l = length - 2 * wall_thickness
        inner_w = width - 2 * wall_thickness
        rib_t = 2.4
        rib_h = max(8.0, (height - floor_thickness) * 0.5)
        rib_r = max(0, corner_radius - wall_thickness - 1.0)
        rib_x = (
            rounded_rect(inner_l - 4.0, rib_t, 0)
            .extrude(rib_h)
            .translate((0, 0, floor_thickness + 1.0))
        )
        rib_y = (
            rounded_rect(rib_t, inner_w - 4.0, 0)
            .extrude(rib_h)
            .translate((0, 0, floor_thickness + 1.0))
        )
        tub = tub.union(rib_x).union(rib_y)

    return tub


def make_lid(
    length=200.0,
    width=150.0,
    lid_height=18.0,
    wall_thickness=3.6,
    corner_radius=8.0,
    groove_depth=3.6,
    groove_width=3.0,
    gasket_clearance=0.5,
    hinge_knuckle_d=8.0,
    hinge_knuckle_len=14.0,
    hinge_count=3,
    pin_diameter=3.0,
    top_plate=3.0,
) -> cq.Workplane:
    """Create the lid with a matching gasket groove and interleaved hinge knuckles."""
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")

    # Build a cap (open at bottom) + top plate
    outer = rounded_rect(length, width, corner_radius).extrude(lid_height)
    lid = outer.faces("<Z").shell(-wall_thickness)  # open bottom shell

    # Add solid top plate inside (strength)
    inner_l = length - 2 * wall_thickness
    inner_w = width - 2 * wall_thickness
    top = rounded_rect(inner_l - 1.0, inner_w - 1.0, max(0, corner_radius - wall_thickness - 0.6)).extrude(top_plate)
    lid = lid.union(top.translate((0, 0, lid_height - top_plate)))

    # Gasket groove on the bottom inner lip (mates with bottom tongue)
    # Groove should be slightly larger than bottom tongue (gasket_clearance)
    groove_l = inner_l - 1.0
    groove_w = inner_w - 1.0
    groove_r = max(0, corner_radius - wall_thickness - 0.6)

    groove_outer = rounded_rect(groove_l, groove_w, groove_r)
    groove_inner = rounded_rect(
        groove_l - 2 * (groove_width + gasket_clearance),
        groove_w - 2 * (groove_width + gasket_clearance),
        max(0, groove_r - (groove_width + gasket_clearance)),
    )

    groove = (
        groove_outer.transformed(offset=(0, 0, groove_depth)).cut(groove_inner.transformed(offset=(0, 0, groove_depth)))
    )
    lid = lid.cut(groove)

    # Hinge knuckles for the lid: place the odd indices (1,3,...) so they interleave
    back_y = width / 2.0
    spacing = (length - 2 * 12.0) / (hinge_count)
    kn_half = hinge_knuckle_len / 2.0
    start_x = -length / 2.0 + 12.0 + kn_half

    lid_knuckles = cq.Workplane("XY")
    for i in range(hinge_count):
        if i % 2 == 1:
            x = start_x + i * spacing
            k = (
                cq.Workplane("XY")
                .center(x, back_y + wall_thickness / 2.0)
                .cylinder(hinge_knuckle_len, hinge_knuckle_d / 2.0, centered=(True, True, False))
                .translate((0, 0, lid_height - hinge_knuckle_len))
            )
            k = k.cut(
                cq.Workplane("XY")
                .center(x, back_y + wall_thickness / 2.0)
                .circle(pin_diameter / 2.0)
                .extrude(hinge_knuckle_len + 2.0)
                .translate((0, 0, lid_height - hinge_knuckle_len))
            )
            lid_knuckles = lid_knuckles.union(k)

    lid = lid.union(lid_knuckles)

    # Front stiffening rib under the latch region (opposite side = -Y)
    front_y = -width / 2.0
    stiff = (
        cq.Workplane("XY")
        .center(0, front_y - wall_thickness / 2.0)
        .box(40.0, 8.0, 8.0, centered=(True, True, False))
        .translate((0, 0, lid_height - 8.0))
    )
    lid = lid.union(stiff)

    return lid


def make_hinge(length=30.0, width=15.0, thickness=3.0, pin_diameter=3.0) -> cq.Workplane:
    """Simple printable hinge leaf with a through pin bore."""
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")

    body = cq.Workplane("XY").box(length, width, thickness, centered=(True, True, False))
    kn_d = min(width - 2.0, 8.0)
    kn_h = max(6.0, thickness + 2.0)
    gap = 4.0
    n = max(2, floor((length - gap) / (kn_d + gap)))
    leaf = body
    start_x = -length / 2.0 + gap + kn_d / 2.0
    for i in range(n):
        x = start_x + i * (kn_d + gap)
        k = cq.Workplane("XY").center(x, 0).cylinder(kn_h, kn_d / 2.0, centered=(True, True, False))
        leaf = leaf.union(k)
    leaf = leaf.cut(cq.Workplane("XY").circle(pin_diameter / 2.0).extrude(kn_h + 2.0))
    return leaf


def make_latch(length=40.0, width=20.0, thickness=4.0, catch_depth=8.0) -> cq.Workplane:
    """Basic latch body with a protruding catch and two M3 pilot holes."""
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")

    latch = cq.Workplane("XY").box(length, width, thickness, centered=(True, True, False))
    catch = cq.Workplane("XY").center(length / 2.0, 0).box(catch_depth, width - 4.0, thickness + 3.0, centered=(True, True, False))
    latch = latch.union(catch)
    for xo in (-12.0, 12.0):
        latch = latch.cut(cq.Workplane("XY").center(xo, 0).circle(1.5).extrude(thickness + 2.0))
    return latch


# ----------------------------
# CLI
# ----------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Advanced Rugged Box Generator — tongue & groove, interleaved hinges, and more",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 rugged_box_advanced.py make_bottom --length 200 --width 150 --height 80 -o bottom.stl\n"
            "  python3 rugged_box_advanced.py make_lid    --length 200 --width 150 -o lid.stl\n"
            "  python3 rugged_box_advanced.py make_hinge  -o hinge.stl\n"
            "  python3 rugged_box_advanced.py make_latch  -o latch.stl\n"
        ),
    )

    sub = parser.add_subparsers(dest="function", help="Available functions")

    p_btm = sub.add_parser("make_bottom", help="Create the bottom tub")
    p_btm.add_argument("--length", type=float, default=200.0)
    p_btm.add_argument("--width", type=float, default=150.0)
    p_btm.add_argument("--height", type=float, default=80.0)
    p_btm.add_argument("--wall_thickness", type=float, default=3.6)
    p_btm.add_argument("--floor_thickness", type=float, default=6.0)
    p_btm.add_argument("--corner_radius", type=float, default=8.0)
    p_btm.add_argument("--tongue_height", type=float, default=3.2)
    p_btm.add_argument("--tongue_width", type=float, default=2.4)
    p_btm.add_argument("--hinge_knuckle_d", type=float, default=8.0)
    p_btm.add_argument("--hinge_knuckle_len", type=float, default=14.0)
    p_btm.add_argument("--hinge_count", type=int, default=3)
    p_btm.add_argument("--pin_diameter", type=float, default=3.0)
    p_btm.add_argument("--latch_pad_w", type=float, default=18.0)
    p_btm.add_argument("--latch_pad_d", type=float, default=8.0)
    p_btm.add_argument("--boss_d", type=float, default=6.0)
    p_btm.add_argument("--boss_h", type=float, default=10.0)
    p_btm.add_argument("--no_ribs", action="store_true", help="Disable internal ribs")
    p_btm.add_argument("--output", "-o", default="rugged_box_bottom.stl")

    p_lid = sub.add_parser("make_lid", help="Create the lid")
    p_lid.add_argument("--length", type=float, default=200.0)
    p_lid.add_argument("--width", type=float, default=150.0)
    p_lid.add_argument("--lid_height", type=float, default=18.0)
    p_lid.add_argument("--wall_thickness", type=float, default=3.6)
    p_lid.add_argument("--corner_radius", type=float, default=8.0)
    p_lid.add_argument("--groove_depth", type=float, default=3.6)
    p_lid.add_argument("--groove_width", type=float, default=3.0)
    p_lid.add_argument("--gasket_clearance", type=float, default=0.5)
    p_lid.add_argument("--hinge_knuckle_d", type=float, default=8.0)
    p_lid.add_argument("--hinge_knuckle_len", type=float, default=14.0)
    p_lid.add_argument("--hinge_count", type=int, default=3)
    p_lid.add_argument("--pin_diameter", type=float, default=3.0)
    p_lid.add_argument("--top_plate", type=float, default=3.0)
    p_lid.add_argument("--output", "-o", default="rugged_box_lid.stl")

    p_hg = sub.add_parser("make_hinge", help="Create a standalone hinge leaf")
    p_hg.add_argument("--length", type=float, default=30.0)
    p_hg.add_argument("--width", type=float, default=15.0)
    p_hg.add_argument("--thickness", type=float, default=3.0)
    p_hg.add_argument("--pin_diameter", type=float, default=3.0)
    p_hg.add_argument("--output", "-o", default="hinge.stl")

    p_lt = sub.add_parser("make_latch", help="Create a simple latch")
    p_lt.add_argument("--length", type=float, default=40.0)
    p_lt.add_argument("--width", type=float, default=20.0)
    p_lt.add_argument("--thickness", type=float, default=4.0)
    p_lt.add_argument("--catch_depth", type=float, default=8.0)
    p_lt.add_argument("--output", "-o", default="latch.stl")

    args = parser.parse_args()

    if not args.function:
        parser.print_help()
        return

    try:
        if args.function == "make_bottom":
            print(f"🔧 Bottom: {args.length}x{args.width}x{args.height} (t={args.wall_thickness}, floor={args.floor_thickness})")
            solid = make_bottom(
                length=args.length,
                width=args.width,
                height=args.height,
                wall_thickness=args.wall_thickness,
                floor_thickness=args.floor_thickness,
                corner_radius=args.corner_radius,
                tongue_height=args.tongue_height,
                tongue_width=args.tongue_width,
                hinge_knuckle_d=args.hinge_knuckle_d,
                hinge_knuckle_len=args.hinge_knuckle_len,
                hinge_count=args.hinge_count,
                pin_diameter=args.pin_diameter,
                latch_pad_w=args.latch_pad_w,
                latch_pad_d=args.latch_pad_d,
                boss_d=args.boss_d,
                boss_h=args.boss_h,
                add_ribs=(not args.no_ribs),
            )
            data = export_stl_bytes(solid, tol=0.01, ang=0.05)
            with open(args.output, "wb") as f:
                f.write(data)
            print(f"✅ Wrote {args.output} ({len(data)} bytes)")

        elif args.function == "make_lid":
            print(f"🔧 Lid: {args.length}x{args.width} (h={args.lid_height}, t={args.wall_thickness})")
            solid = make_lid(
                length=args.length,
                width=args.width,
                lid_height=args.lid_height,
                wall_thickness=args.wall_thickness,
                corner_radius=args.corner_radius,
                groove_depth=args.groove_depth,
                groove_width=args.groove_width,
                gasket_clearance=args.gasket_clearance,
                hinge_knuckle_d=args.hinge_knuckle_d,
                hinge_knuckle_len=args.hinge_knuckle_len,
                hinge_count=args.hinge_count,
                pin_diameter=args.pin_diameter,
                top_plate=args.top_plate,
            )
            data = export_stl_bytes(solid, tol=0.01, ang=0.05)
            with open(args.output, "wb") as f:
                f.write(data)
            print(f"✅ Wrote {args.output} ({len(data)} bytes)")

        elif args.function == "make_hinge":
            print(f"🔧 Hinge leaf: {args.length}x{args.width}x{args.thickness} (pin {args.pin_diameter})")
            solid = make_hinge(length=args.length, width=args.width, thickness=args.thickness, pin_diameter=args.pin_diameter)
            data = export_stl_bytes(solid, tol=0.01, ang=0.05)
            with open(args.output, "wb") as f:
                f.write(data)
            print(f"✅ Wrote {args.output} ({len(data)} bytes)")

        elif args.function == "make_latch":
            print(f"🔧 Latch: {args.length}x{args.width}x{args.thickness} (catch {args.catch_depth})")
            solid = make_latch(length=args.length, width=args.width, thickness=args.thickness, catch_depth=args.catch_depth)
            data = export_stl_bytes(solid, tol=0.01, ang=0.05)
            with open(args.output, "wb") as f:
                f.write(data)
            print(f"✅ Wrote {args.output} ({len(data)} bytes)")

        else:
            print(f"❌ Unknown function: {args.function}")
            sys.exit(2)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
