import os
from datetime import datetime
from typing import Sequence

import ezdxf
from ezdxf import units, bbox
from ezdxf.addons import MTextExplode, text2path
from ezdxf.addons.drawing.config import Configuration, ColorPolicy
from ezdxf.math import Vec3
from ezdxf.addons.drawing import RenderContext, Frontend, layout
from ezdxf.addons.drawing.svg import SVGBackend
import cairosvg
from math import radians, cos, sin, tan

from PIL import Image

from drawscaffold.const.conts import HORIZONTAL_PART, VERTICAL_PART, SURFACE_COLOR, FOOT_PART, FOOT_INSIDE_PART, \
    ADJUSTMENT_SHAFT1, ADJUSTMENT_SHAFT2, HALF_FOOT_PART, ADJUSTMENT_SHAFT3, COMPLETE_FOOT_PART, HALF_VERTICAL_PART, \
    SUPPORT_SPACE, DIAGONAL_PART
from drawscaffold.diagonal.patterns.x_pattern import draw_x_diagonal_pattern
from drawscaffold.diagonal.patterns.zigzag_pattern import draw_zigzag_diagonal_pattern
from drawscaffold.shapes.shapes_2d import Drawer2D
from drawscaffold.utils.debug_printer import DebugPrinter


def two_d_drawer(verbose:bool, h: float, w: float, slope: float, toe_text: str | None,
                 r_diagonal: bool, surface_line: bool, biggest_surface_line: bool,
                 use_x_pattern: bool, use_zigzag_pattern: bool, use_best_pattern: bool,
                 svg: bool, image: bool, dxf: bool, project_name: str):
    d = DebugPrinter(verbose)

    floor_count = int(h // (VERTICAL_PART - 20))
    floor_gap = h % (VERTICAL_PART - 20)

    module_count = int(w // HORIZONTAL_PART)

    doc = ezdxf.new("R2018")
    doc.units = units.CM

    scaff_layer = doc.layers.add("scaff")
    scaff_layer.description = 'by ScaffAI'

    msp = doc.modelspace()

    d.print(f'kat sayısı: {floor_count}')
    d.print(f'kat boşluğu: {floor_gap}')
    d.print(f'modül sayısı: {module_count}')

    vertical_point = 0

    def y_on_surface(x, width_cm, base_y, slope_deg):
        x0 = width_cm / 2.0      # çizimdeki pivot orta nokta
        m = tan(radians(slope_deg))
        return base_y - m * (x - x0)

    def _rot2d(p, angle_deg, pivot):
        a = radians(angle_deg)
        x, y = p[0] - pivot[0], p[1] - pivot[1]
        xr = x*cos(a) - y*sin(a)
        yr = x*sin(a) + y*cos(a)
        return xr + pivot[0], yr + pivot[1]

    def draw_line(start: Sequence[float], end: Sequence[float], color: int, rotate_angle: float=0, pivot=None):
        z_start = start[2] if len(start) > 2 else 0.0
        z_end = end[2] if len(end) > 2 else z_start

        if pivot is None:
            pivot = ((start[0] + end[0]) / 2.0, (start[1] + end[1]) / 2.0)

        rs = _rot2d((start[0], start[1]), rotate_angle, pivot)
        re = _rot2d((end[0], end[1]), rotate_angle, pivot)

        line = msp.add_line((rs[0], rs[1], z_start), (re[0], re[1], z_end),
                            dxfattribs={'layer': 'scaff'})

        line.dxf.color = color
        line.dxf.extrusion = Vec3(0, 1, 0)

    surface_slope_start = (-300, vertical_point)
    surface_slope_end = (300 + w, vertical_point)

    if surface_line:
        draw_line(surface_slope_start, surface_slope_end, color=SURFACE_COLOR, rotate_angle=(180 - slope))

    # calculate start points if surface have slope
    start_points = []
    surface_horizontal = 0
    for i in range(module_count+1):
        surface_point = y_on_surface(surface_horizontal, w, 0, slope)
        start_points.append(surface_point)

        surface_horizontal += HORIZONTAL_PART

    d.print(start_points)
    biggest_point = max(start_points)

    # YÜKSEKLİK ÇİZGİSİ
    if biggest_surface_line:
        draw_line((-300, biggest_point), (w+300, biggest_point), color=7)

    drawer = Drawer2D(msp, doc)
    # make it zero
    start_x_points = 0
    module_idx = 0
    connection_centers = [[] for i in range(module_count + 1)]

    for start_point in start_points:
        difference = biggest_point - start_point

        if difference < 0:
            d.print("mesafe 0'dan küçük geçiyoruz burayı ki bu mümkün olmamalı")
        elif difference == 0:
            foot_start = (start_x_points, start_point)
            lock_center = drawer.draw_foot(foot_start, lock_start_y=start_point+0.5)

            connection_centers[module_idx].append(lock_center)

        elif difference >= (VERTICAL_PART - 20):
            gap = difference % (VERTICAL_PART - 20)
            vertical_count = int(difference // (VERTICAL_PART - 20))

            if gap <= (FOOT_PART - FOOT_INSIDE_PART):
                foot_y = FOOT_PART - FOOT_INSIDE_PART
                foot_start = (start_x_points, start_point)
                lock_center = drawer.draw_foot(foot_start, lock_start_y=start_point + gap)

                connection_centers[module_idx].append(lock_center)

                last_y = foot_start[1] + gap
            elif gap <= (ADJUSTMENT_SHAFT1*0.8):
                lock_center = drawer.draw_adjustment((start_x_points, start_point), ADJUSTMENT_SHAFT1, gap)
                connection_centers[module_idx].append(lock_center)

                last_y = start_point + gap
            elif gap <= (ADJUSTMENT_SHAFT2*0.8):
                lock_center = drawer.draw_adjustment((start_x_points, start_point), ADJUSTMENT_SHAFT2, gap)

                connection_centers[module_idx].append(lock_center)
                last_y = start_point + gap
            elif gap <= (HALF_FOOT_PART - FOOT_INSIDE_PART):
                foot_y = HALF_FOOT_PART - FOOT_INSIDE_PART
                foot_start = (start_x_points, start_point)
                lock_center = drawer.draw_foot(foot_start, half_foot=True, lock_start_y=start_point + gap)

                connection_centers[module_idx].append(lock_center)
                last_y = foot_start[1] + gap
            elif gap <= (ADJUSTMENT_SHAFT3*0.8):
                lock_center = drawer.draw_adjustment((start_x_points, start_point), ADJUSTMENT_SHAFT3, gap)

                connection_centers[module_idx].append(lock_center)
                last_y = start_point + gap
            elif gap - (HALF_VERTICAL_PART - 20) <= (FOOT_PART - FOOT_INSIDE_PART):
                after_gap = gap - (HALF_VERTICAL_PART - 20)

                lock_y = start_point + after_gap
                drawer.draw_foot(start_point=(start_x_points, start_point), lock_start_y=lock_y)

                last_y = lock_y

                lock_center = drawer.draw_vertical(start_point=(start_x_points, last_y), half_vertical=True)
                connection_centers[module_idx].append(lock_center)

                last_y += (HALF_VERTICAL_PART - 20)

            elif gap - (HALF_VERTICAL_PART - 20) <= (HALF_FOOT_PART - FOOT_INSIDE_PART):
                after_gap = gap - (HALF_VERTICAL_PART - 20)

                lock_y = start_point + after_gap
                drawer.draw_foot(start_point=(start_x_points, start_point), half_foot=True, lock_start_y=lock_y)

                last_y = lock_y

                lock_center = drawer.draw_vertical(start_point=(start_x_points, last_y), half_vertical=True)
                connection_centers[module_idx].append(lock_center)

                last_y += (HALF_VERTICAL_PART - 20)
            elif gap <= (COMPLETE_FOOT_PART - FOOT_INSIDE_PART):
                foot_y = COMPLETE_FOOT_PART - FOOT_INSIDE_PART
                foot_start = (start_x_points, start_point)
                lock_center = drawer.draw_foot(foot_start, complete_foot=True, lock_start_y=start_point + gap)
                connection_centers[module_idx].append(lock_center)

                last_y = foot_start[1] + gap
            else:
                foot_y = COMPLETE_FOOT_PART - FOOT_INSIDE_PART
                slide_cm = gap - foot_y
                foot_start = (start_x_points, start_point + slide_cm)
                lock_center = drawer.draw_foot(foot_start, complete_foot=True)
                connection_centers[module_idx].append(lock_center)

                last_y = foot_start[1] + foot_y

                lock_center = drawer.draw_vertical((start_x_points, last_y))
                connection_centers[module_idx].append(lock_center)

                last_y += (VERTICAL_PART-20)

            for vertical in range(vertical_count):
                lock_center = drawer.draw_vertical((start_x_points, last_y))
                connection_centers[module_idx].append(lock_center)

                last_y += (VERTICAL_PART - 20)

        elif difference <= (FOOT_PART - FOOT_INSIDE_PART):
            foot_start = (start_x_points, start_point)

            lock_center = drawer.draw_foot(foot_start, lock_start_y=start_point + difference)
            connection_centers[module_idx].append(lock_center)
        elif difference <= (ADJUSTMENT_SHAFT1*0.8):
            slide_cm = (ADJUSTMENT_SHAFT1*0.8) - difference
            adj_start = (start_x_points, start_point - slide_cm)

            lock_center = drawer.draw_adjustment(adj_start, ADJUSTMENT_SHAFT1, difference)
            connection_centers[module_idx].append(lock_center)
        elif difference <= (ADJUSTMENT_SHAFT2*0.8):
            slide_cm = (ADJUSTMENT_SHAFT2*0.8) - difference
            adj_start = (start_x_points, start_point - slide_cm)

            lock_center = drawer.draw_adjustment(adj_start, ADJUSTMENT_SHAFT2, difference)
            connection_centers[module_idx].append(lock_center)
        elif difference <= (HALF_FOOT_PART - FOOT_INSIDE_PART):
            foot_start = (start_x_points, start_point)

            lock_center = drawer.draw_foot(foot_start, half_foot=True, lock_start_y=start_point + difference)
            connection_centers[module_idx].append(lock_center)
        elif difference <= (ADJUSTMENT_SHAFT3*0.8):
            slide_cm = (ADJUSTMENT_SHAFT3*0.8) - difference
            adj_start = (start_x_points, start_point - slide_cm)

            lock_center = drawer.draw_adjustment(adj_start, ADJUSTMENT_SHAFT3, difference)
            connection_centers[module_idx].append(lock_center)
        elif difference <= (COMPLETE_FOOT_PART - FOOT_INSIDE_PART):
            foot_start = (start_x_points, start_point)

            lock_center = drawer.draw_foot(foot_start, complete_foot=True, lock_start_y=start_point + difference)
            connection_centers[module_idx].append(lock_center)
        else:
            slide_cm = difference - (COMPLETE_FOOT_PART - FOOT_INSIDE_PART)
            foot_start = (start_x_points, start_point + slide_cm)

            lock_center = drawer.draw_foot(foot_start, complete_foot=True)
            connection_centers[module_idx].append(lock_center)

        start_x_points += HORIZONTAL_PART
        module_idx += 1

    vertical_point = biggest_point
    for vertical in range(floor_count):
        horizontal_point = 0
        connection_index = 0
        use_l_part = vertical == floor_count-1
        is_first_floor = vertical == 0
        for module in range(module_count):
            if use_l_part:
                l_part_connection_center = drawer.draw_L_part((horizontal_point, vertical_point))
                connection_centers[connection_index].append(l_part_connection_center)
            else:
                vertical_connection_center = drawer.draw_vertical((horizontal_point, vertical_point))
                connection_centers[connection_index].append(vertical_connection_center)

            floor_support_point = vertical_point

            support_point1 = floor_support_point + SUPPORT_SPACE
            support_point2 = support_point1 + SUPPORT_SPACE

            if toe_text and not is_first_floor:
                drawer.draw_sign((horizontal_point, floor_support_point), toe_text)

            drawer.draw_horizontal((horizontal_point, floor_support_point))

            drawer.draw_support((horizontal_point, support_point1))
            drawer.draw_support((horizontal_point, support_point2))

            horizontal_point += HORIZONTAL_PART

            connection_index+=1
        if use_l_part:
            vertical_connection_center = drawer.draw_L_part((horizontal_point, vertical_point))
        else:
            vertical_connection_center = drawer.draw_vertical((horizontal_point, vertical_point))
        connection_centers[connection_index].append(vertical_connection_center)

        vertical_point += (VERTICAL_PART - 20)

    if use_zigzag_pattern:
        diagonal_indexes = draw_zigzag_diagonal_pattern(
            connection_centers, drawer, module_count, DIAGONAL_PART, VERTICAL_PART, r_diagonal
        )
        d.print(diagonal_indexes)
    if use_x_pattern:
        draw_x_diagonal_pattern(connection_centers, drawer, module_count, floor_count)

    file_paths = []
    timestamp = datetime.now().timestamp()
    project_name_parts = project_name.split(' ')
    project_name = "_".join(project_name_parts)

    if image:
        context = RenderContext(doc)
        backend = SVGBackend()
        Frontend(context, backend).draw_layout(msp, finalize=True)

        page = layout.Page(210, 297, layout.Units.mm, margins=layout.Margins.all(20))
        svg_path = os.path.abspath(f"{project_name}_{timestamp}.svg")
        png_path = os.path.abspath(f"{project_name}_{timestamp}.png")

        with open(svg_path, "wt", encoding="utf-8") as f:
            f.write(backend.get_string(page))

        cairosvg.svg2png(url=svg_path, write_to=png_path, dpi=300)
        os.remove(svg_path)
        file_paths.append(png_path)
    if svg:
        context = RenderContext(doc)
        backend = SVGBackend()
        Frontend(context, backend, Configuration(color_policy=ColorPolicy.COLOR_SWAP_BW)).draw_layout(msp, finalize=True)

        page = layout.Page(210, 297, layout.Units.mm, margins=layout.Margins.all(20))
        svg_path = os.path.abspath(f"{project_name}_{timestamp}.svg")

        with open(svg_path, "wt", encoding="utf-8") as f:
            f.write(backend.get_string(page))

        file_paths.append(svg_path)

    if dxf:
        ext = bbox.extents(msp)
        if ext is not None:
            (xmin, ymin, _), (xmax, ymax, _) = ext.extmin, ext.extmax

            msp.dxf_layout.dxf.extmin = ezdxf.math.Vec3(xmin, ymin, 0)
            msp.dxf_layout.dxf.extmax = ezdxf.math.Vec3(xmax, ymax, 0)
            doc.header["$EXTMIN"] = msp.dxf_layout.dxf.extmin
            doc.header["$EXTMAX"] = msp.dxf_layout.dxf.extmax

        with MTextExplode(msp) as xpl:
            for m in list(msp.query("MTEXT")):
                xpl.explode(m)

        for t in list(msp.query("TEXT")):
            text2path.explode(t, target=msp)

        dxf_path = os.path.abspath(f"{project_name}_{timestamp}.dxf")
        doc.saveas(dxf_path)
        file_paths.append(dxf_path)

    # for thumbnail
    if dxf or image or svg:
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
        file_paths.append(jpg_path)

    return file_paths
