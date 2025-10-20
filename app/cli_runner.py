#!/usr/bin/env python3
"""
Command Line Interface for STL Model Generation

This script allows you to run model generation functions manually from the command line.
It supports all modules and functions defined in the modules.json configuration.

Usage Examples:
    # Generate a simple sphere
    python cli_runner.py sphere_generator make_sphere --radius 20 --output sphere_20mm.stl
    
    # Generate a hollow sphere
    python cli_runner.py sphere_generator make_hollow_sphere --radius 25 --wall_thickness 3 --output hollow_sphere.stl
    
    # Generate a simple box
    python cli_runner.py simple_box make_simple_box --x 100 --y 80 --z 50 --output simple_box.stl
    
    # Generate a rounded box
    python cli_runner.py simple_box make_rounded_box --x 100 --y 80 --z 50 --corner_radius 10 --output rounded_box.stl
    
    # Generate a hollow box
    python cli_runner.py simple_box make_hollow_box --x 100 --y 80 --z 50 --wall_thickness 5 --output hollow_box.stl
    
    # Generate a web box (bottom)
    python cli_runner.py web_box_generator make_bottom_box --L 160 --W 100 --H 60 --wall 3 --floor 3 --output web_box_bottom.stl
    
    # Generate a web box (lid)
    python cli_runner.py web_box_generator make_lid --L 160 --W 100 --wall 3 --lid_thickness 4 --output web_box_lid.stl

    # List available modules
    python cli_runner.py --list-modules
    
    # List functions for a specific module
    python cli_runner.py --list-functions sphere_generator
"""

import argparse
import sys
import os
import json
import tempfile
from pathlib import Path

# Add the current directory to Python path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def load_modules_config():
    """Load modules configuration from JSON file"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'moduls', 'modules.json')
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading modules config: {e}")
        return {"modules": {}}

def list_available_modules():
    """List all available modules"""
    config = load_modules_config()
    print("Available Modules:")
    print("=" * 50)
    
    for module_name, module_info in config.get("modules", {}).items():
        display_name = module_info.get("display_name", module_name)
        description = module_info.get("description", "No description")
        icon = module_info.get("icon", "🔧")
        print(f"{icon} {module_name}")
        print(f"   Display Name: {display_name}")
        print(f"   Description: {description}")
        print()

def list_module_functions(module_name):
    """List all functions for a specific module"""
    config = load_modules_config()
    modules = config.get("modules", {})
    
    if module_name not in modules:
        print(f"Error: Module '{module_name}' not found!")
        print("Available modules:")
        for name in modules.keys():
            print(f"  - {name}")
        return
    
    module_info = modules[module_name]
    display_name = module_info.get("display_name", module_name)
    print(f"Functions for Module: {display_name} ({module_name})")
    print("=" * 60)
    
    functions = module_info.get("functions", {})
    for func_name, func_info in functions.items():
        display_name = func_info.get("display_name", func_name)
        description = func_info.get("description", "No description")
        print(f"🔧 {func_name}")
        print(f"   Display Name: {display_name}")
        print(f"   Description: {description}")
        
        # Show parameters
        parameters = func_info.get("parameters", {})
        if parameters:
            print("   Parameters:")
            for param_name, param_info in parameters.items():
                param_type = param_info.get("type", "unknown")
                default = param_info.get("default", "none")
                label = param_info.get("label", param_name)
                help_text = param_info.get("help", "No help available")
                print(f"     --{param_name} ({param_type}): {label} (default: {default})")
                print(f"       {help_text}")
        print()

def generate_model(module_name, function_name, output_file, **kwargs):
    """Generate a model using the specified module and function"""
    try:
        # Import the module dynamically
        import importlib.util
        import sys
        
        module_path = os.path.join(os.path.dirname(__file__), 'moduls', f"{module_name}.py")
        if not os.path.exists(module_path):
            raise FileNotFoundError(f"Module file not found: {module_path}")
        
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load module {module_name}")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Get the function
        if not hasattr(module, function_name):
            raise AttributeError(f"Function {function_name} not found in module {module_name}")
        
        func = getattr(module, function_name)
        
        # Call the function with the provided parameters
        print(f"Generating {module_name}.{function_name} with parameters: {kwargs}")
        solid = func(**kwargs)
        
        # Export to STL
        if hasattr(module, 'export_stl_bytes'):
            # Use module's own export function
            data = module.export_stl_bytes(solid, tol=0.01, ang=0.05)
        else:
            # Fallback to web_box_generator export function
            try:
                from moduls.web_box_generator import export_stl_bytes
                data = export_stl_bytes(solid, tol=0.01, ang=0.05)
            except ImportError:
                raise ImportError("No export function available")
        
        # Write to file
        with open(output_file, 'wb') as f:
            f.write(data)
        
        print(f"✅ Model generated successfully: {output_file}")
        print(f"   File size: {len(data)} bytes")
        
    except Exception as e:
        print(f"❌ Error generating model: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Command Line Interface for STL Model Generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Main arguments
    parser.add_argument('module', nargs='?', help='Module name (e.g., sphere_generator, simple_box)')
    parser.add_argument('function', nargs='?', help='Function name (e.g., make_sphere, make_simple_box)')
    parser.add_argument('--output', '-o', help='Output STL file path')
    
    # List options
    parser.add_argument('--list-modules', action='store_true', help='List all available modules')
    parser.add_argument('--list-functions', help='List functions for a specific module')
    
    # Parse known args to handle dynamic parameters
    args, unknown = parser.parse_known_args()
    
    # Handle list options
    if args.list_modules:
        list_available_modules()
        return
    
    if args.list_functions:
        list_module_functions(args.list_functions)
        return
    
    # Validate required arguments for generation
    if not args.module or not args.function:
        print("Error: Module and function are required for generation")
        print("Use --list-modules to see available modules")
        print("Use --list-functions <module> to see available functions")
        sys.exit(1)
    
    if not args.output:
        # Generate default output filename
        args.output = f"{args.module}_{args.function}.stl"
    
    # Parse dynamic parameters from unknown args
    kwargs = {}
    i = 0
    while i < len(unknown):
        arg = unknown[i]
        if arg.startswith('--'):
            param_name = arg[2:]  # Remove '--'
            if i + 1 < len(unknown) and not unknown[i + 1].startswith('--'):
                # Parameter has a value
                value = unknown[i + 1]
                # Try to convert to appropriate type
                try:
                    # Try float first
                    kwargs[param_name] = float(value)
                except ValueError:
                    try:
                        # Try int
                        kwargs[param_name] = int(value)
                    except ValueError:
                        # Keep as string
                        kwargs[param_name] = value
                i += 2
            else:
                # Boolean flag
                kwargs[param_name] = True
                i += 1
        else:
            i += 1
    
    # Generate the model
    generate_model(args.module, args.function, args.output, **kwargs)

if __name__ == '__main__':
    main()
