import math
from typing import Sequence, Dict, Callable, List

from ezdxf.addons import text2path
from ezdxf.fonts import fonts
from ezdxf.layouts import Modelspace, BlockLayout

from drawscaffold.const.conts import (
    HORIZONTAL_PART, TEXT_COLOR, SMALL_HORIZONTAL_PART,
    TOP_CIRCLE_COLOR, TOP_VERTICAL_COLOR, TOP_PLATFORM_COLOR, TOP_INNER_HORIZONTAL_COLOR, TOP_OUTER_HORIZONTAL_COLOR,
)
from drawscaffold.const.top_down_enum import ScaffoldSide


def _measure_width_precise(text: str, char_height: float, font_name: str = "Arial") -> float:
    if not text:
        return 0.0

    face = fonts.FontFace(family=font_name)
    paths = text2path.make_paths_from_str(text, font=face, size=char_height)
    if not paths:
        return 0.0

    xmin = ymin = float("inf")
    xmax = ymax = float("-inf")

    for p in paths:
        bb = p.bbox()
        try:
            x0, y0, x1, y1 = bb
        except Exception:
            if hasattr(bb, "extmin"):
                x0, y0 = float(bb.extmin.x), float(bb.extmin.y)
                x1, y1 = float(bb.extmax.x), float(bb.extmax.y)
            else:
                extmin, extmax = bb
                x0, y0 = float(extmin[0]), float(extmin[1])
                x1, y1 = float(extmax[0]), float(extmax[1])

        if x0 < xmin: xmin = x0
        if y0 < ymin: ymin = y0
        if x1 > xmax: xmax = x1
        if y1 > ymax: ymax = y1

    return max(0.0, xmax - xmin)

def _wrap_text_to_width(text: str, char_height: float, max_width: float,
                        font_name: str = "Arial", hard_wrap: bool = False) -> List[str]:
    words = text.split()
    lines: List[str] = []
    cur: List[str] = []

    def line_width(parts: List[str]) -> float:
        s = " ".join(parts)
        return _measure_width_precise(s, char_height, font_name)

    for w in words:
        if not cur:
            cur = [w]
            continue
        if line_width(cur + [w]) <= max_width:
            cur.append(w)
        else:
            lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))

    if hard_wrap and len(lines) == 1 and " " not in text and _measure_width_precise(text, char_height, font_name) > max_width:
        cur = []
        lines = []
        buf = ""
        for ch in text:
            test = buf + ch
            if _measure_width_precise(test, char_height, font_name) <= max_width:
                buf = test
            else:
                if buf:
                    lines.append(buf)
                buf = ch
        if buf:
            lines.append(buf)

    return lines

def _fit_text_to_box(
    text: str,
    box_w: float,
    box_h: float,
    font_name: str = "Arial",
    line_spacing: float = 1.2,
    h_min: float = 2.0,
    h_max: float = 26.0,
    max_lines: int = 3,
    hard_wrap_long_words: bool = True,
):
    lo, hi = h_min, h_max
    best_h = lo
    best_lines = [text]

    for _ in range(30):
        mid = (lo + hi) / 2.0
        lines = _wrap_text_to_width(
            text, mid, box_w,
            font_name=font_name,
            hard_wrap=hard_wrap_long_words
        )
        total_h = len(lines) * mid * line_spacing
        fits = (total_h <= box_h) and (len(lines) <= max_lines)

        if fits:
            best_h, best_lines = mid, lines
            lo = mid
        else:
            if len(lines) > max_lines or total_h > box_h:
                hi = mid
            else:
                lo = mid

        if hi - lo < 1e-3:
            break

    if len(best_lines) > max_lines:
        h = best_h
        for _ in range(30):
            h = max(h_min, h * 0.9)
            lines = _wrap_text_to_width(
                text, h, box_w,
                font_name=font_name,
                hard_wrap=hard_wrap_long_words
            )
            if len(lines) <= max_lines and (len(lines)*h*line_spacing) <= box_h:
                best_h, best_lines = h, lines
                break
        else:
            tiny = _wrap_text_to_width(
                text, h_min, box_w,
                font_name=font_name,
                hard_wrap=True
            )
            merged = tiny[:max_lines-1]
            merged.append(" ".join(tiny[max_lines-1:]))
            best_h, best_lines = h_min, merged

    return best_h, best_lines

