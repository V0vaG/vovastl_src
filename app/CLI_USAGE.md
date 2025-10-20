# Command Line Interface for STL Model Generation

This document explains how to use the `cli_runner.py` script to generate STL models manually from the command line.

## Quick Start

```bash
# Navigate to the app directory
cd /home/vova/GIT/vovastl_src/app

# List all available modules
python3 cli_runner.py --list-modules

# List functions for a specific module
python3 cli_runner.py --list-functions sphere_generator

# Generate a model
python3 cli_runner.py <module> <function> --output <filename.stl> [parameters...]
```

## Examples

### Sphere Generation

```bash
# Generate a simple sphere with 20mm radius
python3 cli_runner.py sphere_generator make_sphere --radius 20 --output sphere_20mm.stl

# Generate a hollow sphere
python3 cli_runner.py sphere_generator make_hollow_sphere --radius 25 --wall_thickness 3 --output hollow_sphere.stl
```

### Simple Box Generation

```bash
# Generate a simple solid box
python3 cli_runner.py simple_box make_simple_box --x 100 --y 80 --z 50 --output simple_box.stl

# Generate a rounded box
python3 cli_runner.py simple_box make_rounded_box --x 100 --y 80 --z 50 --corner_radius 10 --output rounded_box.stl

# Generate a hollow box
python3 cli_runner.py simple_box make_hollow_box --x 100 --y 80 --z 50 --wall_thickness 5 --output hollow_box.stl
```

### Web Box Generation

```bash
# Generate a web box bottom
python3 cli_runner.py web_box_generator make_bottom_box --L 160 --W 100 --H 60 --wall 3 --floor 3 --output web_box_bottom.stl

# Generate a web box lid
python3 cli_runner.py web_box_generator make_lid --L 160 --W 100 --wall 3 --lid_thickness 4 --output web_box_lid.stl

# Generate a simple hollow box (preview version)
python3 cli_runner.py web_box_generator make_simple_hollow_box --L 160 --W 100 --H 60 --wall 3 --floor 3 --output simple_hollow_box.stl
```

## Parameter Reference

### Sphere Generator Parameters
- `--radius`: Radius of the sphere (mm)
- `--wall_thickness`: Wall thickness for hollow sphere (mm)

### Simple Box Parameters
- `--x`: Length in X direction (mm)
- `--y`: Width in Y direction (mm)
- `--z`: Height in Z direction (mm)
- `--corner_radius`: Corner radius for rounded box (mm)
- `--wall_thickness`: Wall thickness for hollow box (mm)

### Web Box Generator Parameters
- `--L`: Inner length (mm)
- `--W`: Inner width (mm)
- `--H`: Inner height (mm)
- `--wall`: Wall thickness (mm)
- `--floor`: Floor thickness (mm)
- `--corner_fillet`: Corner fillet radius (mm)
- `--rim_height`: Rim height (mm)
- `--tongue_height`: Tongue height (mm)
- `--tongue_clearance`: Tongue clearance (mm)
- `--groove_depth`: Groove depth (mm)
- `--lid_thickness`: Lid thickness (mm)
- `--overhang`: Overhang (mm)
- `--ribs`: Add internal ribs (true/false)

## Advanced Usage

### Batch Processing

You can create scripts to generate multiple models:

```bash
#!/bin/bash
# generate_multiple_models.sh

# Generate spheres with different radii
for radius in 10 15 20 25 30; do
    python3 cli_runner.py sphere_generator make_sphere --radius $radius --output "sphere_${radius}mm.stl"
done

# Generate boxes with different dimensions
python3 cli_runner.py simple_box make_simple_box --x 50 --y 50 --z 50 --output "cube_50mm.stl"
python3 cli_runner.py simple_box make_simple_box --x 100 --y 50 --z 25 --output "box_100x50x25.stl"
```

### Integration with Other Tools

The CLI can be integrated with other tools and scripts:

```python
import subprocess
import os

def generate_sphere(radius, output_file):
    """Generate a sphere using the CLI"""
    cmd = [
        'python3', 'cli_runner.py',
        'sphere_generator', 'make_sphere',
        '--radius', str(radius),
        '--output', output_file
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✅ Generated: {output_file}")
    else:
        print(f"❌ Error: {result.stderr}")

# Usage
generate_sphere(20, "my_sphere.stl")
```

## Troubleshooting

### Common Issues

1. **Module not found**: Make sure you're running from the correct directory (`/home/vova/GIT/vovastl_src/app`)

2. **Function not found**: Use `--list-functions <module>` to see available functions

3. **Parameter errors**: Check the parameter names and types using `--list-functions <module>`

4. **CadQuery not available**: Make sure CadQuery is installed and working

### Getting Help

```bash
# Show help
python3 cli_runner.py --help

# List all modules
python3 cli_runner.py --list-modules

# List functions for a module
python3 cli_runner.py --list-functions <module_name>
```

## File Output

- Generated STL files are saved in the current directory by default
- Use `--output` to specify a custom path
- Files are generated with high resolution (tol=0.01, ang=0.05)
- File sizes vary depending on complexity and resolution
