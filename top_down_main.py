import argparse
import json
import os
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from drawscaffold.calculate_top_down import top_down_calc
from drawscaffold.calculator.price_calculator import calculate_price
from drawscaffold.utils.facade_converter import convert_facades_to_segments
from drawscaffold.model.calculator_oop import SegmentTopDownCalculator


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Draw scaffolds top-down professionally')
    
    # Legacy facade format (kept for backwards compatibility)
    parser.add_argument("--facade", action="append", 
                       help="Legacy: inset/outset,start,length,depth,SIDE")

    # New simplified format
    parser.add_argument("--wall", action="append",
                       help="Wall definition: SIDE:LENGTH (e.g., F:2000)")
    parser.add_argument("--feature", action="append",
                       help="Feature: SIDE:type,pos,depth (e.g., F:inset,300,250)")
    parser.add_argument("--adjust-corners", action="store_true",
                       help="Adjust wall lengths for neighbor insets/outsets")
    parser.add_argument("--no-150", action="store_true", dest="no_150",
                       help="Avoid 150cm modules, prefer gaps")

    # Output options
    parser.add_argument("--image", action="store_true", help="Generate PNG image")
    parser.add_argument("--svg", action="store_true", help="Generate SVG")
    parser.add_argument("--dxf", action="store_true", help="Generate DXF")

    # Required parameters
    parser.add_argument("--height-in-cm", type=float, required=True, help="Construct height in cm")
    parser.add_argument("--surface-slope", type=float, required=True, help="Surface slope")
    parser.add_argument("--toe-board-text", action="store_true", help="Text on toe board")

    # Pattern options
    pattern_group = parser.add_mutually_exclusive_group()
    pattern_group.add_argument("--use-x-pattern", action="store_true")
    pattern_group.add_argument("--use-zigzag-pattern", action="store_true")

    # Other
    parser.add_argument("--calculate", action="store_true", help="Calculate materials only")
    parser.add_argument("--calculate-price", action="store_true", help="Calculate price")
    parser.add_argument("--project-name", type=str, default='project', help="Project name")
    parser.add_argument("--verbose", action="store_true", help="Debug output")

    return parser.parse_args()


def parse_walls(wall_args):
    """Parse --wall arguments into dict."""
    walls = {}
    if not wall_args:
        return walls
    for w in wall_args:
        try:
            side, length = w.split(':')
            walls[side.upper()] = int(length)
        except:
            pass
    return walls


def parse_features(feature_args):
    """Parse --feature arguments into dict of lists."""
    features = {'F': [], 'R': [], 'B': [], 'L': []}
    if not feature_args:
        return features
    for f in feature_args:
        try:
            side, rest = f.split(':', 1)
            parts = rest.split(',')
            ftype = parts[0]  # inset/outset
            pos = int(parts[1])
            depth = int(parts[2])
            features[side.upper()].append({
                'type': ftype,
                'pos': pos,
                'depth': depth
            })
        except:
            pass
    return features


def calculate_corner_adjustment(features_list):
    """
    Calculate corner adjustment value for a wall.
    
    This returns the maximum outset depth on the wall, as outsets
    protrude beyond the building baseline and affect neighboring walls.
    """
    max_outset = 0
    for f in features_list:
        if f['type'] == 'outset':
            max_outset = max(max_outset, f['depth'])
    return max_outset


def build_facade_dict_from_simplified(walls, features, adjust_corners=False, verbose=False):
    """
    Build facade dict from simplified --wall and --feature input.
    
    If adjust_corners=True, adjusts wall lengths to account for
    neighbor wall outsets/insets at corners.
    """
    # Calculate corner adjustments for each wall (based on outsets)
    corner_adjustments = {}
    for side in ['F', 'R', 'B', 'L']:
        corner_adjustments[side] = calculate_corner_adjustment(features.get(side, []))
    
    if verbose:
        print(f"Corner adjustments: {corner_adjustments}")
    
    # Neighbor mapping: which walls affect which
    # For wall X, start is affected by prev wall's end, end is affected by next wall's start
    prev_wall = {'F': 'L', 'R': 'F', 'B': 'R', 'L': 'B'}
    next_wall = {'F': 'R', 'R': 'B', 'B': 'L', 'L': 'F'}
    
    # Adjust wall lengths if requested
    adjusted_lengths = {}
    for side in ['F', 'R', 'B', 'L']:
        base_length = walls.get(side, 0)
        if adjust_corners and base_length > 0:
            # Subtract neighbor outsets from both ends
            start_adjust = corner_adjustments[prev_wall[side]]
            end_adjust = corner_adjustments[next_wall[side]]
            adjusted_length = base_length - start_adjust - end_adjust
            adjusted_lengths[side] = max(0, adjusted_length)
            if verbose:
                print(f"{side}: {base_length} - {start_adjust} - {end_adjust} = {adjusted_lengths[side]}")
        else:
            adjusted_lengths[side] = base_length
    
    # Build facade dict in legacy format
    facade_dict = {'F': [], 'R': [], 'B': [], 'L': []}
    
    for side in ['F', 'R', 'B', 'L']:
        length = adjusted_lengths.get(side, 0)
        if length <= 0:
            continue
            
        # Start command
        facade_dict[side].append(f"start,0,{length},0,{side}")
        
        # Add features
        for f in features.get(side, []):
            cmd = f"{f['type']},{f['pos']},{length},{f['depth']},{side}"
            facade_dict[side].append(cmd)
    
    return facade_dict


