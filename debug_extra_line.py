#!/usr/bin/env python
"""Debug script to identify the source of extra wall line with exact user command."""
import sys
sys.path.insert(0, '.')

from drawscaffold.utils.facade_converter import convert_facades_to_segments
from drawscaffold.model.calculator_oop import SegmentTopDownCalculator

# Exact user command parameters
facades = {
    'F': ['start,0,2000,0,F', 'inset,500,2000,300,F'], 
    'R': ['start,0,1500,0,R'], 
    'B': ['start,0,2000,0,B'], 
    'L': ['start,0,1500,0,L']
}

print("=" * 80)
print("STEP 1: SEGMENTS FROM FACADE_CONVERTER")
print("=" * 80)

segs = convert_facades_to_segments(facades)

for i, s in enumerate(segs):
    dir_ = s.get('direction', 'N/A')
    len_ = s.get('length', 0)
    p1 = s.get('p1', {'x': 0, 'y': 0})
    p2 = s.get('p2', {'x': 0, 'y': 0})
    
    # Calculate scaled wall coordinates (as used in segment_drawer.py)
    SX, SY = 5.0, -5.0
    w1_x, w1_y = p1['x'] * SX, p1['y'] * SY
    w2_x, w2_y = p2['x'] * SX, p2['y'] * SY
    
    print(f"Seg {i}: dir={dir_:5} len={len_:5} | raw: ({p1['x']:.1f},{p1['y']:.1f})->({p2['x']:.1f},{p2['y']:.1f}) | scaled wall: ({w1_x:.0f},{w1_y:.0f})->({w2_x:.0f},{w2_y:.0f})")

print("\n" + "=" * 80)
print("STEP 2: DRAWING DATA FROM CALCULATOR_OOP")
print("=" * 80)

calc = SegmentTopDownCalculator(height=1500, slope=12, verbose=False, prefer_gaps=False)
drawing_data = calc.get_scaffold_segments(segs)

for i, dd in enumerate(drawing_data):
    w_p1 = dd['wall_p1']
    w_p2 = dd['wall_p2']
    s_p1 = dd['scaff_p1']
    s_p2 = dd['scaff_p2']
    mods = dd['modules']
    
    # Scaled coordinates
    SX, SY = 5.0, -5.0
    w1_x, w1_y = w_p1['x'] * SX, w_p1['y'] * SY
    w2_x, w2_y = w_p2['x'] * SX, w_p2['y'] * SY
    s1_x, s1_y = s_p1['x'] * SX, s_p1['y'] * SY
    s2_x, s2_y = s_p2['x'] * SX, s_p2['y'] * SY
    
    print(f"Seg {i}: wall ({w1_x:.0f},{w1_y:.0f})->({w2_x:.0f},{w2_y:.0f}) | scaff ({s1_x:.0f},{s1_y:.0f})->({s2_x:.0f},{s2_y:.0f}) | mods={len(mods)}")

print("\n" + "=" * 80)
print("STEP 3: LOOKING FOR EXTRA/PROBLEMATIC WALL SEGMENTS")
print("=" * 80)

# Looking for segments where wall line might create extra line
# The extra line is on the RIGHT side of the scaffolds, so X should be > 2000 (R wall is at X=2000)
for i, dd in enumerate(drawing_data):
    w_p1 = dd['wall_p1']
    w_p2 = dd['wall_p2']
    SX, SY = 5.0, -5.0
    w1_x = w_p1['x'] * SX
    w2_x = w_p2['x'] * SX
    
    # Check for walls at high X values (around R wall position)
    if w1_x >= 2000 or w2_x >= 2000:
        print(f"Seg {i}: HIGH X WALL at ({w1_x:.0f},{w_p1['y']*SY:.0f})->({w2_x:.0f},{w_p2['y']*SY:.0f})")

print("\n" + "=" * 80)
print("STEP 4: CHECK FOR VERTICAL WALL SEGMENTS (likely our extra line)")
print("=" * 80)

for i, dd in enumerate(drawing_data):
    w_p1 = dd['wall_p1']
    w_p2 = dd['wall_p2']
    SX, SY = 5.0, -5.0
    w1_x, w1_y = w_p1['x'] * SX, w_p1['y'] * SY
    w2_x, w2_y = w_p2['x'] * SX, w_p2['y'] * SY
    
    # Check for vertical lines (same X coordinate)
    if abs(w1_x - w2_x) < 1:  # Vertical line
        direction = segs[i].get('direction', 'N/A')
        print(f"Seg {i} ({direction}): VERTICAL wall at X={w1_x:.0f}, from Y={w1_y:.0f} to Y={w2_y:.0f}")

print("\nDone.")
