
import random
import sys
import os
import math
import shutil

# Ensure we can import from parent directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from drawscaffold.model.calculator_oop import SegmentTopDownCalculator
from drawscaffold.utils.facade_converter import convert_facades_to_segments

def generate_random_facades():
    sides = ['F', 'R', 'B', 'L']
    facades = {side: [] for side in sides}
    
    # Define lengths for each side to form a closed loop (rectangle)
    width = random.randint(1500, 4000) # F and B
    depth = random.randint(1500, 4000) # R and L
    
    side_lengths = {
        'F': width,
        'R': depth,
        'B': width,
        'L': depth
    }
    
    for side in sides:
        length = side_lengths[side]
        side_cmds = []
        
        # Always add start command
        side_cmds.append(f"start,0,{length},0,{side}")
        
        # Generate random intervals for features
        # Limit to 1 feature per side to drastically improve collision success rate
        # while maintaining randomness.
        num_features = 1
        if length < 600: 
            num_features = 0
            
        placed_intervals = []
        
        attempts = 0
        while len(placed_intervals) < num_features and attempts < 50:
            attempts += 1
            
            # Feature dimensions: Larger range
            ft_len = random.randint(400, 1200)
            if ft_len >= length - 200: continue
            
            # Position (Start)
            # Leave buffer at corners (120cm) to prevent immediate corner clashes.
            # 120cm is enough for a standard 73cm scaffold + gap.
            min_pos = 120
            max_pos = length - 120 - ft_len
            
            if max_pos <= min_pos: continue
            
            start_pos = random.randint(min_pos, max_pos)
            end_pos = start_pos + ft_len
            
            # Check overlap
            overlap = False
            for (p_start, p_end) in placed_intervals:
                # Buffer of 50cm between features
                if not (end_pos + 50 <= p_start or start_pos >= p_end + 50):
                    overlap = True
                    break
            
            if not overlap:
                placed_intervals.append((start_pos, end_pos))
                
                ft_type = random.choice(['inset', 'outset'])
                
                # Handling User Request: "No scaffold in areas < 200cm"
                # Solution: Don't generate Insets with Depth < 200 or Width < 200 (Length is already > 400).
                # Also ensure Width/Depth ratio avoids collisions.
                
                valid_feature = True
                final_depth = 0
                
                if ft_type == 'inset':
                    # INSET RULES
                    # User feedback: 200cm Width still causes collisions (visual overlap).
                    # Need wider clearance. 
                    # Scaffold width ~1m. Two scaffolds facing = 2m + Gap.
                    # 200cm is tight if offsets vary.
                    # Let's enforce Min Width = 300cm.
                    
                    min_width_required = 300
                    
                    # 2. Collision Avoidance (Smart Depth)
                    # Relaxed Formula: Depth <= (Length - 100) / 2 to allow deeper features if width is sufficient?
                    # Previous: (Length - 200) / 2.
                    # If Length 300 -> (100)/2 = 50. Too shallow?
                    # The user wants "No scaffold in small areas".
                    # So if it forces shallow depth, that's GOOD.
                    
                    max_allowed_depth = (ft_len - 200) // 2
                    
                    if ft_len < min_width_required:
                        # Too narrow for an Inset. Switch to Outset.
                        ft_type = 'outset'
                    elif max_allowed_depth < 100: # If max depth is tiny, skip Inset
                        ft_type = 'outset'
                    else:
                        # Choose depth
                        possible_depths = [d for d in [100, 150, 200, 250, 300, 400] if d <= max_allowed_depth]
                        if not possible_depths:
                             ft_type = 'outset'
                        else:
                             final_depth = random.choice(possible_depths)
                
                if ft_type == 'outset':
                    # OUTSET RULES
                     if ft_len < 200: # Very small bump
                         final_depth = 50
                     else:
                         final_depth = random.choice([200, 250, 300, 400])
                
                if valid_feature:
                     side_cmds.append(f"{ft_type},{start_pos},{length},{final_depth},{side}")
                     ret_type = 'outset' if ft_type == 'inset' else 'inset'
                     side_cmds.append(f"{ret_type},{end_pos},{length},{final_depth},{side}")
                
        # Sort commands by position
        # Format: type,pos,length,depth,side
        # We sort by 'pos' (2nd element)
        def get_pos(cmd):
            return int(cmd.split(',')[1])
            
        side_cmds.sort(key=get_pos)
        facades[side] = side_cmds
            
    return facades



def ccw(A,B,C):
    return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])

def intersect(A,B,C,D):
    # Return true if line segments AB and CD intersect
    return ccw(A,C,D) != ccw(B,C,D) and ccw(A,B,C) != ccw(A,B,D)

def dot(v, w):
    return v[0]*w[0] + v[1]*w[1]

def length_sq(v):
    return v[0]**2 + v[1]**2

