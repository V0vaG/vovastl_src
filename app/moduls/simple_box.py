#!/usr/bin/env python3
"""
Simple Box Generator Module
Creates basic box models with x, y, z dimensions

Command Line Usage:
    python3 simple_box.py make_simple_box --x 100 --y 80 --z 50 --output simple_box.stl
    python3 simple_box.py make_rounded_box --x 100 --y 80 --z 50 --corner_radius 10 --output rounded_box.stl
    python3 simple_box.py make_hollow_box --x 100 --y 80 --z 50 --wall_thickness 5 --output hollow_box.stl
"""

import cadquery as cq
import argparse
import sys
import tempfile
import os

CADQUERY_AVAILABLE = True  # Assume CadQuery is available in this module's context

def make_simple_box(x=100.0, y=100.0, z=50.0):
    """
    Creates a simple solid box
    
    Args:
        x: Length in X direction (mm)
        y: Width in Y direction (mm)
        z: Height in Z direction (mm)
    
    Returns:
        CadQuery solid object
    """
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")
    
    # Create a simple box
    box = cq.Workplane("XY").box(x, y, z)
    
    return box

def make_hollow_box(x=100.0, y=100.0, z=50.0, wall_thickness=5.0):
    """
    Creates a hollow box with specified wall thickness
    
    Args:
        x: Outer length in X direction (mm)
        y: Outer width in Y direction (mm)
        z: Outer height in Z direction (mm)
        wall_thickness: Thickness of the walls (mm)
    
    Returns:
        CadQuery solid object
    """
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")
    
    # Create outer box
    outer_box = cq.Workplane("XY").box(x, y, z)
    
    # Create inner box (hollow space)
    inner_x = x - 2 * wall_thickness
    inner_y = y - 2 * wall_thickness
    inner_z = z - wall_thickness  # Keep bottom floor
    
    if inner_x > 0 and inner_y > 0 and inner_z > 0:
        inner_box = (
            cq.Workplane("XY")
            .box(inner_x, inner_y, inner_z)
            .translate((0, 0, wall_thickness))
        )
        hollow_box = outer_box.cut(inner_box)
    else:
        # If walls are too thick, just return solid box
        hollow_box = outer_box
    
    return hollow_box

def make_rounded_box(x=100.0, y=100.0, z=50.0, corner_radius=10.0):
    """
    Creates a box with rounded corners
    
    Args:
        x: Length in X direction (mm)
        y: Width in Y direction (mm)
        z: Height in Z direction (mm)
        corner_radius: Radius of corner rounding (mm)
    
    Returns:
        CadQuery solid object
    """
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")
    
    # Create a box with rounded corners
    box = cq.Workplane("XY").box(x, y, z)
    
    # Add fillets to vertical edges (with validation)
    if corner_radius > 0:
        # Validate that corner_radius is reasonable for the box dimensions
        max_radius = min(x, y) / 2.0  # Maximum radius is half the smallest dimension
        safe_radius = min(corner_radius, max_radius * 0.9)  # Use 90% of max for safety
        
        if safe_radius > 0.1:  # Only apply fillet if radius is meaningful
            box = box.edges("|Z").fillet(safe_radius)
    
    return box

def export_stl_bytes(solid, tol=0.02, ang=0.2) -> bytes:
    """
    Export CadQuery solid to STL bytes
    """
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")
        
    import tempfile
    import os
    
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

def main():
    """Command line interface for simple box generator"""
    parser = argparse.ArgumentParser(
        description="Simple Box Generator - Create box STL models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 simple_box.py make_simple_box --x 100 --y 80 --z 50 --output simple_box.stl
    python3 simple_box.py make_rounded_box --x 100 --y 80 --z 50 --corner_radius 10 --output rounded_box.stl
    python3 simple_box.py make_hollow_box --x 100 --y 80 --z 50 --wall_thickness 5 --output hollow_box.stl
        """
    )
    
    # Subcommands for different functions
    subparsers = parser.add_subparsers(dest='function', help='Available functions')
    
    # make_simple_box command
    simple_parser = subparsers.add_parser('make_simple_box', help='Create a solid box')
    simple_parser.add_argument('--x', type=float, default=100.0, help='Length in X direction (mm)')
    simple_parser.add_argument('--y', type=float, default=100.0, help='Width in Y direction (mm)')
    simple_parser.add_argument('--z', type=float, default=50.0, help='Height in Z direction (mm)')
    simple_parser.add_argument('--output', '-o', default='simple_box.stl', help='Output STL file')
    
    # make_rounded_box command
    rounded_parser = subparsers.add_parser('make_rounded_box', help='Create a box with rounded corners')
    rounded_parser.add_argument('--x', type=float, default=100.0, help='Length in X direction (mm)')
    rounded_parser.add_argument('--y', type=float, default=100.0, help='Width in Y direction (mm)')
    rounded_parser.add_argument('--z', type=float, default=50.0, help='Height in Z direction (mm)')
    rounded_parser.add_argument('--corner_radius', type=float, default=5.0, help='Corner radius (mm)')
    rounded_parser.add_argument('--output', '-o', default='rounded_box.stl', help='Output STL file')
    
    # make_hollow_box command
    hollow_parser = subparsers.add_parser('make_hollow_box', help='Create a hollow box')
    hollow_parser.add_argument('--x', type=float, default=100.0, help='Outer length in X direction (mm)')
    hollow_parser.add_argument('--y', type=float, default=100.0, help='Outer width in Y direction (mm)')
    hollow_parser.add_argument('--z', type=float, default=50.0, help='Outer height in Z direction (mm)')
    hollow_parser.add_argument('--wall_thickness', type=float, default=3.0, help='Wall thickness (mm)')
    hollow_parser.add_argument('--output', '-o', default='hollow_box.stl', help='Output STL file')
    
    args = parser.parse_args()
    
    if not args.function:
        parser.print_help()
        return
    
    try:
        print(f"📦 Generating {args.function}...")
        
        if args.function == 'make_simple_box':
            print(f"   Dimensions: {args.x} x {args.y} x {args.z} mm")
            solid = make_simple_box(x=args.x, y=args.y, z=args.z)
        elif args.function == 'make_rounded_box':
            print(f"   Dimensions: {args.x} x {args.y} x {args.z} mm")
            print(f"   Corner radius: {args.corner_radius} mm")
            solid = make_rounded_box(x=args.x, y=args.y, z=args.z, corner_radius=args.corner_radius)
        elif args.function == 'make_hollow_box':
            print(f"   Outer dimensions: {args.x} x {args.y} x {args.z} mm")
            print(f"   Wall thickness: {args.wall_thickness} mm")
            solid = make_hollow_box(x=args.x, y=args.y, z=args.z, wall_thickness=args.wall_thickness)
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
