#!/usr/bin/env python3
"""
Flask web app that generates parametric “Rugged Box” STL files (bottom + lid)
using CadQuery, and serves an in-browser 3D preview via Three.js (STLLoader).

Run:
  pip install flask cadquery
  python app.py
Then open http://127.0.0.1:5000
"""

from __future__ import annotations
import math
from io import BytesIO
from flask import Flask, request, Response, send_file
import cadquery as cq

app = Flask(__name__)

# -----------------------------
# CadQuery modeling functions
# -----------------------------

def make_simple_hollow_box(inner_len, inner_wid, inner_h, wall=3.0, floor=3.0, corner_fillet=4.0, rim_height=6.0):
    """
    Creates a simple hollow box for preview - no bosses, tongue, or other features
    Just a basic hollow box to show the interior space clearly
    """
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
    Creates the bottom box:
    - Start with outer shell with fillets
    - Hollow out to create inner volume + upper rim
    - Add sealing tongue on the rim
    - Add bosses for screws + pilot holes
    - Optional: strengthening ribs
    """
    outer_len = inner_len + 2 * wall
    outer_wid = inner_wid + 2 * wall
    outer_h   = floor + inner_h + rim_height

    # Outer body
    body = (
        cq.Workplane("XY")
        .box(outer_len, outer_wid, outer_h, centered=(True, True, False))
    )
    if corner_fillet > 0:
        body = body.edges("|Z").fillet(corner_fillet)

    # Hollow out - leave floor + walls + upper rim
    cavity_h = inner_h + rim_height
    inner = (
        cq.Workplane("XY")
        .box(inner_len, inner_wid, cavity_h, centered=(True, True, False))
        .translate((0, 0, floor))
    )
    body = body.cut(inner)

    # Sealing tongue (tongue) - protrudes from rim inward
    # Only add tongue for larger boxes to preserve interior space
    if inner_len > 60 and inner_wid > 40:
        tongue_len = inner_len - 2 * tongue_clearance
        tongue_wid = inner_wid - 2 * tongue_clearance
        tongue = (
            cq.Workplane("XY")
            .box(tongue_len, tongue_wid, tongue_height, centered=(True, True, False))
            .translate((0, 0, floor + inner_h))  # at top of inner cavity
        )
        # Break corners slightly on tongue to prevent friction
        tongue = tongue.edges("|Z").fillet(min(0.6, max(0.0, corner_fillet/4)))
        body = body.union(tongue)

    # Bosses for corners (bottom): four bosses at inner corners, with pilot hole
    # Make bosses smaller and position them better to preserve interior space
    boss_offset_x = inner_len/2 - 8  # Closer to walls but still safe
    boss_offset_y = inner_wid/2 - 8
    boss_centers = [
        (+boss_offset_x, +boss_offset_y),
        (+boss_offset_x, -boss_offset_y),
        (-boss_offset_x, +boss_offset_y),
        (-boss_offset_x, -boss_offset_y),
    ]
    
    # Only add bosses if the box is large enough
    if inner_len > 80 and inner_wid > 60:
        bosses = cq.Workplane("XY")
        for (x, y) in boss_centers:
            bosses = bosses.union(
                cq.Workplane("XY")
                .workplane(offset=floor)
                .center(x, y)
                .cylinder(boss_h, boss_outer_d/2.0)
            )
        body = body.union(bosses)

        # Pilot holes in bosses (for M3 plastic threading or hot insert after drilling)
        for (x, y) in boss_centers:
            pilot_hole = (
                cq.Workplane("XY")
                .workplane(offset=floor)
                .center(x, y)
                .cylinder(boss_h+1, boss_core_d/2.0)
            )
            body = body.cut(pilot_hole)

    # Optional strengthening ribs on floor
    if ribs:
        # Rib grid along X and Y
        # Along X
        y = -inner_wid/2 + rib_pitch
        while y < inner_wid/2 - rib_pitch/2:
            rib = (
                cq.Workplane("XY")
                .workplane(offset=floor + 0.01)
                .center(0, y)
                .rect(inner_len - 2*8, rib_thickness)
                .extrude( min(8.0, inner_h/3) )
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
                .rect(rib_thickness, inner_wid - 2*8)
                .extrude( min(8.0, inner_h/3) )
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
    - Plate with lid_thickness thickness with outer rim (overhang) for clean seating
    - Seal groove (groove) matching the bottom tongue
    - Countersunk screw holes in four corners
    """
    outer_len = inner_len + 2 * (wall + overhang)
    outer_wid = inner_wid + 2 * (wall + overhang)
    height    = lid_thickness + wall  # including margin for seal groove

    lid = (
        cq.Workplane("XY")
        .box(outer_len, outer_wid, height, centered=(True, True, False))
    )
    if corner_fillet > 0:
        lid = lid.edges("|Z").fillet(corner_fillet)

    # Hollow out to create "cap" - that sits on box walls
    inner_cap_len = inner_len + 2 * wall + 0.3  # small tolerance
    inner_cap_wid = inner_wid + 2 * wall + 0.3
    inner_cap_h   = height - lid_thickness + 0.2

    cavity = (
        cq.Workplane("XY")
        .box(inner_cap_len, inner_cap_wid, inner_cap_h, centered=(True, True, False))
        .translate((0, 0, lid_thickness))  # leave top plate with lid_thickness thickness
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
    # Set positions relative to lid rim
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


def export_stl_bytes(solid: cq.Workplane, tol=0.02, ang=0.2) -> bytes:
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

# -----------------------------
# Web routes
# -----------------------------

@app.route('/')
def index():
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🔧 Rugged Box Generator</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/STLLoader.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .main-container {
                display: flex;
                gap: 20px;
                max-width: 1400px;
                margin: 0 auto;
            }
            .form-container {
                flex: 1;
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                max-width: 500px;
            }
            .preview-container {
                flex: 1;
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                min-height: 600px;
            }
            .preview-window {
                width: 100%;
                height: 500px;
                border: 2px solid #ddd;
                border-radius: 5px;
                background: #f9f9f9;
                position: relative;
            }
            .preview-controls {
                display: flex;
                gap: 10px;
                margin-bottom: 15px;
                flex-wrap: wrap;
            }
            .preview-btn {
                padding: 8px 16px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 14px;
                transition: background-color 0.3s;
            }
            .preview-btn.active {
                background-color: #4CAF50;
                color: white;
            }
            .preview-btn:not(.active) {
                background-color: #e0e0e0;
                color: #666;
            }
            .preview-btn:hover {
                background-color: #45a049;
                color: white;
            }
            .preview-info {
                font-size: 12px;
                color: #666;
                margin-top: 10px;
                text-align: center;
            }
            h1 {
                color: #333;
                text-align: center;
                margin-bottom: 30px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
                color: #555;
            }
            input[type="number"], input[type="checkbox"], select {
                width: 100%;
                padding: 10px;
                border: 2px solid #ddd;
                border-radius: 5px;
                font-size: 16px;
                box-sizing: border-box;
            }
            input[type="number"]:focus, select:focus {
                border-color: #4CAF50;
                outline: none;
            }
            .checkbox-group {
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .checkbox-group input[type="checkbox"] {
                width: auto;
            }
            .button-group {
                display: flex;
                gap: 15px;
                margin-top: 30px;
            }
            button {
                flex: 1;
                padding: 15px;
                font-size: 16px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                transition: background-color 0.3s;
            }
            .btn-bottom {
                background-color: #4CAF50;
                color: white;
            }
            .btn-bottom:hover {
                background-color: #45a049;
            }
            .btn-lid {
                background-color: #2196F3;
                color: white;
            }
            .btn-lid:hover {
                background-color: #1976D2;
            }
            .btn-both {
                background-color: #FF9800;
                color: white;
            }
            .btn-both:hover {
                background-color: #F57C00;
            }
            .btn-reset {
                background-color: #9E9E9E;
                color: white;
            }
            .btn-reset:hover {
                background-color: #757575;
            }
            .section {
                margin-bottom: 30px;
                padding: 20px;
                background-color: #f9f9f9;
                border-radius: 5px;
            }
            .section h3 {
                margin-top: 0;
                color: #333;
                border-bottom: 2px solid #4CAF50;
                padding-bottom: 10px;
            }
            .help-text {
                font-size: 12px;
                color: #666;
                margin-top: 5px;
            }
            .loading {
                display: none;
                text-align: center;
                margin: 20px 0;
            }
            .spinner {
                border: 4px solid #f3f3f3;
                border-top: 4px solid #4CAF50;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            /* Responsive design */
            @media (max-width: 1200px) {
                .main-container {
                    flex-direction: column;
                }
                .form-container, .preview-container {
                    max-width: none;
                }
            }
            
            @media (max-width: 768px) {
                body {
                    padding: 10px;
                }
                .form-container, .preview-container {
                    padding: 20px;
                }
                .preview-window {
                    height: 400px;
                }
                .button-group {
                    flex-direction: column;
                }
                .preview-controls {
                    flex-direction: column;
                }
            }
        </style>
    </head>
    <body>
        <div class="main-container">
            <div class="form-container">
                <h1>🔧 Rugged Box Generator</h1>
                
                <form id="boxForm">
                <div class="section">
                    <h3>📏 Basic Dimensions</h3>
                    <div class="form-group">
                        <label for="inner_length">Inner Length (mm):</label>
                        <input type="number" id="inner_length" name="L" value="160" min="10" max="1000" step="0.1" required>
                        <div class="help-text">Length of the inner cavity</div>
                    </div>
                    <div class="form-group">
                        <label for="inner_width">Inner Width (mm):</label>
                        <input type="number" id="inner_width" name="W" value="100" min="10" max="1000" step="0.1" required>
                        <div class="help-text">Width of the inner cavity</div>
                    </div>
                    <div class="form-group">
                        <label for="inner_height">Inner Height (mm):</label>
                        <input type="number" id="inner_height" name="H" value="60" min="5" max="500" step="0.1" required>
                        <div class="help-text">Height of the inner cavity</div>
                    </div>
                </div>

                <div class="section">
                    <h3>🏗️ Wall & Structure</h3>
                    <div class="form-group">
                        <label for="wall_thickness">Wall Thickness (mm):</label>
                        <input type="number" id="wall_thickness" name="wall" value="3.0" min="1" max="20" step="0.1">
                        <div class="help-text">Thickness of the side walls</div>
                    </div>
                    <div class="form-group">
                        <label for="floor_thickness">Floor Thickness (mm):</label>
                        <input type="number" id="floor_thickness" name="floor" value="3.0" min="1" max="20" step="0.1">
                        <div class="help-text">Thickness of the bottom floor</div>
                    </div>
                    <div class="form-group">
                        <label for="corner_fillet">Corner Fillet (mm):</label>
                        <input type="number" id="corner_fillet" name="corner_fillet" value="4.0" min="0" max="20" step="0.1">
                        <div class="help-text">Radius of corner rounding</div>
                    </div>
                </div>

                <div class="section">
                    <h3>🔒 Sealing & Fit</h3>
                    <div class="form-group">
                        <label for="rim_height">Rim Height (mm):</label>
                        <input type="number" id="rim_height" name="rim_height" value="6.0" min="2" max="20" step="0.1">
                        <div class="help-text">Height of the sealing rim on bottom</div>
                    </div>
                    <div class="form-group">
                        <label for="tongue_height">Tongue Height (mm):</label>
                        <input type="number" id="tongue_height" name="tongue_height" value="2.2" min="1" max="10" step="0.1">
                        <div class="help-text">Height of the sealing tongue</div>
                    </div>
                    <div class="form-group">
                        <label for="tongue_clearance">Tongue Clearance (mm):</label>
                        <input type="number" id="tongue_clearance" name="tongue_clearance" value="0.2" min="0" max="2" step="0.05">
                        <div class="help-text">Clearance between tongue and groove</div>
                    </div>
                    <div class="form-group">
                        <label for="groove_depth">Groove Depth (mm):</label>
                        <input type="number" id="groove_depth" name="groove_depth" value="2.4" min="1" max="10" step="0.1">
                        <div class="help-text">Depth of the sealing groove in lid</div>
                    </div>
                </div>

                <div class="section">
                    <h3>🔧 Lid Settings</h3>
                    <div class="form-group">
                        <label for="lid_thickness">Lid Thickness (mm):</label>
                        <input type="number" id="lid_thickness" name="lid_thickness" value="4.0" min="2" max="20" step="0.1">
                        <div class="help-text">Thickness of the lid top</div>
                    </div>
                    <div class="form-group">
                        <label for="overhang">Overhang (mm):</label>
                        <input type="number" id="overhang" name="overhang" value="2.0" min="0" max="10" step="0.1">
                        <div class="help-text">Overhang of lid over box walls</div>
                    </div>
                </div>

                <div class="section">
                    <h3>⚙️ Advanced Options</h3>
                    <div class="form-group">
                        <div class="checkbox-group">
                            <input type="checkbox" id="ribs" name="ribs">
                            <label for="ribs">Add Internal Ribs</label>
                        </div>
                        <div class="help-text">Add internal strengthening ribs to the bottom</div>
                    </div>
                </div>

                <div class="loading" id="loading">
                    <div class="spinner"></div>
                    <p>Generating STL file...</p>
                </div>

                <div class="button-group">
                    <button type="button" class="btn-bottom" onclick="generateSTL('bottom')">
                        📦 Generate Bottom
                    </button>
                    <button type="button" class="btn-lid" onclick="generateSTL('lid')">
                        🔒 Generate Lid
                    </button>
                    <button type="button" class="btn-both" onclick="generateBoth()">
                        📦🔒 Generate Both
                    </button>
                </div>
                
                <div class="button-group" style="margin-top: 15px;">
                    <button type="button" class="btn-reset" onclick="resetForm()">
                        🔄 Reset to Defaults
                    </button>
                </div>
            </form>
            </div>
            
            <div class="preview-container">
                <h2>👁️ 3D Preview</h2>
                <div class="preview-controls">
                    <button class="preview-btn active" onclick="showPreview('bottom')">📦 Bottom</button>
                    <button class="preview-btn" onclick="showPreview('lid')">🔒 Lid</button>
                    <button class="preview-btn" onclick="showPreview('both')">📦🔒 Both</button>
                    <button class="preview-btn" onclick="updatePreview()">🔄 Refresh</button>
                    <button class="preview-btn" onclick="toggleWireframe()">🔲 Wireframe</button>
                </div>
                <div id="preview-window" class="preview-window">
                    <div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #666;">
                        Click "Refresh" to generate preview
                    </div>
                </div>
                <div class="preview-info">
                    <p>Use mouse to rotate, scroll to zoom, right-click to pan</p>
                    <p id="preview-status">Ready to preview</p>
                </div>
            </div>
        </div>

        <script>
            // Global variables for 3D preview
            let scene, camera, renderer, controls;
            let currentPreview = 'bottom';
            let wireframeMode = false;
            let currentMeshes = [];
            
            function initPreview() {
                const container = document.getElementById('preview-window');
                const width = container.clientWidth;
                const height = container.clientHeight;
                
                // Create scene
                scene = new THREE.Scene();
                scene.background = new THREE.Color(0xf0f0f0);
                
                // Create camera
                camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
                camera.position.set(50, 50, 50);
                
                // Create renderer
                renderer = new THREE.WebGLRenderer({ antialias: true });
                renderer.setSize(width, height);
                renderer.shadowMap.enabled = true;
                renderer.shadowMap.type = THREE.PCFSoftShadowMap;
                
                // Clear container and add renderer
                container.innerHTML = '';
                container.appendChild(renderer.domElement);
                
                // Add controls
                controls = new THREE.OrbitControls(camera, renderer.domElement);
                controls.enableDamping = true;
                controls.dampingFactor = 0.05;
                controls.enableZoom = true;
                controls.enablePan = true;
                
                // Add lighting
                const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
                scene.add(ambientLight);
                
                const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
                directionalLight.position.set(50, 50, 50);
                directionalLight.castShadow = true;
                directionalLight.shadow.mapSize.width = 2048;
                directionalLight.shadow.mapSize.height = 2048;
                scene.add(directionalLight);
                
                // Start render loop
                animate();
            }
            
            function animate() {
                requestAnimationFrame(animate);
                controls.update();
                renderer.render(scene, camera);
            }
            
            function showPreview(part) {
                currentPreview = part;
                
                // Update button states
                document.querySelectorAll('.preview-btn').forEach(btn => {
                    btn.classList.remove('active');
                });
                event.target.classList.add('active');
                
                updatePreview();
            }
            
            function updatePreview() {
                const statusEl = document.getElementById('preview-status');
                statusEl.textContent = 'Generating preview...';
                
                // Get form data
                const form = document.getElementById('boxForm');
                const formData = new FormData(form);
                
                const params = new URLSearchParams();
                for (let [key, value] of formData.entries()) {
                    if (key === 'ribs') {
                        if (value) params.append(key, 'true');
                    } else {
                        params.append(key, value);
                    }
                }
                
                // Clear existing models
                currentMeshes.forEach(mesh => {
                    scene.remove(mesh);
                });
                currentMeshes = [];
                
                // Re-add lighting
                const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
                scene.add(ambientLight);
                
                const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
                directionalLight.position.set(50, 50, 50);
                directionalLight.castShadow = true;
                scene.add(directionalLight);
                
                if (currentPreview === 'both') {
                    // Load both bottom and lid
                    loadSTLModel('/preview?' + params.toString() + '&part=bottom', [0, 0, 0], 0x4CAF50, () => {
                        loadSTLModel('/preview?' + params.toString() + '&part=lid', [0, 0, 30], 0x2196F3, () => {
                            statusEl.textContent = 'Preview ready - Both parts loaded';
                        });
                    });
                } else {
                    // Load single part
                    const color = currentPreview === 'bottom' ? 0x4CAF50 : 0x2196F3;
                    loadSTLModel('/preview?' + params.toString() + '&part=' + currentPreview, [0, 0, 0], color, () => {
                        statusEl.textContent = `Preview ready - ${currentPreview} loaded`;
                    });
                }
            }
            
            function loadSTLModel(url, position, color, callback) {
                const loader = new THREE.STLLoader();
                loader.load(url, function(geometry) {
                    // Create both solid and wireframe materials for better visualization
                    const solidMaterial = new THREE.MeshPhongMaterial({ 
                        color: color,
                        transparent: true,
                        opacity: 0.7,
                        side: THREE.DoubleSide
                    });
                    
                    const wireframeMaterial = new THREE.MeshBasicMaterial({ 
                        color: 0x000000,
                        wireframe: true,
                        transparent: true,
                        opacity: 0.3
                    });
                    
                    // Create solid mesh
                    const solidMesh = new THREE.Mesh(geometry, solidMaterial);
                    solidMesh.position.set(position[0], position[1], position[2]);
                    solidMesh.castShadow = true;
                    solidMesh.receiveShadow = true;
                    
                    // Create wireframe mesh
                    const wireframeMesh = new THREE.Mesh(geometry, wireframeMaterial);
                    wireframeMesh.position.set(position[0], position[1], position[2]);
                    
                    // Center both models
                    geometry.computeBoundingBox();
                    const center = geometry.boundingBox.getCenter(new THREE.Vector3());
                    solidMesh.position.sub(center);
                    wireframeMesh.position.sub(center);
                    
                    scene.add(solidMesh);
                    scene.add(wireframeMesh);
                    
                    // Store references for wireframe toggle
                    currentMeshes.push(solidMesh, wireframeMesh);
                    
                    // Auto-fit camera
                    const box = new THREE.Box3().setFromObject(solidMesh);
                    const size = box.getSize(new THREE.Vector3());
                    const maxDim = Math.max(size.x, size.y, size.z);
                    const fov = camera.fov * (Math.PI / 180);
                    let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2));
                    cameraZ *= 1.5; // Add some margin
                    camera.position.set(cameraZ, cameraZ, cameraZ);
                    controls.target.set(0, 0, 0);
                    controls.update();
                    
                    if (callback) callback();
                }, function(progress) {
                    // Progress callback
                }, function(error) {
                    console.error('Error loading STL:', error);
                    document.getElementById('preview-status').textContent = 'Error loading preview';
                });
            }

            function showLoading() {
                document.getElementById('loading').style.display = 'block';
            }

            function hideLoading() {
                document.getElementById('loading').style.display = 'none';
            }

            function generateSTL(part) {
                showLoading();
                
                const form = document.getElementById('boxForm');
                const formData = new FormData(form);
                formData.append('part', part);
                
                const params = new URLSearchParams();
                for (let [key, value] of formData.entries()) {
                    if (key === 'ribs') {
                        if (value) params.append(key, 'true');
                    } else {
                        params.append(key, value);
                    }
                }
                
                const url = `/generate?${params.toString()}`;
                
                // Create a temporary link to download the file
                const link = document.createElement('a');
                link.href = url;
                link.download = `rugged_box_${part}.stl`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                setTimeout(hideLoading, 2000);
            }

            function generateBoth() {
                generateSTL('bottom');
                setTimeout(() => generateSTL('lid'), 1000);
            }
            
            function resetForm() {
                // Ask for confirmation before resetting
                if (confirm('Are you sure you want to reset all parameters to default values? This will clear all your current settings.')) {
                    // Reset all form fields to their default values
                    document.getElementById('inner_length').value = '160';
                    document.getElementById('inner_width').value = '100';
                    document.getElementById('inner_height').value = '60';
                    document.getElementById('wall_thickness').value = '3.0';
                    document.getElementById('floor_thickness').value = '3.0';
                    document.getElementById('corner_fillet').value = '4.0';
                    document.getElementById('rim_height').value = '6.0';
                    document.getElementById('tongue_height').value = '2.2';
                    document.getElementById('tongue_clearance').value = '0.2';
                    document.getElementById('groove_depth').value = '2.4';
                    document.getElementById('lid_thickness').value = '4.0';
                    document.getElementById('overhang').value = '2.0';
                    document.getElementById('ribs').checked = false;
                    
                    // Update preview with new values
                    if (scene) {
                        updatePreview();
                    }
                    
                    // Show success message
                    const statusEl = document.getElementById('preview-status');
                    statusEl.textContent = 'Parameters reset to defaults';
                    setTimeout(() => {
                        statusEl.textContent = 'Ready to preview';
                    }, 2000);
                }
            }
            
            function toggleWireframe() {
                wireframeMode = !wireframeMode;
                
                // Toggle visibility of solid and wireframe meshes
                currentMeshes.forEach((mesh, index) => {
                    if (index % 2 === 0) { // Solid meshes (even indices)
                        mesh.visible = !wireframeMode;
                    } else { // Wireframe meshes (odd indices)
                        mesh.visible = wireframeMode;
                    }
                });
                
                // Update button text
                const button = event.target;
                if (wireframeMode) {
                    button.textContent = '🔳 Solid';
                } else {
                    button.textContent = '🔲 Wireframe';
                }
            }

            // Add some interactivity
            document.addEventListener('DOMContentLoaded', function() {
                // Initialize 3D preview
                initPreview();
                
                const inputs = document.querySelectorAll('input[type="number"]');
                inputs.forEach(input => {
                    input.addEventListener('input', function() {
                        if (this.value < this.min) this.value = this.min;
                        if (this.value > this.max) this.value = this.max;
                    });
                });
                
                // Auto-update preview when form changes
                const form = document.getElementById('boxForm');
                form.addEventListener('input', function() {
                    // Debounce the preview update
                    clearTimeout(window.previewTimeout);
                    window.previewTimeout = setTimeout(() => {
                        if (scene) updatePreview();
                    }, 1000);
                });
            });
        </script>
    </body>
    </html>
    """
    return Response(html, mimetype='text/html')


@app.route('/preview')
def preview():
    """Generate STL for preview (not download) - simplified for better visualization"""
    try:
        # Basic dimensions
        L = float(request.args.get('L', 160))
        W = float(request.args.get('W', 100))
        H = float(request.args.get('H', 60))
        part = request.args.get('part', 'bottom')
        
        # Wall and structure parameters
        wall = float(request.args.get('wall', 3.0))
        floor = float(request.args.get('floor', 3.0))
        corner_fillet = float(request.args.get('corner_fillet', 4.0))
        
        # Sealing parameters
        rim_height = float(request.args.get('rim_height', 6.0))
        tongue_height = float(request.args.get('tongue_height', 2.2))
        tongue_clearance = float(request.args.get('tongue_clearance', 0.2))
        groove_depth = float(request.args.get('groove_depth', 2.4))
        
        # Lid parameters
        lid_thickness = float(request.args.get('lid_thickness', 4.0))
        overhang = float(request.args.get('overhang', 2.0))
        
        # Advanced options
        ribs = request.args.get('ribs') == 'true'
        
        # Validate basic parameters
        if L <= 0 or W <= 0 or H <= 0:
            return Response("Dimensions must be positive", status=400)
        if L > 1000 or W > 1000 or H > 1000:
            return Response("Dimensions too large (max 1000mm)", status=400)
        if part not in ['bottom', 'lid']:
            return Response("Part must be 'bottom' or 'lid'", status=400)
            
    except ValueError as e:
        return Response(f"Invalid parameters: {str(e)}", status=400)
    except Exception as e:
        return Response(f"Parameter error: {str(e)}", status=400)

    try:
        if part == 'bottom':
            # Create simplified preview version - just basic hollow box
            solid = make_simple_hollow_box(L, W, H, wall, floor, corner_fillet, rim_height)
        elif part == 'lid':
            solid = make_lid(
                L, W,
                wall=wall,
                lid_thickness=lid_thickness,
                overhang=overhang,
                corner_fillet=corner_fillet,
                groove_depth=groove_depth,
                groove_clearance=tongue_clearance
            )
        else:
            return Response("Part must be 'bottom' or 'lid'", status=400)

        # Export with lower resolution for faster preview
        data = export_stl_bytes(solid, tol=0.02, ang=0.1)
        return send_file(BytesIO(data), mimetype='application/sla')
        
    except Exception as e:
        return Response(f"STL generation failed: {str(e)}", status=500)


@app.route('/generate')
def generate():
    try:
        # Basic dimensions
        L = float(request.args.get('L', 160))
        W = float(request.args.get('W', 100))
        H = float(request.args.get('H', 60))
        part = request.args.get('part', 'bottom')
        
        # Wall and structure parameters
        wall = float(request.args.get('wall', 3.0))
        floor = float(request.args.get('floor', 3.0))
        corner_fillet = float(request.args.get('corner_fillet', 4.0))
        
        # Sealing parameters
        rim_height = float(request.args.get('rim_height', 6.0))
        tongue_height = float(request.args.get('tongue_height', 2.2))
        tongue_clearance = float(request.args.get('tongue_clearance', 0.2))
        groove_depth = float(request.args.get('groove_depth', 2.4))
        
        # Lid parameters
        lid_thickness = float(request.args.get('lid_thickness', 4.0))
        overhang = float(request.args.get('overhang', 2.0))
        
        # Advanced options
        ribs = request.args.get('ribs') == 'true'
        
        # Validate basic parameters
        if L <= 0 or W <= 0 or H <= 0:
            return Response("Dimensions must be positive", status=400)
        if L > 1000 or W > 1000 or H > 1000:
            return Response("Dimensions too large (max 1000mm)", status=400)
        if part not in ['bottom', 'lid']:
            return Response("Part must be 'bottom' or 'lid'", status=400)
            
    except ValueError as e:
        return Response(f"Invalid parameters: {str(e)}", status=400)
    except Exception as e:
        return Response(f"Parameter error: {str(e)}", status=400)

    try:
        if part == 'bottom':
            solid = make_bottom_box(
                L, W, H,
                wall=wall,
                floor=floor,
                corner_fillet=corner_fillet,
                rim_height=rim_height,
                tongue_height=tongue_height,
                tongue_clearance=tongue_clearance,
                ribs=ribs
            )
        elif part == 'lid':
            solid = make_lid(
                L, W,
                wall=wall,
                lid_thickness=lid_thickness,
                overhang=overhang,
                corner_fillet=corner_fillet,
                groove_depth=groove_depth,
                groove_clearance=tongue_clearance
            )
        else:
            return Response("Part must be 'bottom' or 'lid'", status=400)

        data = export_stl_bytes(solid)
        fname = f"rugged_box_{part}.stl"
        return send_file(BytesIO(data), as_attachment=True, download_name=fname, mimetype='application/sla')
        
    except Exception as e:
        return Response(f"STL generation failed: {str(e)}", status=500)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
