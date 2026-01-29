
def convert_facades_to_segments(facades):
    """
    Convert facade command strings into 2D polyline segments.
    
    Key Design:
    - Each wall is processed in order: F -> R -> B -> L
    - Inset = wall goes INTO building (positive depth)
    - Outset = wall goes OUT of building (negative depth, bay window/protrusion)
    - Depth is CUMULATIVE within a wall
    - At wall end, depth returns to 0 (baseline)
    - Next wall starts from corner position
    
    Coordinate System:
    - F: +X direction, inside = +Y
    - R: +Y direction, inside = -X  
    - B: -X direction, inside = -Y
    - L: -Y direction, inside = +X
    """
    
    scale = 1.0 / 5.0  # pixels per cm
    
    # Direction and inside vectors
    direction_vectors = {
        'F': (1, 0), 'R': (0, 1), 'B': (-1, 0), 'L': (0, -1)
    }
    inside_vectors = {
        'F': (0, 1), 'R': (-1, 0), 'B': (0, -1), 'L': (1, 0)
    }
    
    # First pass: determine wall lengths
    wall_lengths = {}
    for side in ['F', 'R', 'B', 'L']:
        cmds = facades.get(side, [])
        wall_len = 0
        for cmd in cmds:
            parts = str(cmd).split(',')
            if len(parts) >= 3:
                if parts[0] == 'start':
                    wall_len = int(parts[2])
                    break
                else:
                    try:
                        wall_len = int(parts[2])
                    except:
                        pass
        wall_lengths[side] = wall_len
    
    segments = []
    x, y = 0, 0
    
    pending_overlap_depth = 0
    
    # Pre-calculate L (last wall) final depth to set initial overlap for F
    last_side = 'L'
    l_cmds = facades.get(last_side, [])
    if l_cmds:
        l_depth = 0
        for cmd in l_cmds:
            # Standardize parsing: cmd is likely a string "type,pos,length,depth,side"
            parts = str(cmd).split(',')
            if len(parts) >= 2:
                ftype = parts[0].strip().replace("'", "").replace('"', "")
                if ftype in ['inset', 'outset']:
                    try:
                        # Depth is typically at index 3 for standardized commands
                        # But user input might be "inset,pos,depth"
                        # Top_down_main constructs: "type,pos,length,depth,side"
                        # We need to handle both just in case, or rely on standardized index 3
                        # If index 3 exists, use it. Else check index 2.
                        d = 0
                        if len(parts) > 3:
                            d = int(parts[3])
                        elif len(parts) > 2:
                            d = int(parts[2])
                            
                        if ftype == 'inset': l_depth += d
                        elif ftype == 'outset': l_depth -= d
                    except:
                        pass
        
        # Check if L ends with overlap against F
        if l_depth != 0:
            # L End Return Vector
            delta = -l_depth
            if delta > 0:
                rx, ry = inside_vectors[last_side]
            else:
                rx, ry = -inside_vectors[last_side][0], -inside_vectors[last_side][1]
            
            # F Direction
            ndx, ndy = direction_vectors['F']
            
            if rx * ndx + ry * ndy == -1:
                pending_overlap_depth = abs(delta)
    
    # Ordered sides list for circular access
    sides = ['F', 'R', 'B', 'L']
    
    for i, side in enumerate(sides):
        cmds = facades.get(side, [])
        # Apply pending overlap shortening, even if no commands
        wall_len = wall_lengths.get(side, 0)
        
        dx, dy = direction_vectors[side]
        idx, idy = inside_vectors[side]
        
        # Apply pending overlap shortening
        if pending_overlap_depth > 0:
            original_len = wall_len
            wall_len -= pending_overlap_depth
            if wall_len < 0: wall_len = 0
            
            # Note: We do NOT advance x, y here. 
            # We are "starting" effectively further along the intended path, 
            # but physically we are already at the correct overlap position from previous step.
        
        if wall_len <= 0 and not cmds:
             # Just skip if no wall remaining
             pending_overlap_depth = 0
             continue
        
        # Parse features
        features = []
        for cmd in cmds:
            parts = str(cmd).split(',')
            if len(parts) < 2:
                continue
            if parts[0] in ['inset', 'outset']:
                try:
                    pos = int(parts[1])
                    if pending_overlap_depth > 0:
                        pos -= pending_overlap_depth
                        if pos < 0: continue # Feature was in the overlapped (skipped) part
                        
                    depth = int(parts[3]) if len(parts) > 3 else 0
                    features.append({
                        'type': parts[0],
                        'pos': pos,
                        'depth': depth
                    })
                except:
                    pass
        
        # Sort by features position
        features.sort(key=lambda f: f['pos'])
        features.append({'type': 'end', 'pos': wall_len, 'depth': 0})
        
        current_depth = 0
        curr_dist = 0
        
        # Use overlap check reset
        next_pending_overlap = 0

        # Group features by position
        import itertools
        for pos, group_iter in itertools.groupby(features, key=lambda f: f['pos']):
            group = list(group_iter)
            
            # Distance from previous position
            dist_diff = pos - curr_dist
            
            # Draw wall segment
            if dist_diff > 0:
                next_x = x + dx * dist_diff
                next_y = y + dy * dist_diff
                
                segments.append({
                    'p1': {'x': x * scale, 'y': y * scale},
                    'p2': {'x': next_x * scale, 'y': next_y * scale},
                    'length': dist_diff,
                    'direction': side,
                    'is_perpendicular_inset': False
                })
                
                x, y = next_x, next_y
                curr_dist = pos
            
            # Process features at this position
            net_delta = 0
            has_end = False
            
            for ft in group:
                if ft['type'] == 'inset':
                    d = ft['depth']
                elif ft['type'] == 'outset':
                    d = -ft['depth']
                elif ft['type'] == 'end':
                    d = -current_depth
                    has_end = True
                else:
                    d = 0
                
                current_depth += d
                net_delta += d
            
            if net_delta != 0:
                # Check for overlap at the END of the wall
                is_end_overlap = False
                if has_end:
                    # Determine return vector direction
                    if net_delta > 0:
                        rx, ry = idx, idy
                    else:
                        rx, ry = -idx, -idy
                    
                    # Look ahead to next wall direction
                    next_side = sides[(i + 1) % 4]
                    ndx, ndy = direction_vectors[next_side]
                    
                    # Check collinearity
                    dot = rx * ndx + ry * ndy
                    
                    if dot == -1:
                        is_end_overlap = True
                        next_pending_overlap = abs(net_delta)

                if is_end_overlap:
                    # Skip drawing return segment
                    # Do NOT update x, y (stay at depth)
                    pass
                else:
                    if net_delta > 0:
                        # Move INTO building
                        mx, my = idx, idy
                        move_len = net_delta
                    else:
                        # Move OUT OF building
                        mx, my = -idx, -idy
                        move_len = abs(net_delta)
                    
                    ft_x = x + mx * move_len
                    ft_y = y + my * move_len
                    
                    segments.append({
                        'p1': {'x': x * scale, 'y': y * scale},
                        'p2': {'x': ft_x * scale, 'y': ft_y * scale},
                        'length': move_len,
                        'direction': side,
                        'is_perpendicular_inset': True
                    })
                    
                    x, y = ft_x, ft_y
        
        pending_overlap_depth = next_pending_overlap
    
    # Close loop if needed
    close_dist = (x**2 + y**2)**0.5
    if close_dist > 1:
        segments.append({
            'p1': {'x': x * scale, 'y': y * scale},
            'p2': {'x': 0, 'y': 0},
            'length': int(close_dist),
            'direction': 'CLOSE',
            'is_perpendicular_inset': False
        })
    
    return segments
