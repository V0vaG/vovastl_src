#!/usr/bin/env python3
"""
Module Discovery System
Scans the moduls folder and extracts function information for dynamic UI generation
"""

import os
import inspect
import importlib.util
from pathlib import Path
from typing import Dict, List, Any, Optional

def discover_modules(moduls_dir: str = "moduls") -> Dict[str, Dict[str, Any]]:
    """
    Discover all Python modules in the moduls directory and extract function information
    
    Returns:
        Dict mapping module names to their function information
    """
    modules_info = {}
    moduls_path = Path(moduls_dir)
    
    if not moduls_path.exists():
        return modules_info
    
    # Scan for Python files
    for py_file in moduls_path.glob("*.py"):
        if py_file.name.startswith("__"):
            continue
            
        module_name = py_file.stem
        try:
            # Load the module
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if spec is None or spec.loader is None:
                continue
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Extract function information
            functions_info = extract_functions_info(module)
            
            if functions_info:
                modules_info[module_name] = {
                    "name": module_name,
                    "display_name": format_module_name(module_name),
                    "description": (getattr(module, "__doc__", "") or "").strip() or f"Module: {module_name}",
                    "functions": functions_info
                }
                
        except Exception as e:
            print(f"Warning: Could not load module {module_name}: {e}")
            continue
    
    return modules_info

def extract_functions_info(module) -> Dict[str, Dict[str, Any]]:
    """
    Extract information about functions in a module that are suitable for model generation
    
    Returns:
        Dict mapping function names to their parameter information
    """
    functions_info = {}
    
    # Look for functions that start with 'make_' (model generation functions)
    for name, obj in inspect.getmembers(module):
        if (inspect.isfunction(obj) and 
            name.startswith('make_') and 
            not name.startswith('__')):
            
            try:
                sig = inspect.signature(obj)
                params_info = {}
                
                for param_name, param in sig.parameters.items():
                    param_info = {
                        "name": param_name,
                        "type": get_parameter_type(param),
                        "default": param.default if param.default != inspect.Parameter.empty else None,
                        "required": param.default == inspect.Parameter.empty,
                        "description": get_parameter_description(obj, param_name)
                    }
                    params_info[param_name] = param_info
                
                functions_info[name] = {
                    "name": name,
                    "display_name": format_function_name(name),
                    "description": (obj.__doc__ or "").strip() or f"Function: {name}",
                    "parameters": params_info
                }
                
            except Exception as e:
                print(f"Warning: Could not extract info for function {name}: {e}")
                continue
    
    return functions_info

def get_parameter_type(param: inspect.Parameter) -> str:
    """
    Determine the parameter type for UI generation
    """
    if param.annotation != inspect.Parameter.empty:
        if param.annotation == bool:
            return "boolean"
        elif param.annotation in (int, float):
            return "number"
        elif param.annotation == str:
            return "text"
    
    # Infer from default value
    if param.default != inspect.Parameter.empty:
        if isinstance(param.default, bool):
            return "boolean"
        elif isinstance(param.default, (int, float)):
            return "number"
        elif isinstance(param.default, str):
            return "text"
    
    # Default to number for model generation parameters
    return "number"

def get_parameter_description(func, param_name: str) -> str:
    """
    Extract parameter description from function docstring
    """
    if not func.__doc__:
        return f"Parameter: {param_name}"
    
    # Simple extraction - look for parameter descriptions
    lines = func.__doc__.split('\n')
    for line in lines:
        if param_name in line and ':' in line:
            return line.split(':', 1)[1].strip()
    
    return f"Parameter: {param_name}"

def format_module_name(module_name: str) -> str:
    """
    Format module name for display
    """
    return module_name.replace('_', ' ').title()

def format_function_name(func_name: str) -> str:
    """
    Format function name for display
    """
    # Remove 'make_' prefix and format
    display_name = func_name.replace('make_', '').replace('_', ' ').title()
    return display_name

def get_module_functions(module_name: str, moduls_dir: str = "moduls") -> Optional[Dict[str, Any]]:
    """
    Get functions for a specific module
    """
    print(f"DEBUG: get_module_functions called with module_name={module_name}, moduls_dir={moduls_dir}")
    modules_info = discover_modules(moduls_dir)
    print(f"DEBUG: Available modules: {list(modules_info.keys())}")
    result = modules_info.get(module_name)
    print(f"DEBUG: Result for {module_name}: {result}")
    return result

def get_available_modules(moduls_dir: str = "moduls") -> List[Dict[str, str]]:
    """
    Get list of available modules for dropdown
    """
    modules_info = discover_modules(moduls_dir)
    return [
        {
            "value": name,
            "label": info["display_name"],
            "description": info["description"]
        }
        for name, info in modules_info.items()
    ]

# Test the discovery system
if __name__ == "__main__":
    print("Discovering modules...")
    modules = discover_modules()
    
    for module_name, module_info in modules.items():
        print(f"\nModule: {module_info['display_name']}")
        print(f"Description: {module_info['description']}")
        print("Functions:")
        
        for func_name, func_info in module_info['functions'].items():
            print(f"  - {func_info['display_name']}")
            print(f"    Parameters: {len(func_info['parameters'])}")
            
            for param_name, param_info in func_info['parameters'].items():
                required = "required" if param_info['required'] else "optional"
                default = f" (default: {param_info['default']})" if param_info['default'] is not None else ""
                print(f"      {param_name}: {param_info['type']} - {required}{default}")
