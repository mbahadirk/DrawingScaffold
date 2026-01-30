import os
import math
import ezdxf
import cairosvg
from PIL import Image
from ezdxf import units
from ezdxf.addons.drawing import RenderContext, Frontend, layout
from ezdxf.addons.drawing.svg import SVGBackend
from drawscaffold.shapes.shapes_top_down import DrawerTopView
from drawscaffold.const.top_down_enum import ScaffoldSide

class SegmentDrawer:
    def __init__(self, verbose=False):
        self.verbose = verbose
        
    def _calculate_signed_area(self, segments):
        # Polymer Signed Area: 0.5 * sum(x_i*y_i+1 - x_i+1*y_i)
        area = 0.0
        for seg in segments:
            p1 = seg['p1']
            p2 = seg['p2']
            area += (p1['x'] * p2['y'] - p2['x'] * p1['y'])
        return 0.5 * area

    def _is_clockwise(self, area):
        # In Canvas coords (Y Down), Positive Area = CW?
        # Standard: Sum(x1y2 - x2y1).
        # Rectangle: (0,0)->(10,0)->(10,10)->(0,10)->(0,0) [CW visual]
        # 1. 0*0 - 10*0 = 0
        # 2. 10*10 - 10*0 = 100
        # 3. 10*10 - 0*10 = 100
        # 4. 0*0 - 0*10 = 0
        # Sum = 200. Positive.
        # So CW is Positive in Canvas Coords.
        return area > 0

    def draw_project(self, point_segments, filename):
        """
        point_segments: List of dicts with 
        {
          'wall_p1': (x,y), 'wall_p2': (x,y), 
          'scaff_p1': (x,y), 'scaff_p2': (x,y),
          'length': cm, 
          'modules': [250, 250, 150...]
        }
        """
        
        # Initialize DXF Doc
        doc = ezdxf.new("R2018")
        doc.units = units.CM
        scaff_layer = doc.layers.add("scaff")
        msp = doc.modelspace()
        
        drawer = DrawerTopView(msp, doc)
        
        for seg in point_segments:
            # Scale Factors (1px = 5cm)
            # Flip Y (Screen Y is Down, CAD Y is Up. To match visuals, mapped Y should be negative)
            SX = 5.0
            SY = -5.0
            
            # Wall Drawing (Red)
            w1 = seg['wall_p1']
            w2 = seg['wall_p2']
            w1_x, w1_y = w1['x'] * SX, w1['y'] * SY
            w2_x, w2_y = w2['x'] * SX, w2['y'] * SY
            
            msp.add_lwpolyline([(w1_x, w1_y), (w2_x, w2_y)], close=False, dxfattribs={'color': 1, 'lineweight': 30})
            
            # Scaffold Drawing (Modules)
            # Use Pre-Calculated Scaffold Geometry
            s1 = seg['scaff_p1']
            s2 = seg['scaff_p2']
            modules = seg['modules']
            
            s1_x, s1_y = s1['x'] * SX, s1['y'] * SY
            s2_x, s2_y = s2['x'] * SX, s2['y'] * SY
            
            # Calculate Vector for Orientation from Scaled Points
            dx = s2_x - s1_x
            dy = s2_y - s1_y
            
            # If length is tiny (inner corner collapse), skip drawing modules
            dist = math.hypot(dx, dy)
            if dist < 1: continue
            
            dir_x = dx / dist
            dir_y = dy / dist
            
            # Angle for Rotation (Parallel to Scaffold Line)
            raw_angle = math.degrees(math.atan2(dy, dx))
            target_rotation = (raw_angle + 90) % 360
            
            # Map to ScaffoldSide
            side = ScaffoldSide.LEFT
            if 45 <= target_rotation < 135: 
                side = ScaffoldSide.BACK 
            elif 135 <= target_rotation < 225: 
                side = ScaffoldSide.RIGHT
            elif 225 <= target_rotation < 315: 
                side = ScaffoldSide.FRONT
            
            # Calculate total module length and gap
            total_module_length = sum(modules)
            gap = dist - total_module_length
            
            # Determine Alignment (Default to Center)
            alignment = seg.get('alignment', 'center')
            
            if alignment == 'start':
                start_offset = 0.0
            elif alignment == 'end':
                start_offset = gap
            else:
                # Center
                start_offset = gap / 2.0
                
            # If gap is negative (overhang), start_offset checks:
            # Start (0): Starts at P1. Ends strictly past P2? Yes. (P1 Flush)
            # End (gap): Starts before P1. Ends at P2. (P2 Flush)
            
            current_x = s1_x + dir_x * start_offset
            current_y = s1_y + dir_y * start_offset
            
            for mod_len in modules:
                is_small = (mod_len == 150)
                
                # Draw the scaffold module
                drawer.draw_scaffold((current_x, current_y), small=is_small, console_count=0, scaffold_side=side)
                
                # Advance position
                current_x += dir_x * mod_len
                current_y += dir_y * mod_len
        # Save logic (Copied from legacy)
        return self._save_file(doc, msp, filename)

    def _save_file(self, doc, msp, project_name):
        import time
        timestamp = time.time()
        file_paths = []
        
        # Save PNG
        context = RenderContext(doc)
        backend = SVGBackend()
        Frontend(context, backend).draw_layout(msp, finalize=True)
        
        # Auto-size page to content?
        # bbox = ezdxf.bbox.extents(msp)
        # Using fixed page for now as per legacy
        
        svg_path = os.path.abspath(f"{project_name}.svg")
        png_path = os.path.abspath(f"{project_name}.png")
        dxf_path = os.path.abspath(f"{project_name}.dxf")
        
        # Save DXF
        doc.saveas(dxf_path)
        
        with open(svg_path, "wt", encoding="utf-8") as f:
            f.write(backend.get_string(layout.Page(210, 297, layout.Units.mm, margins=layout.Margins.all(20))))
            
        cairosvg.svg2png(url=svg_path, write_to=png_path, dpi=300)
        # if os.path.exists(svg_path): os.remove(svg_path) # Keep SVG
        
        return png_path
