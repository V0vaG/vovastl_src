#!/usr/bin/env python3
"""Simple test script for CLI functionality"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test importing the CLI runner
try:
    from cli_runner import load_modules_config, list_available_modules
    print("✅ CLI runner imported successfully")
    
    # Test loading modules config
    config = load_modules_config()
    print(f"✅ Modules config loaded: {len(config.get('modules', {}))} modules found")
    
    # Test listing modules
    print("\n📋 Available modules:")
    list_available_modules()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
