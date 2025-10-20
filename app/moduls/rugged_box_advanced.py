#!/usr/bin/env python3
"""
Advanced Rugged Box Generator Module
Creates a real rugged box with hinges, latches, and professional features

Command Line Usage:
    python3 rugged_box_advanced.py make_bottom --length 200 --width 150 --height 80 --output bottom.stl
    python3 rugged_box_advanced.py make_lid --length 200 --width 150 --output lid.stl
    python3 rugged_box_advanced.py make_hinge --output hinge.stl
    python3 rugged_box_advanced.py make_latch --output latch.stl
"""

import cadquery as cq
import argparse
import sys
import tempfile
import os
import math

CADQUERY_AVAILABLE = True

def make_bottom(length=200.0, width=150.0, height=80.0, wall_thickness=4.0, floor_thickness=6.0, 
                corner_radius=8.0, rim_height=8.0, hinge_mount_width=20.0, latch_mount_width=15.0):
    """
    Creates the bottom part of a rugged box with hinge and latch mounting points
    
    Args:
        length: External length of the box (mm)
        width: External width of the box (mm)
        height: External height of the box (mm)
        wall_thickness: Thickness of the side walls (mm)
        floor_thickness: Thickness of the bottom floor (mm)
        corner_radius: Radius of corner rounding (mm)
        rim_height: Height of the sealing rim (mm)
        hinge_mount_width: Width of hinge mounting area (mm)
        latch_mount_width: Width of latch mounting area (mm)
    
    Returns:
        CadQuery Workplane object
    """
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")
    
    # Calculate internal dimensions
    inner_length = length - 2 * wall_thickness
    inner_width = width - 2 * wall_thickness
    inner_height = height - floor_thickness
    
    # Create the main box
    box = cq.Workplane("XY").box(length, width, height, centered=(True, True, False))
    
    # Create sealing rim first - positioned at the top edge of the box
    if rim_height > 0:
        rim = cq.Workplane("XY").box(inner_length - 4, inner_width - 4, rim_height, centered=(True, True, False))
        rim = rim.translate((0, 0, height - rim_height))
        box = box.union(rim)
    
    # Create inner cavity - make it taller to ensure it cuts through the entire box
    inner_box = cq.Workplane("XY").box(inner_length, inner_width, height + 2, centered=(True, True, False))
    inner_box = inner_box.translate((0, 0, floor_thickness - 1))
    
    # Cut out the inner cavity
    box = box.cut(inner_box)
    
    # Add corner rounding
    if corner_radius > 0:
        box = box.edges("|Z").fillet(corner_radius)
    
    # Add hinge mounting points (on the back)
    hinge_mounts = make_hinge_mounts(length, width, height, hinge_mount_width, wall_thickness)
    box = box.union(hinge_mounts)
    
    # Add latch mounting points (on the front)
    latch_mounts = make_latch_mounts(length, width, height, latch_mount_width, wall_thickness)
    box = box.union(latch_mounts)
    
    # Add reinforcement ribs
    ribs = make_reinforcement_ribs(inner_length, inner_width, inner_height, wall_thickness, floor_thickness)
    box = box.union(ribs)
    
    return box

def make_lid(length=200.0, width=150.0, lid_thickness=8.0, wall_thickness=4.0, 
             corner_radius=8.0, overhang=3.0, hinge_mount_width=20.0, latch_mount_width=15.0):
    """
    Creates the lid part of a rugged box with hinge and latch mounting points
    
    Args:
        length: External length of the lid (mm)
        width: External width of the lid (mm)
        lid_thickness: Thickness of the lid top (mm)
        wall_thickness: Thickness of the lid walls (mm)
        corner_radius: Radius of corner rounding (mm)
        overhang: Overhang of lid over box walls (mm)
        hinge_mount_width: Width of hinge mounting area (mm)
        latch_mount_width: Width of latch mounting area (mm)
    
    Returns:
        CadQuery Workplane object
    """
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")
    
    # Calculate dimensions
    outer_length = length + 2 * overhang
    outer_width = width + 2 * overhang
    wall_height = 15.0  # Height of lid walls
    
    # Create the main lid
    lid = cq.Workplane("XY").box(outer_length, outer_width, lid_thickness, centered=(True, True, False))
    
    # Create inner cavity for sealing
    inner_length = length - 2 * wall_thickness
    inner_width = width - 2 * wall_thickness
    inner_cavity = cq.Workplane("XY").box(inner_length, inner_width, lid_thickness + 1, centered=(True, True, False))
    inner_cavity = inner_cavity.translate((0, 0, -1))
    lid = lid.cut(inner_cavity)
    
    # Add corner rounding
    if corner_radius > 0:
        lid = lid.edges("|Z").fillet(corner_radius)
    
    # Add hinge mounting points (on the back)
    hinge_mounts = make_hinge_mounts(outer_length, outer_width, lid_thickness, hinge_mount_width, wall_thickness, is_lid=True)
    lid = lid.union(hinge_mounts)
    
    # Add latch mounting points (on the front)
    latch_mounts = make_latch_mounts(outer_length, outer_width, lid_thickness, latch_mount_width, wall_thickness, is_lid=True)
    lid = lid.union(latch_mounts)
    
    return lid

