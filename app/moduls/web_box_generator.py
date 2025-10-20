#!/usr/bin/env python3
"""
Web Box Generator Module
Contains CadQuery functions for generating STL models in the web application
"""

import tempfile
import os

# Try to import CadQuery
try:
    import cadquery as cq
    CADQUERY_AVAILABLE = True
except ImportError:
    CADQUERY_AVAILABLE = False
    cq = None


def make_simple_hollow_box(inner_len, inner_wid, inner_h, wall=3.0, floor=3.0, corner_fillet=4.0, rim_height=6.0):
    """
    Creates a simple hollow box for preview - no bosses, tongue, or other features
    Just a basic hollow box to show the interior space clearly
    """
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")
        
    outer_len = inner_len + 2 * wall
    outer_wid = inner_wid + 2 * wall
    outer_h = floor + inner_h + rim_height  # Include rim height for accurate preview

    # Outer body
    body = (
        cq.Workplane("XY")
        .box(outer_len, outer_wid, outer_h, centered=(True, True, False))
    )
    if corner_fillet > 0:
        body = body.edges("|Z").fillet(corner_fillet)

    # Hollow out - just basic hollowing
    inner = (
        cq.Workplane("XY")
        .box(inner_len, inner_wid, inner_h, centered=(True, True, False))
        .translate((0, 0, floor))
    )
    body = body.cut(inner)

    return body


def make_bottom_box(
    inner_len, inner_wid, inner_h,
    wall=3.0, floor=3.0,
    corner_fillet=4.0,
    rim_height=6.0,
    tongue_height=2.2,
    tongue_clearance=0.2,
    screw_d=3.2,
    screw_csink_d=6.0,
    screw_csink_angle=82,
    boss_outer_d=2.0,  # Much smaller bosses
    boss_h=3.0,        # Much shorter bosses
    boss_core_d=1.0,   # Much smaller pilot holes
    ribs=False,
    rib_thickness=2.0,
    rib_pitch=20.0,
):
    """
    Creates the bottom box with all features
    """
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")
        
    # Outer dimensions
    outer_len = inner_len + 2 * wall
    outer_wid = inner_wid + 2 * wall
    outer_h = floor + inner_h + rim_height

    # Outer body
    body = (
        cq.Workplane("XY")
        .box(outer_len, outer_wid, outer_h, centered=(True, True, False))
    )
    if corner_fillet > 0:
        body = body.edges("|Z").fillet(corner_fillet)

    # Hollow out - keep floor + walls + rim
    cavity_h = inner_h + rim_height
    inner = (
        cq.Workplane("XY")
        .box(inner_len, inner_wid, cavity_h, centered=(True, True, False))
        .translate((0, 0, floor))
    )
    body = body.cut(inner)

    # Tongue for sealing - protrudes from rim inward
    tongue_len = inner_len - 2 * tongue_clearance
    tongue_wid = inner_wid - 2 * tongue_clearance
    tongue = (
        cq.Workplane("XY")
        .box(tongue_len, tongue_wid, tongue_height, centered=(True, True, False))
        .translate((0, 0, floor + inner_h))
    )
    # Light corner rounding on tongue
    tongue = tongue.edges("|Z").fillet(min(0.6, max(0.0, corner_fillet / 4)))
    body = body.union(tongue)

    # Bosses - 4 internal corners
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

    # Pilot holes in bosses - drill from body (has parent solid, no error)
    body = (
        body
        .faces(">Z").workplane(centerOption="CenterOfBoundBox")
        .pushPoints(boss_centers)
        .hole(boss_core_d, depth=boss_h + 2)   # Slightly deeper than boss height
    )

    # Optional stiffening ribs on floor
    if ribs:
        # Along X
        y = -inner_wid/2 + rib_pitch
        while y < inner_wid/2 - rib_pitch/2:
            rib = (
                cq.Workplane("XY")
                .workplane(offset=floor + 0.01)
                .center(0, y)
                .rect(inner_len - 16, rib_thickness)  # 8mm clearance from bosses on each side
                .extrude(min(8.0, inner_h/3))
            )
            body = body.union(rib)
            y += rib_pitch

        # Along Y
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
    overhang=2.0,            # "rim" that covers the bottom's wall
    corner_fillet=4.0,
    groove_depth=2.4,        # seal groove depth
    groove_clearance=0.25,   # clearance between bottom tongue and lid groove
    screw_d=3.2,             # screw hole in lid (clearance)
    screw_csink_d=6.0,       # countersink diameter
    screw_csink_angle=82,    # countersink angle
):
    """
    Creates the lid:
    - Plate with lid_thickness with external rim (overhang) for clean seating.
    - Seal groove (groove) matching the tongue in the bottom.
    - Countersunk screw holes in four corners.
    """
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")
        
    outer_len = inner_len + 2 * (wall + overhang)
    outer_wid = inner_wid + 2 * (wall + overhang)
    height = lid_thickness + wall  # Including margins for seal groove

    lid = (
        cq.Workplane("XY")
        .box(outer_len, outer_wid, height, centered=(True, True, False))
    )
    if corner_fillet > 0:
        lid = lid.edges("|Z").fillet(corner_fillet)

    # Hollow out to create "cap" - sits on box walls
    inner_cap_len = inner_len + 2 * wall + 0.3  # Small tolerance
    inner_cap_wid = inner_wid + 2 * wall + 0.3
    inner_cap_h = height - lid_thickness + 0.2

    cavity = (
        cq.Workplane("XY")
        .box(inner_cap_len, inner_cap_wid, inner_cap_h, centered=(True, True, False))
        .translate((0, 0, lid_thickness))  # Leave top plate with lid_thickness
    )
    lid = lid.cut(cavity)

    # Seal groove - slightly larger than bottom tongue
    groove_len = inner_len - 2 * groove_clearance
    groove_wid = inner_wid - 2 * groove_clearance
    groove = (
        cq.Workplane("XY")
        .box(groove_len, groove_wid, groove_depth, centered=(True, True, False))
        .translate((0, 0, lid_thickness - groove_depth + 0.2))
    )
    lid = lid.cut(groove)

    # Countersunk screw holes (4 corners)
    # Position relative to lid rim
    hole_offset_x = (inner_len/2) + wall - 8
    hole_offset_y = (inner_wid/2) + wall - 8
    hole_centers = [
        (+hole_offset_x, +hole_offset_y),
        (+hole_offset_x, -hole_offset_y),
        (-hole_offset_x, +hole_offset_y),
        (-hole_offset_x, -hole_offset_y),
    ]

    # Holes through entire lid
    for (x, y) in hole_centers:
        lid = (
            lid.faces(">Z").workplane(centerOption="CenterOfBoundBox")
            .center(x, y)
            .cskHole(screw_d, screw_csink_d, screw_csink_angle, depth=height+1)
        )

    return lid


def export_stl_bytes(solid, tol=0.02, ang=0.2) -> bytes:
    """
    Export CadQuery solid to STL bytes
    """
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")
        
    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as tmp_file:
        tmp_path = tmp_file.name
    
    try:
        # Export to temporary file
        cq.exporters.export(solid, tmp_path, exportType='STL', tolerance=tol, angularTolerance=ang)
        
        # Read the file content
        with open(tmp_path, 'rb') as f:
            data = f.read()
        
        return data
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
