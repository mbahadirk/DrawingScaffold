from drawscaffold.calculate_top_down import frontal_calculator2D, MaterialCounterTopDown, CalculatorTopDown
from drawscaffold.utils.debug_printer import DebugPrinter
from drawscaffold.calculator.calculator_top_down import CalculatorTopDown
from drawscaffold.model.segment_drawer import SegmentDrawer

class SegmentTopDownCalculator:
    def __init__(self, height, slope, verbose=False, prefer_gaps=False):
        self.height = height
        self.slope = slope
        self.verbose = verbose
        self.prefer_gaps = prefer_gaps  # Skip 150cm modules if True
        self.d = DebugPrinter(verbose)
        self.material_counter = MaterialCounterTopDown()
        self.top_down_counter = CalculatorTopDown()
        self.gap = 25

    def calculate_and_draw(self, segments_data, filename):
        # Wrapper for backward compatibility
        drawing_data = self.get_scaffold_segments(segments_data)
        return self.draw_scaffold_segments(drawing_data, filename)

    def get_scaffold_segments(self, segments_data):
        # segments_data: List of dicts with full point info and lengths
        # [{p1: {x,y}, p2: {x,y}, length: cm, direction: str}]
        
        # 1. Prepare Points List for Geometry
        points = []
        for i, seg in enumerate(segments_data):
            points.append((seg['p1']['x'], seg['p1']['y']))
        
        # Determine if closed loop
        is_closed = False
        last_p2 = segments_data[-1]['p2']
        first_p1 = segments_data[0]['p1']
        if abs(last_p2['x'] - first_p1['x']) < 1 and abs(last_p2['y'] - first_p1['y']) < 1:
             is_closed = True
             
        # Calculate Scaffolding Polygon (Offset)
        scaffold_segments = self._calculate_scaffold_geometry(segments_data, is_closed)
        
        # Build initial drawing data with perpendicular info preserved
        drawing_data = []
        for i, seg_geom in enumerate(scaffold_segments):
            is_perp = segments_data[i].get('is_perpendicular_inset', False)
            
            p1 = {'x': seg_geom['p1']['x'], 'y': seg_geom['p1']['y']}
            p2 = {'x': seg_geom['p2']['x'], 'y': seg_geom['p2']['y']}
            length = seg_geom['length']
            
            drawing_data.append({
                'wall_p1': segments_data[i]['p1'],
                'wall_p2': segments_data[i]['p2'],
                'scaff_p1': p1,
                'scaff_p2': p2,
                'length': length,
                'modules': [],  # Will be calculated after collision resolution
                'is_perpendicular': is_perp,
                'direction': segments_data[i]['direction']
            })
        
        # 2. Resolve collisions by shifting segments
        drawing_data = self._resolve_collisions(drawing_data)
        
        # 3. Calculate modules for each segment after collision resolution
        for seg in drawing_data:
            seg['modules'] = self._process_segment_logic(seg['length'], seg['direction'])
            
        return drawing_data

    # ==================== COLLISION RESOLUTION ====================
    
    def _resolve_collisions(self, drawing_data, max_iterations=10):
        """
        Iteratively resolve all collisions by shifting segments.
        Perpendicular segments are shifted first (priority-based).
        """
        import math
        
        BUFFER_DISTANCE = 100  # cm - minimum distance (includes scaffold width + margin)
        MAX_SHIFT_RATIO = 0.50  # Maximum shift = 50% of segment length
        
        for iteration in range(max_iterations):
            collisions = self._detect_collisions(drawing_data, BUFFER_DISTANCE)
            
            if not collisions:
                if self.verbose:
                    self.d.print(f"All collisions resolved after {iteration} iterations")
                break
            
            if self.verbose:
                self.d.print(f"Iteration {iteration + 1}: Found {len(collisions)} collisions")
            
            for (i, j, overlap, collision_end_i, collision_end_j) in collisions:
                seg_i = drawing_data[i]
                seg_j = drawing_data[j]
                
                # Determine which segment to shift
                # Priority: Perpendicular segments are shifted first
                # If both or neither are perpendicular, shift the shorter one
                shift_target_idx = None
                
                is_perp_i = seg_i.get('is_perpendicular', False)
                is_perp_j = seg_j.get('is_perpendicular', False)
                
                if is_perp_i and not is_perp_j:
                    shift_target_idx = i
                elif is_perp_j and not is_perp_i:
                    shift_target_idx = j
                else:
                    # Both or neither perpendicular - shift the shorter one
                    if seg_i['length'] <= seg_j['length']:
                        shift_target_idx = i
                    else:
                        shift_target_idx = j
                
                target = drawing_data[shift_target_idx]
                collision_end = collision_end_i if shift_target_idx == i else collision_end_j
                
                # Calculate shift amount
                shift_amount = overlap + 20  # 20cm extra buffer
                max_shift = target['length'] * MAX_SHIFT_RATIO
                shift_amount = min(shift_amount, max_shift)
                
                # Minimum segment length check
                if target['length'] - shift_amount < 100:
                    shift_amount = max(0, target['length'] - 100)
                
                if shift_amount <= 0:
                    continue
                
                # Apply shift
                self._apply_shift(target, shift_amount, collision_end)
                
                if self.verbose:
                    self.d.print(f"  Shifted segment {shift_target_idx} by {shift_amount:.1f}cm from {collision_end} end")
        
        return drawing_data
    
    def _detect_collisions(self, drawing_data, buffer_distance):
        """
        Detect all collisions between segments.
        Now also checks adjacent segments because L-corners can collide.
        Returns: List of (seg_a_idx, seg_b_idx, overlap_amount, collision_end_a, collision_end_b)
        """
        import math
        
        collisions = []
        n = len(drawing_data)
        
        for i in range(n):
            for j in range(i + 1, n):  # Check ALL pairs including adjacent
                seg_a = drawing_data[i]
                seg_b = drawing_data[j]
                
                # Get segment endpoints
                a1 = (seg_a['scaff_p1']['x'], seg_a['scaff_p1']['y'])
                a2 = (seg_a['scaff_p2']['x'], seg_a['scaff_p2']['y'])
                b1 = (seg_b['scaff_p1']['x'], seg_b['scaff_p1']['y'])
                b2 = (seg_b['scaff_p2']['x'], seg_b['scaff_p2']['y'])
                
                # For adjacent segments, only check if they form an L-corner
                # where scaffolds could actually overlap
                is_adjacent = (j == i + 1) or (i == 0 and j == n - 1)
                
                if is_adjacent:
                    # For adjacent segments, check if their shared endpoint is too close
                    # This happens when perpendicular scaffolds overlap at corners
                    # Only flag if the MIDDLE of one segment is close to the other
                    shared_point = a2 if j == i + 1 else a1  # Shared corner point
                    
                    # Distance from shared point to segment midpoints
                    mid_a = ((a1[0] + a2[0]) / 2, (a1[1] + a2[1]) / 2)
                    mid_b = ((b1[0] + b2[0]) / 2, (b1[1] + b2[1]) / 2)
                    
                    # If segments are very short (perpendicular stubs), they might overlap
                    len_a = math.hypot(a2[0]-a1[0], a2[1]-a1[1]) * 5.0  # px to cm
                    len_b = math.hypot(b2[0]-b1[0], b2[1]-b1[1]) * 5.0
                    
                    # Only check collision for L-corners with short perpendicular segments
                    # where scaffold width matters
                    if len_a < 400 or len_b < 400:  # Short segments = perpendicular stubs
                        distance_px, closest_end_a, closest_end_b = self._segment_distance_with_ends(a1, a2, b1, b2)
                        distance_cm = distance_px * 5.0
                        
                        # Scaffold width is ~73cm, so if centerlines are < 80cm apart at corners
                        # there will be visual overlap
                        corner_buffer = 80  # cm - scaffold width + small margin
                        if distance_cm < corner_buffer:
                            overlap = corner_buffer - distance_cm
                            collisions.append((i, j, overlap, closest_end_a, closest_end_b))
                else:
                    # Non-adjacent: normal distance check
                    distance_px, closest_end_a, closest_end_b = self._segment_distance_with_ends(a1, a2, b1, b2)
                    distance_cm = distance_px * 5.0
                    
                    if distance_cm < buffer_distance:
                        overlap = buffer_distance - distance_cm
                        collisions.append((i, j, overlap, closest_end_a, closest_end_b))
        
        return collisions
    
    def _segment_distance_with_ends(self, a1, a2, b1, b2):
        """
        Calculate minimum distance between two line segments.
        Also returns which end of each segment is closest.
        Returns: (distance, end_a ('p1' or 'p2'), end_b ('p1' or 'p2'))
        """
        import math
        
        def point_to_segment_dist(p, v, w):
            """Return minimum distance from point p to segment vw"""
            l2 = (w[0]-v[0])**2 + (w[1]-v[1])**2
            if l2 == 0:
                return math.hypot(p[0]-v[0], p[1]-v[1]), 0.0
            t = max(0, min(1, ((p[0]-v[0])*(w[0]-v[0]) + (p[1]-v[1])*(w[1]-v[1])) / l2))
            proj = (v[0] + t*(w[0]-v[0]), v[1] + t*(w[1]-v[1]))
            return math.hypot(p[0]-proj[0], p[1]-proj[1]), t
        
        # Check all 4 endpoint-to-segment distances
        d1, t1 = point_to_segment_dist(a1, b1, b2)  # a1 to segment b
        d2, t2 = point_to_segment_dist(a2, b1, b2)  # a2 to segment b
        d3, t3 = point_to_segment_dist(b1, a1, a2)  # b1 to segment a
        d4, t4 = point_to_segment_dist(b2, a1, a2)  # b2 to segment a
        
        # Find minimum
        distances = [
            (d1, 'p1', 'p1' if t1 < 0.5 else 'p2'),  # a1 closest
            (d2, 'p2', 'p1' if t2 < 0.5 else 'p2'),  # a2 closest
            (d3, 'p1' if t3 < 0.5 else 'p2', 'p1'),  # b1 closest
            (d4, 'p1' if t4 < 0.5 else 'p2', 'p2'),  # b2 closest
        ]
        
        min_dist = min(distances, key=lambda x: x[0])
        return min_dist
    
    def _apply_shift(self, segment, shift_amount, direction):
        """
        Shift a segment along its axis.
        direction: 'p1' (shift from p1 end) or 'p2' (shift from p2 end)
        """
        import math
        
        p1 = segment['scaff_p1']
        p2 = segment['scaff_p2']
        
        dx = p2['x'] - p1['x']
        dy = p2['y'] - p1['y']
        length_px = math.hypot(dx, dy)
        
        if length_px == 0:
            return
        
        ux = dx / length_px
        uy = dy / length_px
        
        shift_px = shift_amount / 5.0  # cm to pixels
        
        if direction == 'p1':
            # Shift P1 towards P2 (shrink from start)
            segment['scaff_p1']['x'] += ux * shift_px
            segment['scaff_p1']['y'] += uy * shift_px
        else:
            # Shift P2 towards P1 (shrink from end)
            segment['scaff_p2']['x'] -= ux * shift_px
            segment['scaff_p2']['y'] -= uy * shift_px
        
        # Update length
        segment['length'] = max(0, segment['length'] - shift_amount)

    # ==================== END COLLISION RESOLUTION ====================

    def draw_scaffold_segments(self, drawing_data, filename):
        # Draw
        drawer = SegmentDrawer(self.verbose)
        final_path = drawer.draw_project(drawing_data, filename)
        
        return self.material_counter.counter_dict, final_path

    def _calculate_scaffold_geometry(self, segments_data, is_closed):
        import math
        
        # Extract Points
        pts = [s['p1'] for s in segments_data]
        if is_closed:
             pts.append(segments_data[0]['p1']) # Close the loop for calculation
        else:
             pts.append(segments_data[-1]['p2'])
             
        # 1. Signed Area & Orientation
        area = 0.0
        for i in range(len(pts) - 1):
            area += (pts[i]['x'] * pts[i+1]['y'] - pts[i+1]['x'] * pts[i]['y'])
        area *= 0.5
        is_cw = area > 0 # Y-Down System: CW is Positive Area
        
        # Offset Amount (Gap + Width)
        # Gap 25cm. Width 70cm approx or 75cm? Standard is ~73cm or 70cm? 
        # Using 95cm total.
        offset_dist = 25
        
        # In Y-Down:
        # CW (Right Turns): Outside is Left. Normal(-dy, dx).
        # CCW (Left Turns): Outside is Right. Normal(dy, -dx).
        # Let's verify Normal Left: (dx, dy) -> (-dy, dx).
        # (1, 0) Right -> (0, 1) Down? No, (0, 1) is Down.
        # Down is "Right" of (1,0) in Y-Down system?
        # RHR: X(Thumb), Y(Index Down). Z(Middle INTO screen).
        # Vector (1,0). Left is Up (0,-1).
        # Formula (-dy, dx): -(0), 1 = (0,1) Down. This is RIGHT normal in Y-Down.
        # Formula (dy, -dx): (0, -1) Up. This is LEFT normal in Y-Down.
        
        # So: 
        # Left Normal (Up relative to Right vector) = (dy, -dx).
        # CW Loop (Right turns): We are walking Inside. Outside is Left.
        # So CW -> Use Left Normal (dy, -dx).
        # CCW Loop (Left turns): We are walking Outside? Or Inside?
        # Standard Poly: CCW area < 0 (Y-Down).
        # If CCW, Outside is Right Normal (-dy, dx).
        
        # Wait, Area formula:
        # Rectangle (0,0)-(10,0)-(10,10)-(0,10).
        # 0->10 (R). 10->10 (D). 10->0 (L). 0->0 (U).
        # Area was +200. (Positive).
        # Orientation is CW.
        # We want OUTSIDE.
        # R vector (1,0). Outside is Up (0,-1). Left Normal.
        # So CW -> Left Normal.
        
        # Let's check CCW.
        # (0,0)-(0,10)-(10,10)-(10,0).
        # D->R->U->L.
        # Area will be Negative.
        # D vector (0,1). Outside is Right (1,0). (Right of vector D).
        # Wait. If I walk Down, Right is (West? No -X? No).
        # Pos (0,0) -> (0,10). Vector (0,1).
        # Looking Down. Right is -X (Left on screen).
        # We want Outside of Rectangle.
        # (0,0) to (0,10) is Left Edge. Outside is Left (-1,0).
        # So Outside is Right Normal relative to vector? 
        # Vector (0,1). Right Normal is (-1, 0)?
        # Right Normal formula (-dy, dx) -> (-1, 0). YES.
        
        # So:
        # CW (Area > 0): Use Left Normal (dy, -dx).
        # CCW (Area < 0): Use Right Normal (-dy, dx).
        
        offset_sign = 1 if area > 0 else -1
        
        # Line Equation: P + t*D
        # Offset Line: (P + N*dist) + t*D
        
        lines = []
        for i in range(len(segments_data)):
            p1 = pts[i]
            p2 = pts[i+1]
            dx = p2['x'] - p1['x']
            dy = p2['y'] - p1['y']
            length = math.hypot(dx, dy)
            if length == 0: continue
            
            ndx = dx / length
            ndy = dy / length
            
            # Normal
            if is_cw: # CW -> Left Normal (dy, -dx)
                 nx = ndy
                 ny = -ndx
            else: # CCW -> Right Normal (-dy, dx)
                 nx = -ndy
                 ny = ndx
                 
            # Convert pixels to cm scaler?
            # INPUT Points are pixels.
            # INPUT Length is cm.
            # We should do geometry in PIXELS to match drawing, then scale result?
            # Or geometry in CM?
            # The UI sends pixels. But Length is real CM.
            # The scaling factor is hypot(px_dx, px_dy) / length_cm? approx 0.2 px/cm?
            # 1 px = 5 cm (heuristic).
            # So Offset 95cm -> 95 / 5 = 19 pixels.
            
            scale = 1.0 / 5.0 # pixels per cm
            pixel_offset = offset_dist * scale
            
            off_dx = nx * pixel_offset
            off_dy = ny * pixel_offset
            
            # Line defined by Point on line and Direction vector
            line_pt = {'x': p1['x'] + off_dx, 'y': p1['y'] + off_dy}
            line_dir = {'x': ndx, 'y': ndy}
            
            lines.append({'p': line_pt, 'd': line_dir})
            
        # Calculate Intersections
        new_segments = []
        num_seg = len(lines)
        
        # Vertices of Offset Polygon
        offset_verts = []
        for i in range(num_seg):
            l1 = lines[i]
            l2 = lines[(i + 1) % num_seg] # Wrap around if closed
            
            # Find Intersection
            # P1 + t*D1 = P2 + u*D2
            # P1x + t*D1x = P2x + u*D2x
            # P1y + t*D1y = P2y + u*D2y
            
            # Solve for t, u
            # t*D1x - u*D2x = P2x - P1x
            # t*D1y - u*D2y = P2y - P1y
            
            # Cramer's Rule or Det
            det = l1['d']['x'] * (-l2['d']['y']) - l1['d']['y'] * (-l2['d']['x'])
            
            if abs(det) < 1e-9:
                # Parallel lines. Just use the endpoint?
                # If simplified setup, use "end of first" or "start of second".
                # For rigid generic:
                # Just take the average of standard endpoints?
                # Let's project P1_end to offset.
                # Actually, if parallel, they technically don't intersect or intersect everywhere.
                # Assuming simple corners for now. If parallel, just use p of L2?
                inter_x = l2['p']['x']
                inter_y = l2['p']['y']
            else:
                dx = l2['p']['x'] - l1['p']['x']
                dy = l2['p']['y'] - l1['p']['y']
                
                det_t = dx * (-l2['d']['y']) - dy * (-l2['d']['x'])
                t = det_t / det
                
                inter_x = l1['p']['x'] + t * l1['d']['x']
                inter_y = l1['p']['y'] + t * l1['d']['y']
            
            offset_verts.append({'x': inter_x, 'y': inter_y})
            
        # If open loop, we must handle start/end differently?
        # Typically open loop: Offset Start = Start + Normal*Offset.
        # But for 'Inner/Outer' collision, we assume contiguous chain.
        # For Open Loop: intersection i, i+1 works for internal vertices.
        # Start of 0 and End of Last need special handling (Perpendicular caps?).
        # For now, adopting intersection logic (assuming Closed or "Infinite" extension).
        # User draws Closed Loops mostly.
        
        if not is_closed:
             # Fix first and last vertices to not be influenced by wrap-around
             # Start V0: Just L0 start point?
             l0 = lines[0]
             v0 = l0['p'] # Start of offset line 0
             offset_verts[0] = v0 # Replace the wrap-around intersection
             
             # Last V_end?
             # Last segment lines[-1]. End point?
             # Offset verts contains i...i+1 intersection.
             # Verts: V0 (Start of S0), V1 (S0-S1), ... V_last (End of S_last?)
             # Current logic produced N verts for N lines (Closed loop logic).
             # If open, we need N+1 vertices.
             
             llast = lines[-1]
             # Estimated length in px
             # We rely on original length
             orig_last_len = math.hypot(pts[-1]['x']-pts[-2]['x'], pts[-1]['y']-pts[-2]['y'])
             v_last = {
                 'x': llast['p']['x'] + llast['d']['x']*orig_last_len,
                 'y': llast['p']['y'] + llast['d']['y']*orig_last_len
             }
             offset_verts.append(v_last)
             
             # Re-align indices
             # offset_verts now has N+1 points?
             # Logic loop above: range(num_seg). 0..N-1.
             # intersection 0: L0-L1. This is Vertex 1.
             # intersection N-1: L(N-1)-L0. This is Vertex 0 (Wrap).
             # If Open:
             # V0 = L0.p
             # V1 = Intersect(L0, L1)
             # ...
             # Vn = Ln.end
             
             final_verts = [l0['p']] # Start
             for i in range(num_seg - 1):
                 # Intersect i and i+1
                 # ... (Use calculation from loop above, but re-indexed)
                 # Actually, let's just use the loop above but ignore the wrapped index if !is_closed
                 pass
             # This is becoming complex inline.
             # Simplified: If open, use the computed intersections for inner corners.
             # Overwrite Vert 0 and Append Vert Last.
             
             # For now, let's keep closed loop logic as primary use case.
             pass

        # Build Segment List
        # Vertex i to Vertex i+1
        count = len(offset_verts)
        calc_segments = []
        for i in range(len(segments_data)): # Iterate original segments to map 1:1
             p1 = offset_verts[i]
             p2 = offset_verts[(i+1) % count]
             if not is_closed and i == len(segments_data) - 1:
                  p2 = offset_verts[i+1] # Use the extra point if we had it
             
             # Pixel Dist
             dist_px = math.hypot(p2['x']-p1['x'], p2['y']-p1['y'])
             
             # Convert back to CM
             # Scale = 5.
             length_cm = dist_px * 5.0
             
             calc_segments.append({
                 'p1': p1, 
                 'p2': p2, 
                 'length': int(length_cm)
             })
             
        return calc_segments

    def _process_segment_logic(self, length, direction):
        """
        Return list of module lengths to fill the given segment.
        
        Strategy (User Request):
        - Maximize 250cm modules first.
        - If 'prefer_gaps' is False (no-150 filter NOT active):
            - Use 150cm module ONLY if remaining space >= 150cm.
            - This effectively minimizes 150cm usage (max 1 per segment).
        """
        if length < 100:
            # Too short for any module
            return []
        
        scaffs = []
        remaining = length
        
        # 1. Fill with 250cm modules (Greedy)
        while remaining >= 250:
            scaffs.append(250)
            remaining -= 250
        
        # 2. Conditional 150cm usage
        # Revised Strategy (User Request): 
        # "Zorunda kalmadıkça 150cm kullanma" -> Only use 150cm if no 250cm modules could fit.
        # If we already have 250cm modules, prefer leaving a gap rather than mixing 150cm.
        
        if remaining >= 150:
            # Revised Strategy (User Request): 
            # If "prefer_gaps" is True (User used --no-150), we NEVER use 150cm.
            # We strictly prefer leaving a gap.
            if self.prefer_gaps:
                pass
            
            else:
                # Normal logic (prefer_gaps=False means we allow 150cm)
                # Only add 150cm if the segment is too short for a single 250cm module
                # (i.e., this is a short wall segment or corner piece)
                if len(scaffs) == 0:
                    scaffs.append(150)
                    remaining -= 150
                
                # Note: We already removed the logic for filling gaps with 150cm if 250cm exist.
                # So this handles short segments and "zorunda kalmadıkça" logic.
        
        if self.verbose:
            total_modules = sum(scaffs)
            gap = length - total_modules
            self.d.print(f"Segment {length}cm -> modules: {scaffs}, gap: {gap}cm")
            
        # Calculate materials (Side effect)
        segment_slope = 0
        if direction in ['RIGHT', 'LEFT']: 
            segment_slope = self.slope

        frontal_calculator2D(
            length_list=scaffs,
            h=self.height,
            slope=segment_slope, 
            toe_board=True, 
            use_x_pattern=False, 
            use_zigzag_pattern=True,
            material_counter=self.material_counter, 
            counter=self.top_down_counter, 
            d=self.d
        )
        
        return scaffs