def make_hinge_mounts(length, width, height, mount_width, wall_thickness, is_lid=False):
    """
    Creates hinge mounting points
    
    Args:
        length: Length of the box/lid (mm)
        width: Width of the box/lid (mm)
        height: Height of the box/lid (mm)
        mount_width: Width of the mounting area (mm)
        wall_thickness: Wall thickness (mm)
        is_lid: Whether this is for the lid (affects positioning)
    
    Returns:
        CadQuery Workplane object with hinge mounts
    """
    # Hinge mounting points (2 on each side)
    mounts = cq.Workplane("XY")
    
    # Mount dimensions
    mount_height = 12.0
    mount_depth = 8.0
    mount_spacing = 40.0  # Distance between hinges
    
    # Calculate positions
    y_pos = width / 2 + wall_thickness / 2
    x_positions = [-mount_spacing/2, mount_spacing/2]
    
    for x_pos in x_positions:
        # Create mounting block
        mount = cq.Workplane("XY").box(mount_width, mount_depth, mount_height, centered=(True, True, False))
        mount = mount.translate((x_pos, y_pos, height - mount_height))
        
        # Add mounting holes
        hole_diameter = 4.0
        hole_depth = mount_depth + 2
        
        # Top hole
        top_hole = cq.Workplane("XY").circle(hole_diameter/2).extrude(hole_depth)
        top_hole = top_hole.translate((x_pos, y_pos + mount_depth/2 + 1, height - mount_height/2))
        
        # Bottom hole
        bottom_hole = cq.Workplane("XY").circle(hole_diameter/2).extrude(hole_depth)
        bottom_hole = bottom_hole.translate((x_pos, y_pos + mount_depth/2 + 1, height - mount_height + 2))
        
        mount = mount.cut(top_hole).cut(bottom_hole)
        mounts = mounts.union(mount)
    
    return mounts

def make_latch_mounts(length, width, height, mount_width, wall_thickness, is_lid=False):
    """
    Creates latch mounting points
    
    Args:
        length: Length of the box/lid (mm)
        width: Width of the box/lid (mm)
        height: Height of the box/lid (mm)
        mount_width: Width of the mounting area (mm)
        wall_thickness: Wall thickness (mm)
        is_lid: Whether this is for the lid (affects positioning)
    
    Returns:
        CadQuery Workplane object with latch mounts
    """
    # Latch mounting points (center front)
    mounts = cq.Workplane("XY")
    
    # Mount dimensions
    mount_height = 10.0
    mount_depth = 6.0
    
    # Calculate position (center front)
    y_pos = width / 2 + wall_thickness / 2
    
    # Create mounting block
    mount = cq.Workplane("XY").box(mount_width, mount_depth, mount_height, centered=(True, True, False))
    mount = mount.translate((0, y_pos, height - mount_height))
    
    # Add mounting holes
    hole_diameter = 3.0
    hole_spacing = 12.0
    
    # Two mounting holes
    for x_offset in [-hole_spacing/2, hole_spacing/2]:
        hole = cq.Workplane("XY").circle(hole_diameter/2).extrude(mount_depth + 2)
        hole = hole.translate((x_offset, y_pos + mount_depth/2 + 1, height - mount_height/2))
        mount = mount.cut(hole)
    
    mounts = mounts.union(mount)
    return mounts

def make_reinforcement_ribs(inner_length, inner_width, inner_height, wall_thickness, floor_thickness):
    """
    Creates reinforcement ribs inside the box
    
    Args:
        inner_length: Inner length of the box (mm)
        inner_width: Inner width of the box (mm)
        inner_height: Inner height of the box (mm)
        wall_thickness: Wall thickness (mm)
    
    Returns:
        CadQuery Workplane object with reinforcement ribs
    """
    ribs = cq.Workplane("XY")
    
    # Rib dimensions
    rib_thickness = 2.0
    rib_height = inner_height * 0.7  # 70% of inner height
    
    # Vertical ribs on sides - positioned to not interfere with hollow space
    for x_pos in [-inner_length/2 + wall_thickness, inner_length/2 - wall_thickness]:
        rib = cq.Workplane("XY").box(rib_thickness, inner_width - 2*wall_thickness, rib_height, centered=(True, True, False))
        rib = rib.translate((x_pos, 0, floor_thickness + 2))  # Start above floor
        ribs = ribs.union(rib)
    
    # Vertical ribs on front/back - positioned to not interfere with hollow space
    for y_pos in [-inner_width/2 + wall_thickness, inner_width/2 - wall_thickness]:
        rib = cq.Workplane("XY").box(inner_length - 2*wall_thickness, rib_thickness, rib_height, centered=(True, True, False))
        rib = rib.translate((0, y_pos, floor_thickness + 2))  # Start above floor
        ribs = ribs.union(rib)
    
    return ribs

