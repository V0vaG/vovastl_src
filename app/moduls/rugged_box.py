#!/usr/bin/env python3
"""
Rugged Box Generator Module
Creates rugged box models with advanced sealing features
"""

import cadquery as cq
import math
import argparse
from pathlib import Path

def mm(val): return float(val)

def make_bottom_box(
    inner_len, inner_wid, inner_h,
    wall=3.0, floor=3.0,
    corner_fillet=4.0,
    rim_height=6.0,              # גובה השפה העליונה (בולטת פנימה)
    tongue_height=2.2,           # גובה הלשון לאטימה
    tongue_clearance=0.2,        # מרווח התאמה בין לשון לשקע
    boss_outer_d=8.0,            # קוטר חיצוני של בוס בתחתית
    boss_h=10.0,                 # גובה בוס (נבנה פנימה מהרצפה)
    boss_core_d=2.4,             # קוטר חור פיילוט (ל-M3 הברגת פלסטיק / אינסרט אחרי קידוח)
    ribs=False,                  # צלעות קשיחה פנימיות (אופציונלי)
    rib_thickness=2.0,
    rib_pitch=20.0,
):
    # מידות חיצוניות
    outer_len = inner_len + 2 * wall
    outer_wid = inner_wid + 2 * wall
    outer_h   = floor + inner_h + rim_height

    # גוף חיצוני
    body = (
        cq.Workplane("XY")
        .box(outer_len, outer_wid, outer_h, centered=(True, True, False))
    )
    if corner_fillet > 0:
        body = body.edges("|Z").fillet(corner_fillet)

    # חלילה פנימה – שומרים רצפה + דפנות + שפה עליונה
    cavity_h = inner_h + rim_height
    inner = (
        cq.Workplane("XY")
        .box(inner_len, inner_wid, cavity_h, centered=(True, True, False))
        .translate((0, 0, floor))
    )
    body = body.cut(inner)

    # לשון אטימה (tongue) – בולטת מהשפה פנימה
    tongue_len = inner_len - 2 * tongue_clearance
    tongue_wid = inner_wid - 2 * tongue_clearance
    tongue = (
        cq.Workplane("XY")
        .box(tongue_len, tongue_wid, tongue_height, centered=(True, True, False))
        .translate((0, 0, floor + inner_h))
    )
    # ריכוך פינות קל בלשון
    tongue = tongue.edges("|Z").fillet(min(0.6, max(0.0, corner_fillet / 4)))
    body = body.union(tongue)

    # בוסים (Bosses) – 4 פינות פנימיות
    boss_offset_x = inner_len/2 - 8
    boss_offset_y = inner_wid/2 - 8
    boss_centers = [
        (+boss_offset_x, +boss_offset_y),
        (+boss_offset_x, -boss_offset_y),
        (-boss_offset_x, +boss_offset_y),
        (-boss_offset_x, -boss_offset_y),
    ]

    bosses = cq.Workplane("XY")
    for (x, y) in boss_centers:
        bosses = bosses.union(
            cq.Workplane("XY")
            .workplane(offset=floor)
            .center(x, y)
            .cylinder(boss_h, boss_outer_d / 2.0)
        )
    body = body.union(bosses)

    # חורי פיילוט בבוסים – לקדוח מתוך ה-body (יש parent solid, אין שגיאה)
    body = (
        body
        .faces(">Z").workplane(centerOption="CenterOfBoundBox")
        .pushPoints(boss_centers)
        .hole(boss_core_d, depth=boss_h + 2)   # קצת יותר עמוק מגובה הבוס
    )

    # צלעות קשיחה אופציונליות על הרצפה
    if ribs:
        # לאורך X
        y = -inner_wid/2 + rib_pitch
        while y < inner_wid/2 - rib_pitch/2:
            rib = (
                cq.Workplane("XY")
                .workplane(offset=floor + 0.01)
                .center(0, y)
                .rect(inner_len - 16, rib_thickness)  # מרווח 8 מ״מ מכל צד מהבוסים
                .extrude(min(8.0, inner_h/3))
            )
            body = body.union(rib)
            y += rib_pitch

        # לאורך Y
        x = -inner_len/2 + rib_pitch
        while x < inner_len/2 - rib_pitch/2:
            rib = (
                cq.Workplane("XY")
                .workplane(offset=floor + 0.01)
                .center(x, 0)
                .rect(rib_thickness, inner_wid - 16)
                .extrude(min(8.0, inner_h/3))
            )
            body = body.union(rib)
            x += rib_pitch

    return body