def build_facade_dict_legacy(facades):
    """Convert legacy CLI facade arguments to structured dictionary."""
    facade_dict = {'F': [], 'R': [], 'L': [], 'B': []}
    
    for facade in facades:
        for facade_key in facade_dict.keys():
            if facade_key in facade:
                facade_dict[facade_key].append(facade)
    
    # Inject start commands if missing
    for key in facade_dict:
        if len(facade_dict[key]) > 0:
            first = facade_dict[key][0]
            if not first.startswith('start'):
                try:
                    parts = first.split(',')
                    w_len = parts[2]
                    facade_dict[key].insert(0, f"start,0,{w_len},0,{key}")
                except:
                    pass
    
    # Auto-fill opposite walls
    if len(facade_dict['F']) == 0 and len(facade_dict['B']) != 0:
        facade_length = facade_dict['B'][-1].split(',')[2]
        facade_dict['F'].append(f'start,0,{facade_length},0,F')
    if len(facade_dict['B']) == 0 and len(facade_dict['F']) != 0:
        facade_length = facade_dict['F'][-1].split(',')[2]
        facade_dict['B'].append(f'start,0,{facade_length},0,B')
    if len(facade_dict['R']) == 0 and len(facade_dict['L']) != 0:
        facade_length = facade_dict['L'][-1].split(',')[2]
        facade_dict['R'].append(f'start,0,{facade_length},0,R')
    if len(facade_dict['L']) == 0 and len(facade_dict['R']) != 0:
        facade_length = facade_dict['R'][-1].split(',')[2]
        facade_dict['L'].append(f'start,0,{facade_length},0,L')
    
    return facade_dict


def main():
    args = parse_arguments()
    
    # Determine input mode
    if args.wall:
        # New simplified input
        walls = parse_walls(args.wall)
        features = parse_features(args.feature)
        facade_dict = build_facade_dict_from_simplified(
            walls, features, 
            adjust_corners=args.adjust_corners,
            verbose=args.verbose
        )
    elif args.facade:
        # Legacy input
        facade_dict = build_facade_dict_legacy(args.facade)
    else:
        print("Error: Provide --wall or --facade arguments")
        exit(-1)
    
    if args.verbose:
        print(f"Facade Dict: {facade_dict}")
    
    # Handle calculation-only modes
    if args.calculate:
        material_dict = top_down_calc(
            args.verbose, facade_dict, args.height_in_cm, 
            args.surface_slope, args.toe_board_text, 
            args.use_x_pattern, args.use_zigzag_pattern
        )
        print(material_dict)
        exit(0)
        
    if args.calculate_price:
        material_dict = top_down_calc(
            args.verbose, facade_dict, args.height_in_cm,
            args.surface_slope, args.toe_board_text,
            args.use_x_pattern, args.use_zigzag_pattern
        )
        price, currency, symbol = calculate_price(material_dict)
        print(f"{price} {symbol}({currency})")
        exit(0)
    
    # Convert to segments
    segments = convert_facades_to_segments(facade_dict)
    
    if args.verbose:
        print(f"Generated {len(segments)} segments")
        for i, seg in enumerate(segments):
            print(f"  Seg {i}: {seg['direction']} len={seg['length']}")
    
    # Calculate scaffold geometry
    calc = SegmentTopDownCalculator(
        height=args.height_in_cm,
        slope=args.surface_slope,
        verbose=args.verbose,
        prefer_gaps=args.no_150
    )
    drawing_data = calc.get_scaffold_segments(segments)
    
    # Generate output in manual_output folder with timestamp
    import datetime
    timestamp_str = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    output_dir = os.path.join("manual_output", timestamp_str)
    os.makedirs(output_dir, exist_ok=True)
    
    project_name = args.project_name.replace(' ', '_')
    output_name = os.path.join(output_dir, project_name)
    
    materials, dxf_path = calc.draw_scaffold_segments(drawing_data, output_name)
    
    if args.verbose:
        print(f"Materials: {materials}")
        print(f"Output directory: {output_dir}")
    
    # Save materials info
    with open(os.path.join(output_dir, "materials.txt"), "w") as f:
        f.write(f"Facades: {facade_dict}\n")
        f.write(f"Height: {args.height_in_cm}\n")
        f.write(f"Adjust Corners: {args.adjust_corners if hasattr(args, 'adjust_corners') else False}\n")
        f.write("Materials:\n")
        for k, v in materials.items():
            f.write(f"  {k}: {v}\n")
    
    # Collect generated paths
    generated_paths = []
    abs_path_base = os.path.abspath(output_name)
    for ext in ['.png', '.svg', '.dxf', '.jpg']:
        path = f"{abs_path_base}{ext}"
        if os.path.exists(path):
            generated_paths.append(path)
    
    print(json.dumps({"paths": generated_paths, "materials": materials, "output_dir": output_dir}))


if __name__ == "__main__":
    main()