def make_hinge(length=30.0, width=15.0, thickness=3.0, pin_diameter=4.0):
    """
    Creates a simple hinge for the rugged box
    
    Args:
        length: Length of the hinge (mm)
        width: Width of the hinge (mm)
        thickness: Thickness of the hinge material (mm)
        pin_diameter: Diameter of the hinge pin (mm)
    
    Returns:
        CadQuery Workplane object
    """
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")
    
    # Create hinge body
    hinge = cq.Workplane("XY").box(length, width, thickness, centered=(True, True, False))
    
    # Add hinge knuckles
    knuckle_diameter = 8.0
    knuckle_height = 6.0
    knuckle_spacing = 4.0
    
    # Calculate number of knuckles
    num_knuckles = int((length - knuckle_spacing) / (knuckle_diameter + knuckle_spacing))
    
    for i in range(num_knuckles):
        x_pos = -length/2 + knuckle_spacing + i * (knuckle_diameter + knuckle_spacing) + knuckle_diameter/2
        knuckle = cq.Workplane("XY").cylinder(knuckle_height, knuckle_diameter/2)
        knuckle = knuckle.translate((x_pos, 0, thickness))
        hinge = hinge.union(knuckle)
    
    # Add pin hole
    pin_hole = cq.Workplane("XY").cylinder(thickness + knuckle_height, pin_diameter/2)
    hinge = hinge.cut(pin_hole)
    
    return hinge

def make_latch(length=40.0, width=20.0, thickness=4.0, catch_depth=8.0):
    """
    Creates a simple latch for the rugged box
    
    Args:
        length: Length of the latch (mm)
        width: Width of the latch (mm)
        thickness: Thickness of the latch material (mm)
        catch_depth: Depth of the catch mechanism (mm)
    
    Returns:
        CadQuery Workplane object
    """
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")
    
    # Create latch body
    latch = cq.Workplane("XY").box(length, width, thickness, centered=(True, True, False))
    
    # Add catch mechanism
    catch = cq.Workplane("XY").box(catch_depth, width - 4, thickness + 4, centered=(True, True, False))
    catch = catch.translate((length/2 + catch_depth/2, 0, 2))
    latch = latch.union(catch)
    
    # Add mounting holes
    hole_diameter = 3.0
    hole_spacing = 12.0
    
    for x_offset in [-hole_spacing/2, hole_spacing/2]:
        hole = cq.Workplane("XY").circle(hole_diameter/2).extrude(thickness + 2)
        hole = hole.translate((x_offset, 0, -1))
        latch = latch.cut(hole)
    
    return latch

def export_stl_bytes(solid, tol=0.02, ang=0.2) -> bytes:
    """
    Export CadQuery solid to STL bytes
    """
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")
        
    with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as tmp_file:
        tmp_path = tmp_file.name
    
    try:
        cq.exporters.export(solid, tmp_path, exportType='STL', tolerance=tol, angularTolerance=ang)
        with open(tmp_path, 'rb') as f:
            data = f.read()
        return data
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

