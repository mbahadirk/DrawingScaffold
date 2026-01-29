"""
Slim version of drawer_top_down.
Only contains essential entry point for backward compatibility.

For detailed facade drawing, use:
- drawscaffold.model.facade_drawer.FacadeDrawer
"""
import os
from datetime import datetime

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


def top_down_drawer(verbose: bool, facades: dict, image: bool, dxf: bool, 
                    svg: bool, project_name: str):
    """
    Main entry point for top-down scaffold drawing.
    
    For OOP version, use:
    FacadeDrawer from drawscaffold.model.facade_drawer
    
    Args:
        verbose: Enable debug output
        facades: Dictionary with F, R, B, L facade commands
        image: Generate PNG output
        dxf: Generate DXF output
        svg: Generate SVG output
        project_name: Base name for output files
        
    Returns:
        List of generated file paths
    """
    d = DebugPrinter(verbose)
    
    # Initialize DXF document
    doc = ezdxf.new("R2018")
    doc.units = units.CM
    
    scaff_layer = doc.layers.add("scaff")
    scaff_layer.description = 'by ScaffAI'
    
    msp = doc.modelspace()
    drawer = DrawerTopView(msp, doc)
    
    # Draw building outline
    drawer.line_building(facades)
    
    # Draw scaffolds using simplified logic
    _draw_all_facades(facades, drawer, d)
    
    # Generate outputs
    return _save_outputs(doc, msp, project_name, image, dxf, svg)


def _draw_all_facades(facades: dict, drawer: DrawerTopView, d: DebugPrinter, gap: int = 25):
    """Draw scaffolding for all facades."""
    from drawscaffold.model.direction import DIRECTIONS, calculate_modules, parse_facade_command
    
    pos = (0, 0)
    
    for key in ['F', 'R', 'B', 'L']:
        if key not in facades or not facades[key]:
            continue
        
        direction = DIRECTIONS[key]
        
        # Apply gap offset
        pos = (
            pos[0] + direction.gap_offset[0],
            pos[1] + direction.gap_offset[1]
        )
        
        # Get total length from last command
        total_length = _get_total_length(facades[key])
        
        # Process commands
        for cmd_str in facades[key]:
            cmd = parse_facade_command(cmd_str)
            if cmd is None:
                continue
            
            d.print(f"Drawing {cmd['func']} pos={cmd['pos']} depth={cmd['depth']}")
            
            # Calculate and draw modules
            modules = calculate_modules(cmd['pos'])
            pos = _draw_segment(pos, modules, direction, drawer)
            
            # Draw depth if any
            if cmd['depth'] > 0:
                depth_modules = calculate_modules(cmd['depth'])
                pos = _draw_depth_segment(pos, depth_modules, direction, drawer)
        
        # Draw remaining segment
        remaining = calculate_modules(total_length)
        pos = _draw_segment(pos, remaining, direction, drawer)


def _draw_segment(pos, modules, direction, drawer):
    """Draw a row of scaffold modules."""
    x, y = pos
    
    for module_len in modules:
        is_small = (module_len == 150)
        drawer.draw_scaffold((x, y), small=is_small, console_count=0, 
                            scaffold_side=direction.scaffold_side)
        x += direction.dx * module_len
        y += direction.dy * module_len
    
    return (x, y)


def _draw_depth_segment(pos, modules, direction, drawer):
    """Draw depth segment (perpendicular to main direction)."""
    x, y = pos
    dx, dy = direction.depth_dx, direction.depth_dy
    
    for module_len in modules:
        is_small = (module_len == 150)
        drawer.draw_scaffold((x, y), small=is_small, console_count=0,
                            scaffold_side=direction.scaffold_side)
        x += dx * module_len
        y += dy * module_len
    
    return (x, y)


def _get_total_length(commands):
    """Get total length from facade commands."""
    if not commands:
        return 0
    
    from drawscaffold.model.direction import parse_facade_command
    last_cmd = parse_facade_command(commands[-1])
    return last_cmd['length'] if last_cmd else 0


def _save_outputs(doc, msp, project_name, image, dxf, svg):
    """Save generated outputs to files."""
    file_paths = []
    timestamp = datetime.now().timestamp()
    project_name = project_name.replace(' ', '_')
    
    if image:
        path = _save_png(doc, msp, project_name, timestamp)
        file_paths.append(path)
    
    if svg:
        path = _save_svg(doc, msp, project_name, timestamp)
        file_paths.append(path)
    
    if dxf:
        path = _save_dxf(doc, msp, project_name, timestamp)
        file_paths.append(path)
    
    # Generate thumbnail
    if any([image, dxf, svg]):
        thumb_path = _save_thumbnail(doc, msp, project_name, timestamp)
        file_paths.append(thumb_path)
    
    return file_paths


def _save_png(doc, msp, project_name, timestamp):
    """Save PNG output."""
    context = RenderContext(doc)
    backend = SVGBackend()
    Frontend(context, backend).draw_layout(msp, finalize=True)
    
    page = layout.Page(210, 297, layout.Units.mm, margins=layout.Margins.all(20))
    svg_path = os.path.abspath(f"{project_name}_top_down_{timestamp}.svg")
    png_path = os.path.abspath(f"{project_name}_top_down_{timestamp}.png")
    
    with open(svg_path, "wt", encoding="utf-8") as f:
        f.write(backend.get_string(page))
    
    cairosvg.svg2png(url=svg_path, write_to=png_path, dpi=300)
    os.remove(svg_path)
    
    return png_path


def _save_svg(doc, msp, project_name, timestamp):
    """Save SVG output with swapped colors."""
    context = RenderContext(doc)
    backend = SVGBackend()
    config = Configuration(color_policy=ColorPolicy.COLOR_SWAP_BW)
    Frontend(context, backend, config).draw_layout(msp, finalize=True)
    
    page = layout.Page(210, 297, layout.Units.mm, margins=layout.Margins.all(20))
    svg_path = os.path.abspath(f"{project_name}_top_down_{timestamp}.svg")
    
    with open(svg_path, "wt", encoding="utf-8") as f:
        f.write(backend.get_string(page))
    
    return svg_path


def _save_dxf(doc, msp, project_name, timestamp):
    """Save DXF output with proper extents."""
    ext = bbox.extents(msp)
    if ext is not None:
        (xmin, ymin, _), (xmax, ymax, _) = ext.extmin, ext.extmax
        msp.dxf_layout.dxf.extmin = ezdxf.math.Vec3(xmin, ymin, 0)
        msp.dxf_layout.dxf.extmax = ezdxf.math.Vec3(xmax, ymax, 0)
        doc.header["$EXTMIN"] = msp.dxf_layout.dxf.extmin
        doc.header["$EXTMAX"] = msp.dxf_layout.dxf.extmax
    
    # Explode text for compatibility
    with MTextExplode(msp) as xpl:
        for m in list(msp.query("MTEXT")):
            xpl.explode(m)
    
    for t in list(msp.query("TEXT")):
        text2path.explode(t, target=msp)
    
    dxf_path = os.path.abspath(f"{project_name}_{timestamp}.dxf")
    doc.saveas(dxf_path)
    
    return dxf_path


def _save_thumbnail(doc, msp, project_name, timestamp):
    """Save JPG thumbnail."""
    context = RenderContext(doc)
    backend = SVGBackend()
    Frontend(context, backend).draw_layout(msp, finalize=True)
    
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
