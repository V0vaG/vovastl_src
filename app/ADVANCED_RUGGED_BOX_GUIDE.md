# Advanced Rugged Box Generator Guide

This guide explains how to use the new Advanced Rugged Box module that creates professional rugged boxes with hinges, latches, and reinforcement features.

## Overview

The Advanced Rugged Box module creates a complete rugged box system with:
- **Bottom Box**: Main container with hinge and latch mounting points
- **Lid**: Top cover with matching mounting points
- **Hinges**: Simple mechanical hinges for opening/closing
- **Latches**: Secure locking mechanism

## Features

### 🔧 Professional Design
- **Hinge Mounting Points**: Pre-designed mounting areas for hinges
- **Latch Mounting Points**: Secure latch attachment points
- **Reinforcement Ribs**: Internal structural reinforcement
- **Sealing Rim**: Water-resistant sealing system
- **Corner Rounding**: Professional rounded corners

### 📐 Customizable Dimensions
- **External Dimensions**: Length, width, height
- **Wall Thickness**: Adjustable wall and floor thickness
- **Corner Radius**: Customizable corner rounding
- **Sealing System**: Adjustable rim height and overhang

## Usage

### Web Interface

1. **Select Module**: Choose "Advanced Rugged Box" from the dropdown
2. **Select Function**: Choose from:
   - `make_bottom` - Create the bottom box
   - `make_lid` - Create the lid
   - `make_hinge` - Create hinges
   - `make_latch` - Create latches
3. **Adjust Parameters**: Set dimensions and features
4. **Generate**: Create preview and download STL files

### Command Line Interface

```bash
# Navigate to modules directory
cd /home/vova/GIT/vovastl_src/app/moduls

# Generate bottom box
python3 rugged_box_advanced.py make_bottom --length 200 --width 150 --height 80 --output bottom.stl

# Generate lid
python3 rugged_box_advanced.py make_lid --length 200 --width 150 --output lid.stl

# Generate hinges
python3 rugged_box_advanced.py make_hinge --output hinge.stl

# Generate latches
python3 rugged_box_advanced.py make_latch --output latch.stl
```

## Functions

### 1. Bottom Box (`make_bottom`)

Creates the main container with all mounting points and features.

**Parameters:**
- `length`: External length (mm) - default: 200.0
- `width`: External width (mm) - default: 150.0
- `height`: External height (mm) - default: 80.0
- `wall_thickness`: Side wall thickness (mm) - default: 4.0
- `floor_thickness`: Bottom floor thickness (mm) - default: 6.0
- `corner_radius`: Corner rounding radius (mm) - default: 8.0
- `rim_height`: Sealing rim height (mm) - default: 8.0

**Features:**
- Internal cavity with proper dimensions
- Hinge mounting points on the back
- Latch mounting points on the front
- Reinforcement ribs for structural strength
- Sealing rim for water resistance

### 2. Lid (`make_lid`)

Creates the top cover with matching mounting points.

**Parameters:**
- `length`: External length (mm) - default: 200.0
- `width`: External width (mm) - default: 150.0
- `lid_thickness`: Top thickness (mm) - default: 8.0
- `wall_thickness`: Side wall thickness (mm) - default: 4.0
- `corner_radius`: Corner rounding radius (mm) - default: 8.0
- `overhang`: Overhang over box walls (mm) - default: 3.0

**Features:**
- Sealing cavity for water resistance
- Hinge mounting points on the back
- Latch mounting points on the front
- Proper overhang for weather protection

### 3. Hinge (`make_hinge`)

Creates simple mechanical hinges for the box.

**Parameters:**
- `length`: Hinge length (mm) - default: 30.0
- `width`: Hinge width (mm) - default: 15.0
- `thickness`: Material thickness (mm) - default: 3.0
- `pin_diameter`: Hinge pin diameter (mm) - default: 4.0

**Features:**
- Multiple knuckles for strength
- Pin hole for metal pin
- Mounting holes for attachment
- Professional appearance

### 4. Latch (`make_latch`)

Creates a secure locking mechanism.

**Parameters:**
- `length`: Latch length (mm) - default: 40.0
- `width`: Latch width (mm) - default: 20.0
- `thickness`: Material thickness (mm) - default: 4.0
- `catch_depth`: Catch mechanism depth (mm) - default: 8.0

