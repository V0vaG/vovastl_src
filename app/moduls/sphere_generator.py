import cadquery as cq
import tempfile
import os
import argparse
import sys

"""
Sphere Generator Module
Creates simple sphere models with customizable radius

Command Line Usage:
    python3 sphere_generator.py make_sphere --radius 20 --output sphere_20mm.stl
    python3 sphere_generator.py make_hollow_sphere --radius 25 --wall_thickness 3 --output hollow_sphere.stl
"""

CADQUERY_AVAILABLE = True

def make_sphere(radius=10.0):
    """
    Creates a simple sphere model.
    :param radius: Radius of the sphere (mm).
    """
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")

    # Create a sphere
    sphere = cq.Workplane("XY").sphere(radius)
    
    return sphere

def make_hollow_sphere(radius=10.0, wall_thickness=2.0):
    """
    Creates a hollow sphere with specified wall thickness.
    :param radius: Outer radius of the sphere (mm).
    :param wall_thickness: Thickness of the sphere wall (mm).
    """
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")

    # Create outer sphere
    outer_sphere = cq.Workplane("XY").sphere(radius)
    
    # Create inner sphere (hollow)
    inner_radius = radius - wall_thickness
    if inner_radius > 0:
        inner_sphere = cq.Workplane("XY").sphere(inner_radius)
        hollow_sphere = outer_sphere.cut(inner_sphere)
    else:
        hollow_sphere = outer_sphere  # If wall is too thick, return solid sphere
    
    return hollow_sphere

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
    """Command line interface for sphere generator"""
    parser = argparse.ArgumentParser(
        description="Sphere Generator - Create sphere STL models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 sphere_generator.py make_sphere --radius 20 --output sphere_20mm.stl
    python3 sphere_generator.py make_hollow_sphere --radius 25 --wall_thickness 3 --output hollow_sphere.stl
        """
    )
    
    # Subcommands for different functions
    subparsers = parser.add_subparsers(dest='function', help='Available functions')
    
    # make_sphere command
    sphere_parser = subparsers.add_parser('make_sphere', help='Create a solid sphere')
    sphere_parser.add_argument('--radius', type=float, default=10.0, help='Radius of the sphere (mm)')
    sphere_parser.add_argument('--output', '-o', default='sphere.stl', help='Output STL file')
    
    # make_hollow_sphere command
    hollow_parser = subparsers.add_parser('make_hollow_sphere', help='Create a hollow sphere')
    hollow_parser.add_argument('--radius', type=float, default=10.0, help='Outer radius of the sphere (mm)')
    hollow_parser.add_argument('--wall_thickness', type=float, default=2.0, help='Wall thickness (mm)')
    hollow_parser.add_argument('--output', '-o', default='hollow_sphere.stl', help='Output STL file')
    
    args = parser.parse_args()
    
    if not args.function:
        parser.print_help()
        return
    
    try:
        print(f"🌐 Generating {args.function}...")
        
        if args.function == 'make_sphere':
            print(f"   Radius: {args.radius} mm")
            solid = make_sphere(radius=args.radius)
        elif args.function == 'make_hollow_sphere':
            print(f"   Outer radius: {args.radius} mm")
            print(f"   Wall thickness: {args.wall_thickness} mm")
            solid = make_hollow_sphere(radius=args.radius, wall_thickness=args.wall_thickness)
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