def make_lid(
    inner_len, inner_wid,
    wall=3.0, lid_thickness=4.0,
    overhang=2.0,            # "שפה" חיצונית שמכסה את הדופן של התחתית
    corner_fillet=4.0,
    groove_depth=2.4,        # עומק חריץ לאטם
    groove_clearance=0.25,   # מרווח בין לשון תחתית לחריץ מכסה
    screw_d=3.2,             # חור בורג במכסה (קלירנס)
    screw_csink_d=6.0,       # קוטר שקיעה
    screw_csink_angle=82,    # זווית שקיעה
):
    """
    יוצר את המכסה:
    - פלטה בעובי lid_thickness עם שפה חיצונית (overhang) לישיבה נקייה.
    - חריץ לאטם (groove) תואם ללשון שבתחתית.
    - חורי ברגים שקועים בארבע פינות.
    """
    outer_len = inner_len + 2 * (wall + overhang)
    outer_wid = inner_wid + 2 * (wall + overhang)
    height    = lid_thickness + wall  # כולל שוליים לשקע האטם

    lid = (
        cq.Workplane("XY")
        .box(outer_len, outer_wid, height, centered=(True, True, False))
    )
    if corner_fillet > 0:
        lid = lid.edges("|Z").fillet(corner_fillet)

    # חלילה כדי ליצור "כובע" – שיישב על דפנות התיבה
    inner_cap_len = inner_len + 2 * wall + 0.3  # טולרנס קטן
    inner_cap_wid = inner_wid + 2 * wall + 0.3
    inner_cap_h   = height - lid_thickness + 0.2

    cavity = (
        cq.Workplane("XY")
        .box(inner_cap_len, inner_cap_wid, inner_cap_h, centered=(True, True, False))
        .translate((0, 0, lid_thickness))  # להשאיר פלטה עליונה בעובי lid_thickness
    )
    lid = lid.cut(cavity)

    # חריץ לאטם – קצת גדול יותר מהלשון של התחתית
    groove_len = inner_len - 2 * groove_clearance
    groove_wid = inner_wid - 2 * groove_clearance
    groove = (
        cq.Workplane("XY")
        .box(groove_len, groove_wid, groove_depth, centered=(True, True, False))
        .translate((0, 0, lid_thickness - groove_depth + 0.2))
    )
    lid = lid.cut(groove)

    # חורי ברגים שקועים (4 פינות)
    # נקבע את המיקומים יחסית לשפת המכסה
    hole_offset_x = (inner_len/2) + wall - 8
    hole_offset_y = (inner_wid/2) + wall - 8
    hole_centers = [
        (+hole_offset_x, +hole_offset_y),
        (+hole_offset_x, -hole_offset_y),
        (-hole_offset_x, +hole_offset_y),
        (-hole_offset_x, -hole_offset_y),
    ]

    # נקבים דרך כל המכסה
    for (x, y) in hole_centers:
        lid = (
            lid.faces(">Z").workplane(centerOption="CenterOfBoundBox")
            .center(x, y)
            .cskHole(screw_d, screw_csink_d, screw_csink_angle, depth=height+1)
        )

    return lid

def export_stl(solid, path: Path, tol=0.1, ang=0.5):
    """
    שמירת STL עם דגימה טובה (tol זוויות/עקומות, ang איכות פאות).
    """
    cq.exporters.export(solid, str(path), exportType='STL', tolerance=tol, angularTolerance=ang)

def main():
    ap = argparse.ArgumentParser(description="Rugged Box STL Generator (CadQuery)")
    ap.add_argument("--inner-length", "-L", type=float, required=True, help="אורך פנימי (מ״מ)")
    ap.add_argument("--inner-width",  "-W", type=float, required=True, help="רוחב פנימי (מ״מ)")
    ap.add_argument("--inner-height", "-H", type=float, required=True, help="גובה פנימי (מ״מ)")
    ap.add_argument("--wall", type=float, default=3.0, help="עובי דופן (מ״מ)")
    ap.add_argument("--floor", type=float, default=3.0, help="עובי רצפה (מ״מ)")
    ap.add_argument("--lid-thickness", type=float, default=4.0, help="עובי מכסה (מ״מ)")
    ap.add_argument("--corner-fillet", type=float, default=4.0, help="פילט פינות חיצוני (מ״מ)")
    ap.add_argument("--rim-height", type=float, default=6.0, help="גובה שפה עליונה בתחתית (מ״מ)")
    ap.add_argument("--tongue-height", type=float, default=2.2, help="גובה לשון אטם (מ״מ)")
    ap.add_argument("--tongue-clearance", type=float, default=0.2, help="טולרנס לשון/חריץ (מ״מ)")
    ap.add_argument("--groove-depth", type=float, default=2.4, help="עומק חריץ אטם במכסה (מ״מ)")
    ap.add_argument("--overhang", type=float, default=2.0, help="שפה חיצונית של המכסה (מ״מ)")
    ap.add_argument("--ribs", action="store_true", help="להוסיף צלעות קשיחה פנימיות")
    ap.add_argument("--outdir", type=str, default=".", help="תיקיית פלט ל-STL")
    args = ap.parse_args()

    inner_len = args.inner_length
    inner_wid = args.inner_width
    inner_h   = args.inner_height

    bottom = make_bottom_box(
        inner_len, inner_wid, inner_h,
        wall=args.wall, floor=args.floor,
        corner_fillet=args.corner_fillet,
        rim_height=args.rim_height,
        tongue_height=args.tongue_height,
        tongue_clearance=args.tongue_clearance,
        ribs=args.ribs
    )

    lid = make_lid(
        inner_len, inner_wid,
        wall=args.wall,
        lid_thickness=args.lid_thickness,
        overhang=args.overhang,
        corner_fillet=args.corner_fillet,
        groove_depth=args.groove_depth,
        groove_clearance=args.tongue_clearance,
    )

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    export_stl(bottom, outdir / "box_bottom.stl")
    export_stl(lid, outdir / "box_lid.stl")

    print(f"✅ נוצרו קבצים:\n  - {outdir/'box_bottom.stl'}\n  - {outdir/'box_lid.stl'}")

if __name__ == "__main__":
    main()
