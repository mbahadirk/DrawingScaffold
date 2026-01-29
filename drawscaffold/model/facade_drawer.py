"""
OOP-based facade drawer for scaffold visualization.
Refactored from drawer_top_down.py for better maintainability.
"""
import os
from datetime import datetime
from typing import List, Dict, Tuple, Optional

import cairosvg
import ezdxf
from PIL import Image
from ezdxf import units, bbox
from ezdxf.addons import MTextExplode, text2path
from ezdxf.addons.drawing import RenderContext, Frontend, layout
from ezdxf.addons.drawing.config import Configuration, ColorPolicy
from ezdxf.addons.drawing.svg import SVGBackend

from drawscaffold.const.top_down_enum import ScaffoldSide
from drawscaffold.shapes.shapes_top_down import DrawerTopView
from drawscaffold.utils.debug_printer import DebugPrinter
from drawscaffold.model.direction import (
    Direction, DIRECTIONS, calculate_modules, parse_facade_command
)


class FacadeSegmentDrawer:
    """Draws scaffold segments for a single facade direction."""
    
    def __init__(self, drawer: DrawerTopView, debug: DebugPrinter, gap: int = 25):
        self.drawer = drawer
        self.debug = debug
        self.gap = gap
    
    def draw_segment(self, start_pos: Tuple[float, float], 
                     modules: List[int],
                     direction: Direction,
                     console_count: int = 0) -> Tuple[float, float]:
        """
        Draw a scaffold segment starting from given position.
        
        Args:
            start_pos: Starting (x, y) position
            modules: List of module lengths [250, 250, 150, ...]
            direction: Direction object with dx, dy vectors
            console_count: Number of console attachments
            
        Returns:
            New (x, y) position after drawing
        """
        x, y = start_pos
        
        for module_len in modules:
            is_small = (module_len == 150)
            
            # Draw scaffold at current position
            self.drawer.draw_scaffold(
                (x, y), 
                small=is_small, 
                console_count=console_count,
                scaffold_side=direction.scaffold_side
            )
            
            # Move to next position
            x += direction.dx * module_len
            y += direction.dy * module_len
        
        return (x, y)
    
    def draw_depth_segment(self, start_pos: Tuple[float, float],
                           modules: List[int],
                           direction: Direction,
                           console_count: int = 0) -> Tuple[float, float]:
        """
        Draw a depth segment (perpendicular to main direction).
        
        Args:
            start_pos: Starting position
            modules: Module lengths
            direction: Main direction (will use perpendicular)
            console_count: Console attachments
            
        Returns:
            New position after drawing
        """
        x, y = start_pos
        dx, dy = direction.depth_dx, direction.depth_dy
        
        for module_len in modules:
            is_small = (module_len == 150)
            
            self.drawer.draw_scaffold(
                (x, y),
                small=is_small,
                console_count=console_count,
                scaffold_side=direction.scaffold_side
            )
            
            x += dx * module_len
            y += dy * module_len
        
        return (x, y)