**Features:**
- Catch mechanism for secure locking
- Mounting holes for attachment
- Robust design for outdoor use

## Complete Box Assembly

### Step 1: Generate All Parts

```bash
# Generate all components for a 200x150x80mm box
python3 rugged_box_advanced.py make_bottom --length 200 --width 150 --height 80 --output rugged_bottom.stl
python3 rugged_box_advanced.py make_lid --length 200 --width 150 --output rugged_lid.stl
python3 rugged_box_advanced.py make_hinge --output hinge.stl
python3 rugged_box_advanced.py make_latch --output latch.stl
```

### Step 2: Print Components

**Recommended Settings:**
- **Layer Height**: 0.2mm
- **Infill**: 20-30%
- **Supports**: Minimal (mostly for overhangs)
- **Material**: PLA, PETG, or ABS

**Print Order:**
1. Bottom box (largest part)
2. Lid
3. Hinges (2x)
4. Latch

### Step 3: Assembly

**Required Hardware:**
- **Hinge Pins**: 4mm diameter metal rods (2x per hinge)
- **Screws**: M3 or M4 screws for mounting
- **Washers**: Small washers for screw heads

**Assembly Steps:**
1. **Install Hinges**: Attach hinges to back of box and lid
2. **Insert Pins**: Slide metal pins through hinge knuckles
3. **Install Latch**: Attach latch to front of box
4. **Test Fit**: Ensure smooth opening/closing
5. **Final Assembly**: Tighten all screws

## Customization Examples

### Small Electronics Box
```bash
python3 rugged_box_advanced.py make_bottom --length 120 --width 80 --height 40 --wall_thickness 3 --output small_bottom.stl
python3 rugged_box_advanced.py make_lid --length 120 --width 80 --lid_thickness 6 --output small_lid.stl
```

### Large Storage Box
```bash
python3 rugged_box_advanced.py make_bottom --length 300 --width 200 --height 120 --wall_thickness 6 --floor_thickness 8 --output large_bottom.stl
python3 rugged_box_advanced.py make_lid --length 300 --width 200 --lid_thickness 10 --output large_lid.stl
```

### Heavy-Duty Box
```bash
python3 rugged_box_advanced.py make_bottom --length 250 --width 180 --height 100 --wall_thickness 8 --floor_thickness 10 --corner_radius 12 --output heavy_bottom.stl
python3 rugged_box_advanced.py make_lid --length 250 --width 180 --lid_thickness 12 --wall_thickness 8 --output heavy_lid.stl
```

## Tips and Best Practices

### Design Considerations
- **Wall Thickness**: Use 4-6mm for standard boxes, 6-8mm for heavy-duty
- **Corner Radius**: Keep under 15mm for most 3D printers
- **Overhang**: 3-5mm provides good weather protection
- **Rim Height**: 6-10mm for effective sealing

### Printing Tips
- **Orientation**: Print bottom and lid flat for best results
- **Supports**: Minimal supports needed, mostly for overhangs
- **Infill**: 20-30% is sufficient for most applications
- **Material**: PETG recommended for outdoor use

### Assembly Tips
- **Test Fit**: Print one hinge first to test fit
- **Hardware**: Use stainless steel hardware for outdoor use
- **Sealing**: Add rubber gasket for water resistance
- **Finishing**: Sand mounting surfaces for better fit

## Troubleshooting

### Common Issues

1. **Hinges Don't Fit**: Check pin diameter and knuckle spacing
2. **Latch Too Tight**: Adjust catch depth parameter
3. **Poor Sealing**: Increase rim height and overhang
4. **Weak Structure**: Increase wall thickness and add more ribs

### Getting Help

```bash
# Get help for specific functions
python3 rugged_box_advanced.py make_bottom --help
python3 rugged_box_advanced.py make_lid --help
python3 rugged_box_advanced.py make_hinge --help
python3 rugged_box_advanced.py make_latch --help
```

## Applications

### Electronics Enclosures
- Raspberry Pi cases
- Arduino project boxes
- Sensor housings
- Control panels

### Outdoor Equipment
- Tool storage
- Camping gear
- Marine electronics
- Weather stations

### Industrial Use
- Equipment protection
- Parts storage
- Test fixtures
- Prototype housings

The Advanced Rugged Box module provides a professional solution for creating durable, functional enclosures with proper mechanical features!