def dist_to_segment_sq(p, v, w):
    # Return minimum distance between line segment vw and point p
    l2 = length_sq((w[0]-v[0], w[1]-v[1]))
    if l2 == 0: return length_sq((p[0]-v[0], p[1]-v[1]))
    t = ((p[0]-v[0])*(w[0]-v[0]) + (p[1]-v[1])*(w[1]-v[1])) / l2
    t = max(0, min(1, t))
    proj = (v[0] + t*(w[0]-v[0]), v[1] + t*(w[1]-v[1]))
    return length_sq((p[0]-proj[0], p[1]-proj[1]))

def dist_to_segment(p, v, w):
    import math
    return math.sqrt(dist_to_segment_sq(p, v, w))

def min_dist_between_segments(p1, p2, p3, p4):
    # p1-p2 and p3-p4
    # Distance is min of dist(endpts to other segment)
    # Check simple intersection first?
    # Actually, simpler: Min distance between two segments is either 0 (intersect) or min of endpoint distances.
    # Wait, parallel segments?
    # Common approach: check all 4 endpoints against opposite segment. 
    # Also need check if they cross (dist=0).
    
    # Efficient check:
    d1 = dist_to_segment(p3, p1, p2)
    d2 = dist_to_segment(p4, p1, p2)
    d3 = dist_to_segment(p1, p3, p4)
    d4 = dist_to_segment(p2, p3, p4)
    
    return min(d1, d2, d3, d4)

def check_intersections(drawing_data):
    # Returns True if ANY collision is detected
    lines = []
    for item in drawing_data:
        p1 = (item['scaff_p1']['x'], item['scaff_p1']['y'])
        p2 = (item['scaff_p2']['x'], item['scaff_p2']['y'])
        lines.append((p1, p2))
        
    # SCAFFOLD WIDTH BUFFER
    # Scaffold is approx 73cm wide.
    # Coordinates are stored at 1px = 5cm scale
    # Center-to-center distance should be at least ~100cm to avoid visual clash.
    # 100cm / 5 = 20 pixels
    BUFFER = 20.0
    
    count = len(lines)
    for i in range(count):
        for j in range(i + 1, count):
            # Skip adjacent
            if abs(i - j) == 1: continue
            if abs(i - j) == count - 1: continue 
            
            l1 = lines[i]
            l2 = lines[j]
            
            # Check 1: Intersection
            if intersect(l1[0], l1[1], l2[0], l2[1]):
                return True
                
            # Check 2: Proximity
            dist = min_dist_between_segments(l1[0], l1[1], l2[0], l2[1])
            if dist < BUFFER:
                return True
                
    return False

def main():
    import argparse
    import datetime
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-150", action="store_true", help="Avoid 150cm modules")
    args = parser.parse_args()
    
    print("Generating random scaffold project...")
    print(f"Option No-150: {args.no_150}")
    
    # Retry Loop
    # We strictly discard any layout with collisions.
    max_retries = 500
    valid_facades = None
    final_drawing_data = None
    final_h = 0
    final_calc = None
    
    for attempt in range(max_retries):
        facades = generate_random_facades()
        segments = convert_facades_to_segments(facades)
        
        h = random.randint(500, 2000)
        # Pass prefer_gaps flag
        calc = SegmentTopDownCalculator(height=h, slope=0, verbose=False, prefer_gaps=args.no_150)
        
        # Get Geometry
        drawing_data = calc.get_scaffold_segments(segments)
        
        # Strict Check
        if check_intersections(drawing_data):
            print(f"Attempt {attempt+1}: Collision detected. Retrying...")
            continue
        else:
            print(f"Attempt {attempt+1}: Valid Layout Found!")
            valid_facades = facades
            final_drawing_data = drawing_data
            final_h = h
            final_calc = calc
            break
            
    if not valid_facades:
        print("Failed to generate valid layout after retries.")
        # Fallback? No, user wants clean output.
        return
    
    # ... (rest of the file as before, but use final_calc)
    
    print(f"Facades Generated: {valid_facades}")
    
    # Create output directory
    timestamp_str = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    output_dir = os.path.join("outputs", timestamp_str)
    os.makedirs(output_dir, exist_ok=True)
    
    project_name_base = f"scaffold"
    project_path = os.path.join(output_dir, project_name_base)
    
    print(f"Project Path: {project_path}")
    
    try:
        # Draw
        # Use the calculator instance that has the correct settings
        print(f"Drawing layout for height: {final_h}")
        materials, dxf_path = final_calc.draw_scaffold_segments(final_drawing_data, project_path)
        
        print("Generated files:", dxf_path)
        print("Materials:", materials)
        
        with open(os.path.join(output_dir, "materials.txt"), "w") as f:
            f.write(f"Height: {final_h}\n")
            f.write(f"Facades: {valid_facades}\n")
            f.write(f"Prefer Gaps: {args.no_150}\n")
            f.write("Materials:\n")
            for k, v in materials.items():
                 f.write(f"{k}: {v}\n")
        print(f"Saved materials to {os.path.join(output_dir, 'materials.txt')}")
        
    except Exception as e:
        print(f"Error during generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