class FacadeDrawer:
    """
    Main facade drawing coordinator.
    Handles all facades and output generation.
    """
    
    def __init__(self, verbose: bool = False, gap: int = 25):
        self.verbose = verbose
        self.gap = gap
        self.debug = DebugPrinter(verbose)
        
        # DXF document
        self.doc = ezdxf.new("R2018")
        self.doc.units = units.CM
        
        scaff_layer = self.doc.layers.add("scaff")
        scaff_layer.description = 'by ScaffAI'
        
        self.msp = self.doc.modelspace()
        self.drawer = DrawerTopView(self.msp, self.doc)
        
        self.segment_drawer = FacadeSegmentDrawer(
            self.drawer, self.debug, gap
        )
    
    def draw_facades(self, facades: Dict[str, List]):
        """
        Draw all facades with their scaffolding.
        
        Args:
            facades: Dictionary with F, R, B, L facade commands
        """
        # Draw building outline
        self.drawer.line_building(facades)
        
        # Track position around building
        pos = (0, 0)
        
        for key in ['F', 'R', 'B', 'L']:
            if key not in facades or not facades[key]:
                continue
            
            direction = DIRECTIONS[key]
            pos = self._draw_facade(facades[key], direction, pos)
    
    def _draw_facade(self, commands: List[str], direction: Direction,
                     start_pos: Tuple[float, float]) -> Tuple[float, float]:
        """
        Draw scaffolding for a single facade.
        
        Args:
            commands: List of facade command strings
            direction: Direction object
            start_pos: Starting position
            
        Returns:
            Position after drawing this facade
        """
        # Apply gap offset
        pos = (
            start_pos[0] + direction.gap_offset[0],
            start_pos[1] + direction.gap_offset[1]
        )
        
        # Get total length from last command
        total_length = self._get_total_length(commands)
        console_count = 0
        
        for cmd_str in commands:
            cmd = parse_facade_command(cmd_str)
            if cmd is None:
                continue
            
            self.debug.print(f"Drawing {cmd['func']} at pos={cmd['pos']}")
            
            # Calculate modules
            length = cmd['length']
            depth = cmd['depth']
            
            main_modules = calculate_modules(cmd['pos'])
            depth_modules = calculate_modules(depth)
            
            if cmd['func'] == 'inset':
                pos = self._draw_inset(pos, cmd, direction, main_modules, depth_modules)
            elif cmd['func'] == 'outset':
                pos = self._draw_outset(pos, cmd, direction, main_modules, depth_modules)
        
        # Draw remaining segment to complete facade
        final_modules = calculate_modules(total_length)
        pos = self.segment_drawer.draw_segment(pos, final_modules, direction)
        
        return pos
    
    def _draw_inset(self, pos: Tuple[float, float], cmd: dict,
                    direction: Direction, main_modules: List[int],
                    depth_modules: List[int]) -> Tuple[float, float]:
        """Draw an inset (wall steps back from baseline)."""
        # Draw main segment
        pos = self.segment_drawer.draw_segment(pos, main_modules, direction)
        
        # Draw depth segment (perpendicular, going inward)
        pos = self.segment_drawer.draw_depth_segment(
            pos, depth_modules, direction
        )
        
        return pos
    
    def _draw_outset(self, pos: Tuple[float, float], cmd: dict,
                     direction: Direction, main_modules: List[int],
                     depth_modules: List[int]) -> Tuple[float, float]:
        """Draw an outset (wall steps forward from baseline)."""
        # Draw main segment
        pos = self.segment_drawer.draw_segment(pos, main_modules, direction)
        
        # Draw depth segment (perpendicular, going outward)
        pos = self.segment_drawer.draw_depth_segment(
            pos, depth_modules, direction
        )
        
        return pos
    
    def _get_total_length(self, commands: List[str]) -> int:
        """Get total length from facade commands."""
        if not commands:
            return 0
        
        last_cmd = parse_facade_command(commands[-1])
        return last_cmd['length'] if last_cmd else 0
    
    def save_outputs(self, project_name: str, 
                     image: bool = True, 
                     dxf: bool = False, 
                     svg: bool = False) -> List[str]:
        """
        Save outputs to files.
        
        Args:
            project_name: Base name for output files
            image: Generate PNG
            dxf: Generate DXF
            svg: Generate SVG
            
        Returns:
            List of generated file paths
        """
        file_paths = []
        timestamp = datetime.now().timestamp()
        project_name = project_name.replace(' ', '_')
        
        if image:
            path = self._save_png(project_name, timestamp)
            file_paths.append(path)
        
        if svg:
            path = self._save_svg(project_name, timestamp)
            file_paths.append(path)
        
        if dxf:
            path = self._save_dxf(project_name, timestamp)
            file_paths.append(path)
        
        # Generate thumbnail
        if any([image, dxf, svg]):
            thumb_path = self._save_thumbnail(project_name, timestamp)
            file_paths.append(thumb_path)
        
        return file_paths
    
    def _save_png(self, project_name: str, timestamp: float) -> str:
        """Save PNG output."""
        context = RenderContext(self.doc)
        backend = SVGBackend()
        Frontend(context, backend).draw_layout(self.msp, finalize=True)
        
        page = layout.Page(210, 297, layout.Units.mm, margins=layout.Margins.all(20))
        svg_path = os.path.abspath(f"{project_name}_top_down_{timestamp}.svg")
        png_path = os.path.abspath(f"{project_name}_top_down_{timestamp}.png")
        
        with open(svg_path, "wt", encoding="utf-8") as f:
            f.write(backend.get_string(page))
        
        cairosvg.svg2png(url=svg_path, write_to=png_path, dpi=300)
        os.remove(svg_path)
        
        return png_path
    
    def _save_svg(self, project_name: str, timestamp: float) -> str:
        """Save SVG output with swapped colors."""
        context = RenderContext(self.doc)
        backend = SVGBackend()
        config = Configuration(color_policy=ColorPolicy.COLOR_SWAP_BW)
        Frontend(context, backend, config).draw_layout(self.msp, finalize=True)
        
        page = layout.Page(210, 297, layout.Units.mm, margins=layout.Margins.all(20))
        svg_path = os.path.abspath(f"{project_name}_top_down_{timestamp}.svg")
        
        with open(svg_path, "wt", encoding="utf-8") as f:
            f.write(backend.get_string(page))
        
        return svg_path
    
    def _save_dxf(self, project_name: str, timestamp: float) -> str:
        """Save DXF output with proper extents."""
        ext = bbox.extents(self.msp)
        if ext is not None:
            (xmin, ymin, _), (xmax, ymax, _) = ext.extmin, ext.extmax
            self.msp.dxf_layout.dxf.extmin = ezdxf.math.Vec3(xmin, ymin, 0)
            self.msp.dxf_layout.dxf.extmax = ezdxf.math.Vec3(xmax, ymax, 0)
            self.doc.header["$EXTMIN"] = self.msp.dxf_layout.dxf.extmin
            self.doc.header["$EXTMAX"] = self.msp.dxf_layout.dxf.extmax
        
        # Explode text for compatibility
        with MTextExplode(self.msp) as xpl:
            for m in list(self.msp.query("MTEXT")):
                xpl.explode(m)
        
        for t in list(self.msp.query("TEXT")):
            text2path.explode(t, target=self.msp)
        
        dxf_path = os.path.abspath(f"{project_name}_{timestamp}.dxf")
        self.doc.saveas(dxf_path)
        
        return dxf_path
    
    def _save_thumbnail(self, project_name: str, timestamp: float) -> str:
        """Save JPG thumbnail."""
        context = RenderContext(self.doc)
        backend = SVGBackend()
        Frontend(context, backend).draw_layout(self.msp, finalize=True)
        
        page = layout.Page(210, 297, layout.Units.mm, margins=layout.Margins.all(20))
        svg_path = os.path.abspath(f"{project_name}_temp_{timestamp}.svg")
        png_path = os.path.abspath(f"{project_name}_temp_{timestamp}.png")
        jpg_path = os.path.abspath(f"{project_name}_{timestamp}.jpg")
        
        with open(svg_path, "wt", encoding="utf-8") as f:
            f.write(backend.get_string(page))
        
        cairosvg.svg2png(url=svg_path, write_to=png_path, dpi=300)
        
        png_image = Image.open(png_path)
        rgb_im = png_image.convert("RGB")
        rgb_im.save(jpg_path)
        
        os.remove(svg_path)
        os.remove(png_path)
        
        return jpg_path


# Backward compatibility function
def top_down_drawer(verbose: bool, facades: dict, image: bool, dxf: bool, 
                    svg: bool, project_name: str) -> List[str]:
    """
    Legacy entry point for facade drawing.
    Wraps FacadeDrawer for backward compatibility.
    """
    drawer = FacadeDrawer(verbose=verbose)
    drawer.draw_facades(facades)
    return drawer.save_outputs(project_name, image=image, dxf=dxf, svg=svg)
