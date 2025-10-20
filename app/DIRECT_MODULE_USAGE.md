# Direct Module Execution Guide

This guide shows how to run the STL generation modules directly from the command line.

## Quick Start

```bash
# Navigate to the moduls directory
cd /home/vova/GIT/vovastl_src/app/moduls

# Run any module directly
python3 <module_name>.py <function> [parameters...]
```

## Sphere Generator

### Available Functions:
- `make_sphere` - Create a solid sphere
- `make_hollow_sphere` - Create a hollow sphere

### Examples:

```bash
# Generate a simple sphere with 20mm radius
python3 sphere_generator.py make_sphere --radius 20 --output sphere_20mm.stl

# Generate a hollow sphere
python3 sphere_generator.py make_hollow_sphere --radius 25 --wall_thickness 3 --output hollow_sphere.stl

# Use default values
python3 sphere_generator.py make_sphere
# Creates: sphere.stl with 10mm radius

# Get help
python3 sphere_generator.py --help
python3 sphere_generator.py make_sphere --help
```

### Parameters:
- `--radius`: Radius of the sphere (mm) - default: 10.0
- `--wall_thickness`: Wall thickness for hollow sphere (mm) - default: 2.0
- `--output`, `-o`: Output STL file - default: function-specific name

## Simple Box Generator

### Available Functions:
- `make_simple_box` - Create a solid box
- `make_rounded_box` - Create a box with rounded corners
- `make_hollow_box` - Create a hollow box

### Examples:

```bash
# Generate a simple solid box
python3 simple_box.py make_simple_box --x 100 --y 80 --z 50 --output simple_box.stl

# Generate a rounded box
python3 simple_box.py make_rounded_box --x 100 --y 80 --z 50 --corner_radius 10 --output rounded_box.stl

# Generate a hollow box
python3 simple_box.py make_hollow_box --x 100 --y 80 --z 50 --wall_thickness 5 --output hollow_box.stl

# Use default values
python3 simple_box.py make_simple_box
# Creates: simple_box.stl with 100x100x50mm dimensions

# Get help
python3 simple_box.py --help
python3 simple_box.py make_rounded_box --help
```

### Parameters:
- `--x`: Length in X direction (mm) - default: 100.0
- `--y`: Width in Y direction (mm) - default: 100.0
- `--z`: Height in Z direction (mm) - default: 50.0
- `--corner_radius`: Corner radius for rounded box (mm) - default: 5.0
- `--wall_thickness`: Wall thickness for hollow box (mm) - default: 3.0
- `--output`, `-o`: Output STL file - default: function-specific name

## Web Box Generator

The web box generator is more complex and has many parameters. You can still run it directly:

```bash
# Generate a simple hollow box (preview version)
python3 web_box_generator.py make_simple_hollow_box --L 160 --W 100 --H 60 --wall 3 --floor 3 --output simple_hollow_box.stl

# Generate a bottom box
python3 web_box_generator.py make_bottom_box --L 160 --W 100 --H 60 --wall 3 --floor 3 --output bottom_box.stl

# Generate a lid
python3 web_box_generator.py make_lid --L 160 --W 100 --wall 3 --lid_thickness 4 --output lid.stl
```

## Batch Processing Examples

### Generate Multiple Spheres:
```bash
#!/bin/bash
# generate_spheres.sh

for radius in 10 15 20 25 30; do
    python3 sphere_generator.py make_sphere --radius $radius --output "sphere_${radius}mm.stl"
done
```

### Generate Multiple Boxes:
```bash
#!/bin/bash
# generate_boxes.sh

# Different sizes
python3 simple_box.py make_simple_box --x 50 --y 50 --z 50 --output "cube_50mm.stl"
python3 simple_box.py make_simple_box --x 100 --y 50 --z 25 --output "box_100x50x25.stl"
python3 simple_box.py make_simple_box --x 200 --y 100 --z 50 --output "box_200x100x50.stl"

# Different corner radii
for radius in 2 5 10 15; do
    python3 simple_box.py make_rounded_box --x 100 --y 100 --z 50 --corner_radius $radius --output "rounded_box_r${radius}mm.stl"
done
```

## Integration with Scripts

### Python Integration:
```python
import subprocess
import os

def generate_sphere(radius, output_file):
    """Generate a sphere using direct module execution"""
    cmd = [
        'python3', 'sphere_generator.py',
        'make_sphere',
        '--radius', str(radius),
        '--output', output_file
    ]
    
    result = subprocess.run(cmd, cwd='/home/vova/GIT/vovastl_src/app/moduls')
    return result.returncode == 0

# Usage
generate_sphere(20, "my_sphere.stl")
```

### Shell Script Integration:
```bash
#!/bin/bash
# generate_custom_models.sh

MODULES_DIR="/home/vova/GIT/vovastl_src/app/moduls"
cd "$MODULES_DIR"

# Generate a custom set of models
python3 sphere_generator.py make_sphere --radius 15 --output "sphere_15mm.stl"
python3 simple_box.py make_rounded_box --x 80 --y 60 --z 40 --corner_radius 8 --output "rounded_box_80x60x40.stl"
python3 simple_box.py make_hollow_box --x 120 --y 80 --z 60 --wall_thickness 4 --output "hollow_box_120x80x60.stl"

echo "✅ All models generated successfully!"
```

## File Output

- **Location**: Files are created in the current directory (usually `/home/vova/GIT/vovastl_src/app/moduls`)
- **Format**: STL files with high resolution (tol=0.01, ang=0.05)
- **Naming**: Use `--output` to specify custom names, or use defaults
- **Size**: File sizes vary based on complexity and resolution

## Troubleshooting

### Common Issues:

1. **Module not found**: Make sure you're in the correct directory (`/home/vova/GIT/vovastl_src/app/moduls`)

2. **CadQuery not available**: Make sure CadQuery is installed and working

3. **Permission errors**: Make sure you have write permissions in the current directory

4. **Parameter errors**: Use `--help` to see available parameters for each function

### Getting Help:

```bash
# General help
python3 sphere_generator.py --help

# Function-specific help
python3 sphere_generator.py make_sphere --help
python3 simple_box.py make_rounded_box --help
```

## Advantages of Direct Execution

1. **No Web Interface**: Generate models without starting the web server
2. **Scripting**: Easy to integrate with batch processing and automation
3. **Testing**: Test individual modules and functions independently
4. **Performance**: Direct execution without web overhead
5. **Flexibility**: Full control over all parameters and output options
