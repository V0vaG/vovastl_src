#!/usr/bin/env python3
"""
Spear Generator Module
Creates simple spear models with customizable radius
"""

import cadquery as cq
import math

CADQUERY_AVAILABLE = True  # Assume CadQuery is available in this module's context

def make_spear(radius=5.0, length=200.0, tip_angle=30.0):
    """
    Creates a simple spear model
    
    Args:
        radius: Radius of the spear shaft (mm)
        length: Total length of the spear (mm)
        tip_angle: Angle of the spear tip in degrees
    
    Returns:
        CadQuery solid object
    """
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")
    
    # Calculate tip length based on angle
    tip_length = radius / math.tan(math.radians(tip_angle))
    
    # Create the shaft (cylindrical part)
    shaft_length = length - tip_length
    shaft = cq.Workplane("XY").cylinder(shaft_length, radius)
    
    # Create the tip (cone)
    tip = (
        cq.Workplane("XY")
        .workplane(offset=shaft_length)
        .cylinder(tip_length, radius)
        .faces(">Z")
        .workplane()
        .hole(0)  # Create a cone by making the top face a point
    )
    
    # Alternative approach for the tip - create a proper cone
    tip = (
        cq.Workplane("XY")
        .workplane(offset=shaft_length)
        .circle(radius)
        .workplane(offset=tip_length)
        .circle(0.1)  # Very small radius for the point
        .loft()
    )
    
    # Combine shaft and tip
    spear = shaft.union(tip)
    
    return spear

def make_spear_with_handle(radius=5.0, length=200.0, tip_angle=30.0, handle_length=50.0, handle_radius=8.0):
    """
    Creates a spear with a handle
    
    Args:
        radius: Radius of the spear shaft (mm)
        length: Length of the spear head (mm)
        tip_angle: Angle of the spear tip in degrees
        handle_length: Length of the handle (mm)
        handle_radius: Radius of the handle (mm)
    
    Returns:
        CadQuery solid object
    """
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")
    
    # Create the spear head
    spear_head = make_spear(radius, length, tip_angle)
    
    # Create the handle
    handle = (
        cq.Workplane("XY")
        .workplane(offset=-handle_length)
        .cylinder(handle_length, handle_radius)
    )
    
    # Combine spear head and handle
    complete_spear = spear_head.union(handle)
    
    return complete_spear

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