def main():
    """Command line interface for advanced rugged box generator"""
    parser = argparse.ArgumentParser(
        description="Advanced Rugged Box Generator - Create professional rugged boxes with hinges and latches",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 rugged_box_advanced.py make_bottom --length 200 --width 150 --height 80 --output bottom.stl
    python3 rugged_box_advanced.py make_lid --length 200 --width 150 --output lid.stl
    python3 rugged_box_advanced.py make_hinge --output hinge.stl
    python3 rugged_box_advanced.py make_latch --output latch.stl
        """
    )
    
    # Subcommands for different functions
    subparsers = parser.add_subparsers(dest='function', help='Available functions')
    
    # make_bottom command
    bottom_parser = subparsers.add_parser('make_bottom', help='Create the bottom part of the rugged box')
    bottom_parser.add_argument('--length', type=float, default=200.0, help='External length (mm)')
    bottom_parser.add_argument('--width', type=float, default=150.0, help='External width (mm)')
    bottom_parser.add_argument('--height', type=float, default=80.0, help='External height (mm)')
    bottom_parser.add_argument('--wall_thickness', type=float, default=4.0, help='Wall thickness (mm)')
    bottom_parser.add_argument('--floor_thickness', type=float, default=6.0, help='Floor thickness (mm)')
    bottom_parser.add_argument('--corner_radius', type=float, default=8.0, help='Corner radius (mm)')
    bottom_parser.add_argument('--rim_height', type=float, default=8.0, help='Sealing rim height (mm)')
    bottom_parser.add_argument('--output', '-o', default='rugged_box_bottom.stl', help='Output STL file')
    
    # make_lid command
    lid_parser = subparsers.add_parser('make_lid', help='Create the lid part of the rugged box')
    lid_parser.add_argument('--length', type=float, default=200.0, help='External length (mm)')
    lid_parser.add_argument('--width', type=float, default=150.0, help='External width (mm)')
    lid_parser.add_argument('--lid_thickness', type=float, default=8.0, help='Lid thickness (mm)')
    lid_parser.add_argument('--wall_thickness', type=float, default=4.0, help='Wall thickness (mm)')
    lid_parser.add_argument('--corner_radius', type=float, default=8.0, help='Corner radius (mm)')
    lid_parser.add_argument('--overhang', type=float, default=3.0, help='Overhang (mm)')
    lid_parser.add_argument('--output', '-o', default='rugged_box_lid.stl', help='Output STL file')
    
    # make_hinge command
    hinge_parser = subparsers.add_parser('make_hinge', help='Create a hinge for the rugged box')
    hinge_parser.add_argument('--length', type=float, default=30.0, help='Hinge length (mm)')
    hinge_parser.add_argument('--width', type=float, default=15.0, help='Hinge width (mm)')
    hinge_parser.add_argument('--thickness', type=float, default=3.0, help='Hinge thickness (mm)')
    hinge_parser.add_argument('--pin_diameter', type=float, default=4.0, help='Pin diameter (mm)')
    hinge_parser.add_argument('--output', '-o', default='hinge.stl', help='Output STL file')
    
    # make_latch command
    latch_parser = subparsers.add_parser('make_latch', help='Create a latch for the rugged box')
    latch_parser.add_argument('--length', type=float, default=40.0, help='Latch length (mm)')
    latch_parser.add_argument('--width', type=float, default=20.0, help='Latch width (mm)')
    latch_parser.add_argument('--thickness', type=float, default=4.0, help='Latch thickness (mm)')
    latch_parser.add_argument('--catch_depth', type=float, default=8.0, help='Catch depth (mm)')
    latch_parser.add_argument('--output', '-o', default='latch.stl', help='Output STL file')
    
    args = parser.parse_args()
    
    if not args.function:
        parser.print_help()
        return
    
    try:
        print(f"🔧 Generating {args.function}...")
        
        if args.function == 'make_bottom':
            print(f"   Dimensions: {args.length} x {args.width} x {args.height} mm")
            print(f"   Wall thickness: {args.wall_thickness} mm")
            print(f"   Floor thickness: {args.floor_thickness} mm")
            solid = make_bottom(
                length=args.length, width=args.width, height=args.height,
                wall_thickness=args.wall_thickness, floor_thickness=args.floor_thickness,
                corner_radius=args.corner_radius, rim_height=args.rim_height
            )
        elif args.function == 'make_lid':
            print(f"   Dimensions: {args.length} x {args.width} mm")
            print(f"   Lid thickness: {args.lid_thickness} mm")
            print(f"   Overhang: {args.overhang} mm")
            solid = make_lid(
                length=args.length, width=args.width, lid_thickness=args.lid_thickness,
                wall_thickness=args.wall_thickness, corner_radius=args.corner_radius,
                overhang=args.overhang
            )
        elif args.function == 'make_hinge':
            print(f"   Dimensions: {args.length} x {args.width} x {args.thickness} mm")
            print(f"   Pin diameter: {args.pin_diameter} mm")
            solid = make_hinge(
                length=args.length, width=args.width, thickness=args.thickness,
                pin_diameter=args.pin_diameter
            )
        elif args.function == 'make_latch':
            print(f"   Dimensions: {args.length} x {args.width} x {args.thickness} mm")
            print(f"   Catch depth: {args.catch_depth} mm")
            solid = make_latch(
                length=args.length, width=args.width, thickness=args.thickness,
                catch_depth=args.catch_depth
            )
        else:
            print(f"❌ Unknown function: {args.function}")
            return
        
        # Export to STL
        print(f"📁 Exporting to: {args.output}")
        data = export_stl_bytes(solid, tol=0.01, ang=0.05)
        
        # Write to file
        with open(args.output, 'wb') as f:
            f.write(data)
        
        print(f"✅ Success! Generated {args.output}")
        print(f"   File size: {len(data)} bytes")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