def _net_perp_offset(points, direction: str) -> float:
    if not points or len(points) < 2:
        return 0.0
    if direction == 'h':
        return points[-1][1] - points[0][1]
    else:
        return points[-1][0] - points[0][0]


def _apply_length_correction(base_len: int, prev_points, prev_dir: str) -> int:
    corr = abs(_net_perp_offset(prev_points, prev_dir))
    return int(round(base_len - corr))

class _BlockCache:
    def __init__(self, doc):
        self.doc = doc
        self._cache: Dict[str, BlockLayout] = {}

    def ensure(self, name: str, builder: Callable[[BlockLayout], None], base_point=(0.0, 0.0)) -> BlockLayout:
        if name in self._cache:
            return self._cache[name]
        if name in self.doc.blocks:
            blk = self.doc.blocks.get(name)
        else:
            blk = self.doc.blocks.new(name=name, base_point=base_point)
            builder(blk)
        self._cache[name] = blk
        return blk

class DrawerTopView:
    def __init__(self, msp: Modelspace, doc):
        self.msp = msp
        self.doc = doc
        self._blocks = _BlockCache(doc)

    def line_building(self, facades: dict):
        front_cmds = self._parse_facade_commands(facades, 'f')
        right_cmds = self._parse_facade_commands(facades, 'r')
        back_cmds = self._parse_facade_commands(facades, 'b')
        left_cmds = self._parse_facade_commands(facades, 'l')

        start_x, start_y = 0.0, 0.0

        front_points = right_points = back_points = left_points = None

        if front_cmds and facades.get('F'):
            front_len = int(facades['F'][-1].split(',')[2])
            front_points = self._calculate_facade_points(start_x, start_y, front_cmds, efficient_cmds=[facades['L'], facades['R']], length=front_len, direction='h')
            self.msp.add_lwpolyline(front_points, close=False)
            if front_points:
                start_x, start_y = front_points[-1]

        if right_cmds and facades.get('R'):
            right_len = int(facades['R'][-1].split(',')[2])
            if front_points:
                right_len = _apply_length_correction(right_len, front_points, 'h')

            right_points = self._calculate_facade_points(start_x, start_y, right_cmds, efficient_cmds=[facades['F'], facades['B']], length=right_len, direction='v')
            self.msp.add_lwpolyline(right_points, close=False)
            if right_points:
                start_x, start_y = right_points[-1]

        if back_cmds and facades.get('B'):
            back_len = int(facades['B'][-1].split(',')[2])
            if right_points:
                back_len = _apply_length_correction(back_len, right_points, 'v')

            back_points = self._calculate_facade_points(start_x, start_y, back_cmds, efficient_cmds=[facades['L'], facades['R']], direction='h', length=back_len,
                                                        reverse=True)
            self.msp.add_lwpolyline(back_points, close=False)
            if back_points:
                start_x, start_y = back_points[-1]

        if left_cmds and facades.get('L'):
            left_len = int(facades['L'][-1].split(',')[2])
            if back_points:
                left_len = _apply_length_correction(left_len, back_points, 'h')

            left_points = self._calculate_facade_points(start_x, start_y, left_cmds, efficient_cmds=[facades['F'], facades['B']], direction='v', length=left_len,
                                                        reverse=True)
            self.msp.add_lwpolyline(left_points, close=False)

    def _draw_facade_with_commands(self, start: tuple, end: tuple,
                                   commands: list, direction: str):
        if not commands:
            # Komut yoksa düz çizgi çiz
            self.msp.add_lwpolyline([start, end], close=False)
            return

        points = [start]
        current_depth = 0

        # commands zaten (0, 0) ile başlıyor ve sıralı
        for i, (pos, signed_depth) in enumerate(commands[1:], 1):
            if direction == 'h':
                # Yatay cephe: X = start[0] + pos, Y = start[1] + current_depth
                points.append((start[0] + pos, start[1] + current_depth))
                current_depth += signed_depth
                points.append((start[0] + pos, start[1] + current_depth))
            else:
                # Dikey cephe: X = start[0] + current_depth, Y = start[1] + pos
                points.append((start[0] + current_depth, start[1] + pos))
                current_depth += signed_depth
                points.append((start[0] + current_depth, start[1] + pos))

        # Son noktayı ekle (end noktası)
        points.append(end)

        # Çizgiyi çiz
        self.msp.add_lwpolyline(points, close=False)

    def _parse_facade_commands(self, facades: dict, side_char: str):
        commands = []

        if side_char in ['f', 'l']:
            inset_sign = 1
            outset_sign = -1
        else:
            inset_sign = -1
            outset_sign = 1

        for key in facades.keys():
            for item in facades[key]:
                values = str(item).split(',')
                if len(values) < 5:
                    continue

                func = str(values[0]).lower()
                pos = int(values[1])
                depth = int(values[3])
                side = str(values[4]).lower()

                if side == side_char:
                    signed_depth = depth * (outset_sign if func == 'outset' else inset_sign)
                    commands.append((pos, signed_depth))

        commands.insert(0, (0, 0))
        commands.sort(key=lambda x: x[0])

        return commands

    def peak_offsets(self, cmds):
        curr = 0
        max_out = 0
        min_in = 0

        for cmd in cmds:
            parts = str(cmd).split(',')
            if len(parts) < 2:
                continue

            op = parts[0].strip().lower()
            depth = int(parts[-2]) if len(parts) > 3 else int(parts[-2])

            if op == "outset":
                curr += depth
            elif op == "inset":
                curr -= depth
            else:
                continue

            if curr > max_out:
                max_out = curr
            if curr < min_in:
                min_in = curr

        return max_out, abs(min_in)

    def _calculate_facade_points(self, start_x: float, start_y: float,
                                 commands: list, efficient_cmds: list[list], direction: str, length: int, reverse: bool = False):
        if not commands:
            return []

        if efficient_cmds and direction=='h':
            total_cumulative_outset = 0
            for cmds in efficient_cmds:
                max_out, max_in = self.peak_offsets(cmds)
                total_cumulative_outset += max_out

            length -= total_cumulative_outset

        points = []
        current_depth = 0

        # Başlangıç noktası
        points.append((start_x, start_y))

        # Komutları işle (derinlik değişimleri)
        for i, (pos, signed_depth) in enumerate(commands[1:], 1):
            pos_factor = -1 if reverse else 1

            if direction == 'h':
                # Yatay hareket
                points.append((start_x + pos * pos_factor, start_y + current_depth))
                current_depth += signed_depth
                points.append((start_x + pos * pos_factor, start_y + current_depth))
            else:
                # Dikey hareket
                points.append((start_x + current_depth, start_y + pos * pos_factor))
                current_depth += signed_depth
                points.append((start_x + current_depth, start_y + pos * pos_factor))

        # Son noktayı hesapla (istenen uzunluğa ulaş)
        last_x, last_y = points[-1]

        if direction == 'h':
            if reverse:
                target_x = start_x - length
            else:
                target_x = start_x + length
            points.append((target_x, last_y))
        else:
            if reverse:
                target_y = start_y - length
            else:
                target_y = start_y + length
            points.append((last_x, target_y))

        return points

    def draw_scaffold(self, start_point: Sequence[float], small: bool, console_count: int, scaffold_side: ScaffoldSide = ScaffoldSide.LEFT):
        x, y = start_point
        height = HORIZONTAL_PART
        if small:
            height = SMALL_HORIZONTAL_PART
        name = f'SCAFFOLD_{height}cm_{console_count}'

        def build(blk):
            cx, cy = 0.0, 0.0
            r = 2.5
            dx = 65.0

            def build_platform_points(steel_x: float, steel_y: float):
                pts = [
                    (steel_x, steel_y), (steel_x + 2.5, steel_y), (steel_x + 2.5, steel_y + 6.8),
                    (steel_x + 6.5, steel_y + 6.8), (steel_x + 6.5, steel_y), (steel_x + 21.5, steel_y),
                    (steel_x + 21.5, steel_y + 6.8), (steel_x + 25.5, steel_y + 6.8), (steel_x + 25.5, steel_y),
                    (steel_x + 33, steel_y), (steel_x + 33, steel_y - height + 4 * r),
                    (steel_x + 30.5, steel_y - height + 4 * r),
                    (steel_x + 30.5, steel_y - height + 4 * r - 6.8), (steel_x + 26.5, steel_y - height + 4 * r - 6.8),
                    (steel_x + 26.5, steel_y - height + 4 * r), (steel_x + 11.5, steel_y - height + 4 * r),
                    (steel_x + 11.5, steel_y - height + 4 * r - 6.8),
                    (steel_x + 7.5, steel_y - height + 4 * r - 6.8), (steel_x + 7.5, steel_y - height + 4 * r),
                    (steel_x, steel_y - height + 4 * r), (steel_x, steel_y),
                    (steel_x + 33, steel_y), (steel_x + 33, steel_y - height + 4 * r),
                    (steel_x + 3.5, steel_y - height + 4 * r), (steel_x + 3.5, steel_y), (steel_x + 2.5, steel_y),
                    (steel_x + 2.5, steel_y - height + 4 * r), (steel_x + 30, steel_y - height + 4 * r),
                    (steel_x + 30, steel_y), (steel_x + 31, steel_y - height + 4 * r),
                    (steel_x, steel_y - height + 4 * r)
                ]

                return pts

            def write_text(cx, cy):
                text_x_left, text_x_right = cx + 3, cx+ 29
                text_y_top, text_y_bot = cy, cy - height + 4 * r
                box_w = (text_x_right - text_x_left)
                box_h = (text_y_top - text_y_bot)

                char_h, lines = _fit_text_to_box(
                    text=f"{height}cm",
                    box_w=box_h,
                    box_h=box_w,
                    font_name="Arial",
                    line_spacing=1.2,
                    h_min=1.5,
                    h_max=15.0,
                    max_lines=3,
                    hard_wrap_long_words=True,
                )

                cx = (text_x_left + text_x_right) / 2.0
                cy = (text_y_bot + text_y_top) / 2.0
                m = blk.add_mtext("\\P".join(lines))
                m.dxf.insert = (cx, cy, 0.0)
                m.dxf.attachment_point = 5
                m.dxf.char_height = char_h
                m.dxf.line_spacing_factor = 1.2
                m.dxf.width = 0.0
                m.dxf.color = TEXT_COLOR

                STYLE_NAME = "BOLD_ARIAL"
                if STYLE_NAME not in self.doc.styles:
                    style = self.doc.styles.new(STYLE_NAME, dxfattribs={"font": "arialbd.ttf"})
                    style.dxf.oblique = 25
                else:
                    style = self.doc.styles.get(STYLE_NAME)
                    style.dxf.oblique = 25

                m.dxf.style = "BOLD_ARIAL"
                m.dxf.rotation = 90

            angle_deg = 40
            angle = math.radians(angle_deg)

            up_c1 = (cx, cy)
            up_c2 = (cx + dx + 2 * r * math.cos(angle), cy)

            bottom_c1 = (cx, cy - height)
            bottom_c2 = (cx + dx + 2 * r * math.cos(angle), cy - height)

            up_l_lock_pts = [
                (cx + dx + 2 * r * math.cos(angle) - r - 0.5, cy - 1), (cx + dx + 2 * r * math.cos(angle) - r - 5.5, cy - 1),
                (cx + dx + 2 * r * math.cos(angle) - r - 5.5, cy + 1), (cx + dx + 2 * r * math.cos(angle) - r - 0.5, cy + 1)
            ]

            up_r_lock_pts = [
                (cx + dx + 2 * r * math.cos(angle) + r + 0.5, cy - 1),
                (cx + dx + 2 * r * math.cos(angle) + r + 5.5, cy - 1),
                (cx + dx + 2 * r * math.cos(angle) + r + 5.5, cy + 1),
                (cx + dx + 2 * r * math.cos(angle) + r + 0.5, cy + 1)
            ]

            bot_l_lock_pts = [
                (cx + dx + 2 * r * math.cos(angle) - r - 0.5, cy - height - 1),
                (cx + dx + 2 * r * math.cos(angle) - r - 5.5, cy - height - 1),
                (cx + dx + 2 * r * math.cos(angle) - r - 5.5, cy- height + 1),
                (cx + dx + 2 * r * math.cos(angle) - r - 0.5, cy- height + 1)
            ]

            bot_r_lock_pts = [
                (cx + dx + 2 * r * math.cos(angle) + r + 0.5, cy - height - 1),
                (cx + dx + 2 * r * math.cos(angle) + r + 5.5, cy - height - 1),
                (cx + dx + 2 * r * math.cos(angle) + r + 5.5, cy - height + 1),
                (cx + dx + 2 * r * math.cos(angle) + r + 0.5, cy - height + 1)
            ]

            upl_lock1 = blk.add_lwpolyline(up_l_lock_pts, close=True)
            upl_lock2 = blk.add_lwpolyline(up_r_lock_pts, close=True)

            bot_lock1 = blk.add_lwpolyline(bot_l_lock_pts, close=True)
            bot_lock2 = blk.add_lwpolyline(bot_r_lock_pts, close=True)

            top_c1 = blk.add_circle(up_c1, r)
            top_c2 = blk.add_circle(up_c2, r)

            bot_c1 = blk.add_circle(bottom_c1, r)
            bot_c2 = blk.add_circle(bottom_c2, r)

            up_p1_top = (
                cx + r * math.cos(angle),
                cy + r * math.sin(angle)
            )
            up_p1_bot = (
                cx + r * math.cos(-angle),
                cy + r * math.sin(-angle)
            )

            bottom_p1_top = (
                cx + r * math.cos(angle),
                cy + r * math.sin(angle) - height
            )
            bottom_p1_bot = (
                cx + r * math.cos(-angle),
                cy + r * math.sin(-angle) - height
            )

            up_p2_top = (
                cx + dx + r * math.cos(angle),
                cy + r * math.sin(angle)
            )
            up_p2_bot = (
                cx + dx + r * math.cos(-angle),
                cy + r * math.sin(-angle)
            )

            bottom_p2_top = (
                cx + dx + r * math.cos(angle),
                cy + r * math.sin(angle) - height
            )
            bottom_p2_bot = (
                cx + dx + r * math.cos(-angle),
                cy + r * math.sin(-angle) - height
            )

            top_l1 = blk.add_line(up_p1_top, up_p2_top)
            top_l2 = blk.add_line(up_p1_bot, up_p2_bot)
            bot_l1 = blk.add_line(bottom_p1_top, bottom_p2_top)
            bot_l2 = blk.add_line(bottom_p1_bot, bottom_p2_bot)

            # plaka
            sx = cx + 0.6 * r
            sy = cy - 2 * r

            pts1 = build_platform_points(sx, sy)
            pl1 = blk.add_lwpolyline(pts1, close=True)

            sx += 33.5

            pts2 = build_platform_points(sx, sy)
            pl2 = blk.add_lwpolyline(pts2, close=True)

            sx -= 33.5
            for i in range(console_count):
                sx -= 33.5

                ptsn = build_platform_points(sx, sy)
                pln = blk.add_lwpolyline(ptsn, close=True)

                write_text(sx, sy)
                pln.dxf.color = TOP_PLATFORM_COLOR

            inner_horizontal_pts = [
                (cx + dx + 2 * r * math.cos(angle) - r - 2.75, cy), (cx + dx + 2 * r * math.cos(angle) - r - 3.75, cy - 3),
                (cx + dx + 2 * r * math.cos(angle) - r - 3.75, cy - height + 3), (cx + dx + 2 * r * math.cos(angle) - r - 2.75, cy - height),
                (cx + dx + 2 * r * math.cos(angle) - r - 1.75, cy - height + 3), (cx + dx + 2 * r * math.cos(angle) - r - 1.75, cy - 3)
            ]

            outer_horizontal_pts = [
                (cx + dx + 2 * r * math.cos(angle) + r + 2.75, cy),
                (cx + dx + 2 * r * math.cos(angle) + r + 3.75, cy - 3),
                (cx + dx + 2 * r * math.cos(angle) + r + 3.75, cy - height + 3),
                (cx + dx + 2 * r * math.cos(angle) + r + 2.75, cy - height),
                (cx + dx + 2 * r * math.cos(angle) + r + 1.75, cy - height + 3),
                (cx + dx + 2 * r * math.cos(angle) + r + 1.75, cy - 3)
            ]

            inner_horizontal_hatch = blk.add_hatch()
            inner_horizontal_hatch.set_solid_fill(color=TOP_INNER_HORIZONTAL_COLOR)
            inner_horizontal_hatch.paths.add_polyline_path(inner_horizontal_pts, is_closed=True)

            outer_horizontal_hatch = blk.add_hatch()
            outer_horizontal_hatch.set_solid_fill(color=TOP_OUTER_HORIZONTAL_COLOR)
            outer_horizontal_hatch.paths.add_polyline_path(outer_horizontal_pts, is_closed=True)

            write_text(cx + 0.6 * r, cy - 2 * r)
            write_text(cx + 0.6 * r + 33.5, cy - 2 * r)

            top_c1.dxf.color = TOP_CIRCLE_COLOR
            top_c2.dxf.color = TOP_CIRCLE_COLOR
            bot_c1.dxf.color = TOP_CIRCLE_COLOR
            bot_c2.dxf.color = TOP_CIRCLE_COLOR

            top_l1.dxf.color = TOP_VERTICAL_COLOR
            top_l2.dxf.color = TOP_VERTICAL_COLOR
            bot_l1.dxf.color = TOP_VERTICAL_COLOR
            bot_l2.dxf.color = TOP_VERTICAL_COLOR

            upl_lock1.dxf.color = TOP_VERTICAL_COLOR
            upl_lock2.dxf.color = TOP_VERTICAL_COLOR
            bot_lock1.dxf.color = TOP_VERTICAL_COLOR
            bot_lock2.dxf.color = TOP_VERTICAL_COLOR

            pl1.dxf.color = TOP_PLATFORM_COLOR
            pl2.dxf.color = TOP_PLATFORM_COLOR

        blk = self._blocks.ensure(name, build)
        ref = self.msp.add_blockref(blk.name, insert=(x, y))

        if scaffold_side == ScaffoldSide.LEFT:
            multiplier = 0
        elif scaffold_side == ScaffoldSide.BACK:
            multiplier = 1
        elif scaffold_side == ScaffoldSide.RIGHT:
            multiplier = 2
        else:
            multiplier = 3

        ref.dxf.rotation = 90 * multiplier
