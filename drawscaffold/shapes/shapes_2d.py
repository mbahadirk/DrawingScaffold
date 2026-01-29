import math
from typing import Sequence, Dict, Callable, List

from ezdxf.addons import text2path
from ezdxf.fonts import fonts
from ezdxf.layouts import Modelspace, BlockLayout

from drawscaffold.const.conts import (
    VERTICAL_PART, HALF_VERTICAL_PART, VERTICAL_COLOR,
    HORIZONTAL_PART, STEEL_PLATFORM_COLOR, HORIZONTAL_COLOR,
    FOOT_PART, HALF_FOOT_PART, COMPLETE_FOOT_PART,
    SURFACE_COLOR, FOOT_COLOR, ADJUSTMENT_COLOR, DIAGONAL_COLOR, DIAGONAL_PART, TEXT_COLOR,
)

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

class Drawer2D:
    def __init__(self, msp: Modelspace, doc):
        self.msp = msp
        self.doc = doc
        self._blocks = _BlockCache(doc)

    def _ensure_lock_block(self):
        name = "LOCK_STD"
        def build(blk):
            pts = [
                (-2.5, +2), (-2.5, -2), (2.5, -2), (2.5, +2), (-2.5, +2),
                (-2.5, +1), (-8.5, +0.5), (-8.5, -0.5), (-2.5, -1),
                (-2.5, -2), (2.5, -2), (2.5, -1), (8.5, -0.5),
                (8.5, +0.5), (2.5, +1), (2.5, +2), (-2.5, +2)
            ]
            poly = blk.add_lwpolyline(pts, close=True)
            poly.dxf.color = SURFACE_COLOR
        return self._blocks.ensure(name, build)

    def _ensure_end_circle_block(self, radius=1.0):
        name = f"END_CIRCLE_R{radius}"
        def build(blk):
            c = blk.add_circle(center=(0, 0), radius=radius)
            c.dxf.color = DIAGONAL_COLOR
        return self._blocks.ensure(name, build)

    def draw_L_part(self, start_point: Sequence[float]):
        x, y = start_point
        height = VERTICAL_PART
        name = f"L_{int(height)}"
        def build(blk):
            pts = [
                (-2.5, 0), (-2.5, height-20), (-1.5, height-20), (-1.5, height),
                (1.5, height), (1.5, height-20), (-1.5, height-20),
                (2.5, height-20), (2.5, 0), (-2.5, 0)
            ]
            pl = blk.add_lwpolyline(pts, close=True)
            pl.dxf.color = VERTICAL_COLOR
            conn = blk.add_lwpolyline([(-1.5, height-24), (-1.5, height-21),
                                       (1.5, height-21), (1.5, height-24),
                                       (-1.5, height-24)], close=True)
            conn.dxf.color = VERTICAL_COLOR
        blk = self._blocks.ensure(name, build)
        self.msp.add_blockref(blk.name, insert=(x, y))
        conn_center = (x, y + ((height - 24) + (height - 21)) / 2)
        return conn_center

    def draw_vertical(self, start_point: Sequence[float], half_vertical: bool = False):
        x, y = start_point
        height = HALF_VERTICAL_PART if half_vertical else VERTICAL_PART
        name = f"VERT_{int(height)}"
        def build(blk):
            pts = [
                (-2.5, 0), (-2.5, height-20), (-1.5, height-20), (-1.5, height),
                (1.5, height), (1.5, height-20), (-1.5, height-20),
                (2.5, height-20), (2.5, 0), (-2.5, 0)
            ]
            pl = blk.add_lwpolyline(pts, close=True)
            pl.dxf.color = VERTICAL_COLOR
            conn = blk.add_lwpolyline([(-1.5, height-24), (-1.5, height-21),
                                       (1.5, height-21), (1.5, height-24),
                                       (-1.5, height-24)], close=True)
            conn.dxf.color = VERTICAL_COLOR
        blk = self._blocks.ensure(name, build)
        self.msp.add_blockref(blk.name, insert=(x, y))
        conn_center = (x, y + ((height-24) + (height-21)) / 2)
        return conn_center

    def draw_horizontal(self, start_point: Sequence[float]):
        x, y = start_point
        L = HORIZONTAL_PART
        name = f"PLATFORM_{int(L)}"
        def build(blk):
            platform_start_x = 3.5
            radius_outer = 1.0
            radius_inner = 0.5
            poly = blk.add_lwpolyline([
                (platform_start_x, -3), (platform_start_x, +3),
                (platform_start_x+L-7, +3), (platform_start_x+L-7, -3),
                (platform_start_x, -3)
            ], close=True)
            poly.dxf.color = STEEL_PLATFORM_COLOR
            blk.add_line((-3.5, -3), (-2.5, -3)).dxf.color = STEEL_PLATFORM_COLOR
            blk.add_line((-3.5, -3), (-3.5, 0)).dxf.color = STEEL_PLATFORM_COLOR
            blk.add_line((-2.5, -3), (-2.5, -0.5)).dxf.color = STEEL_PLATFORM_COLOR
            blk.add_arc(center=(-(3.5-radius_outer), 0), radius=radius_outer,
                        start_angle=90, end_angle=180).dxf.color = STEEL_PLATFORM_COLOR
            blk.add_line((-(3.5-radius_outer), radius_outer),
                         (5-(3.5-radius_outer), radius_outer)).dxf.color = STEEL_PLATFORM_COLOR
            blk.add_arc(center=(-(2.5 - radius_inner), -0.5), radius=radius_inner,
                        start_angle=90, end_angle=180).dxf.color = STEEL_PLATFORM_COLOR
            blk.add_line((-(2.5 - radius_inner), -(0.5 - radius_inner)),
                         (5-(3.5 - radius_inner), -(0.5 - radius_inner))).dxf.color = STEEL_PLATFORM_COLOR
            blk.add_line((+3.5, -3), (+2.5, -3)).dxf.color = STEEL_PLATFORM_COLOR
            blk.add_line((+3.5, -3), (+3.5, 0)).dxf.color = STEEL_PLATFORM_COLOR
            blk.add_line((+2.5, -3), (+2.5, -0.5)).dxf.color = STEEL_PLATFORM_COLOR
            blk.add_arc(center=((3.5 - radius_outer), 0), radius=radius_outer,
                        start_angle=0, end_angle=90).dxf.color = STEEL_PLATFORM_COLOR
            blk.add_arc(center=((2.5 - radius_inner), -0.5), radius=radius_inner,
                        start_angle=0, end_angle=90).dxf.color = STEEL_PLATFORM_COLOR
            blk.add_line((platform_start_x+L-7, -3), (platform_start_x+L-6, -3)).dxf.color = STEEL_PLATFORM_COLOR
            blk.add_line((platform_start_x+L-7, -3), (platform_start_x+L-7, 0)).dxf.color = STEEL_PLATFORM_COLOR
            blk.add_line((platform_start_x+L-6, -3), (platform_start_x+L-6, -0.5)).dxf.color = STEEL_PLATFORM_COLOR
            blk.add_arc(center=(platform_start_x+L-(7 - radius_outer), 0),
                        radius=radius_outer, start_angle=90, end_angle=180).dxf.color = STEEL_PLATFORM_COLOR
            blk.add_line((platform_start_x+L-(7 - radius_outer), radius_outer),
                         (platform_start_x+L+(5 - (7 - radius_outer)), radius_outer)).dxf.color = STEEL_PLATFORM_COLOR
            blk.add_arc(center=(platform_start_x+L-(6 - radius_inner), -0.5),
                        radius=radius_inner, start_angle=90, end_angle=180).dxf.color = STEEL_PLATFORM_COLOR
            blk.add_line((platform_start_x+L-(6 - radius_inner), -(0.5 - radius_inner)),
                         (platform_start_x+L+(5 - (7 - radius_inner)), -(0.5 - radius_inner))).dxf.color = STEEL_PLATFORM_COLOR
            blk.add_line((platform_start_x+L, -3), (platform_start_x+L-1, -3)).dxf.color = STEEL_PLATFORM_COLOR
            blk.add_line((platform_start_x+L, -3), (platform_start_x+L, 0)).dxf.color = STEEL_PLATFORM_COLOR
            blk.add_line((platform_start_x+L-1, -3), (platform_start_x+L-1, -0.5)).dxf.color = STEEL_PLATFORM_COLOR
            blk.add_arc(center=(platform_start_x+L - radius_outer, 0),
                        radius=radius_outer, start_angle=0, end_angle=90).dxf.color = STEEL_PLATFORM_COLOR
            blk.add_arc(center=(platform_start_x+L + (-1 - radius_inner), -0.5),
                        radius=radius_inner, start_angle=0, end_angle=90).dxf.color = STEEL_PLATFORM_COLOR
        blk = self._blocks.ensure(name, build)
        self.msp.add_blockref(blk.name, insert=(x, y))

    def draw_support(self, start_point: Sequence[float]):
        x, y = start_point
        L = HORIZONTAL_PART
        name = f"SUPPORT_{int(L)}"
        def build(blk):
            pts = [
                (0, +2.25), (2, +2.25), (3, +1.25), (L-3, +1.25), (L-2, +2.25),
                (L, +2.25), (L, -2.25), (L-2, -2.25), (L-3, -1.25), (3, -1.25),
                (2, -2.25), (0, -2.25), (0, +2.25)
            ]
            pl = blk.add_lwpolyline(pts, close=True)
            pl.dxf.color = HORIZONTAL_COLOR
        blk = self._blocks.ensure(name, build)
        self.msp.add_blockref(blk.name, insert=(x, y))

    def _ensure_foot_body(self, foot_in_cm: float, color: int, name: str):
        def build(blk):
            pts = [
                (-7.5, 0), (-7.5, 0.5), (-7.5, 0), (7.5, 0), (7.5, 0.5),
                (-7.5, 0.5), (-2, 0.5), (-2, 0.5+foot_in_cm),
                (2, 0.5+foot_in_cm), (2, 0.5), (7.5, 0.5), (7.5, 0), (-7.5, 0)
            ]
            pl = blk.add_lwpolyline(pts, close=True)
            pl.dxf.color = color
        return self._blocks.ensure(name, build)

    def draw_foot(self, start_point: Sequence[float],
                  half_foot: bool = False, complete_foot: bool = False,
                  lock_start_y: float = 0.0):
        x, y = start_point
        foot_h = FOOT_PART
        color = FOOT_COLOR
        name = "FOOT_STD"
        if half_foot:
            foot_h = HALF_FOOT_PART; name = "FOOT_HALF"
        elif complete_foot:
            foot_h = COMPLETE_FOOT_PART; name = "FOOT_FULL"
        body_blk = self._ensure_foot_body(foot_h, color, name)
        self.msp.add_blockref(body_blk.name, insert=(x, y))
        lock_blk = self._ensure_lock_block()
        lock_cy = lock_start_y - 2.0
        self.msp.add_blockref(lock_blk.name, insert=(x, lock_cy))
        return (x, lock_cy)

    def draw_adjustment(self, start_point: Sequence[float],
                        adjustment_height: float, lock_height: float):
        x, y = start_point
        name = f"ADJ_{int(adjustment_height)}"
        body_blk = self._ensure_foot_body(adjustment_height, ADJUSTMENT_COLOR, name)
        self.msp.add_blockref(body_blk.name, insert=(x, y))
        lock_space = 0.5
        lock_start_y = y + (lock_height - lock_space)
        lock_blk = self._ensure_lock_block()
        lock_cy = lock_start_y - 2.0
        self.msp.add_blockref(lock_blk.name, insert=(x, lock_cy))
        return (x, lock_cy)

    def _ensure_diagonal_body_fixed(self, length: float, thickness: float = 2.0, end_radius: float = 1.0):
        L = round(float(length), 2)
        name = f"DIAG_BODY_FIXED_{L:g}"

        def build(blk):
            half = L / 2.0
            r = end_radius
            t = thickness
            cx, cy = 0.0, 0.0

            pts = [
                (cx, cy + t, 0, 0, 0.0),
                (half - 3.0, cy + t, 0, 0, 0.0),
                (half - 2.0, cy + t + 0.5, 0, 0, 0.0),
                (half + r, cy + t, 0, 0, -0.41421356),
                (half + r, cy - t, 0, 0, 0.0),
                (half - 2.0, cy - t - 0.5, 0, 0, 0.0),
                (half - 3.0, cy - t, 0, 0, 0.0),
                (-half + 3.0, cy - t, 0, 0, 0.0),
                (-half + 2.0, cy - t - 0.5, 0, 0, 0.0),
                (-half - r, cy - t, 0, 0, -0.41421356),
                (-half - r, cy + t, 0, 0, 0.0),
                (-half + 2.0, cy + t + 0.5, 0, 0, 0.0),
                (-half + 3.0, cy + t, 0, 0, 0.0),
            ]
            pl = blk.add_lwpolyline(pts, format='xyseb', close=True)
            pl.dxf.color = DIAGONAL_COLOR

        return self._blocks.ensure(name, build, base_point=(0.0, 0.0))

    def draw_diagonal(self, start_point: Sequence[float], end_point: Sequence[float], end_circle_radius: float = 1.0):
        x1, y1 = start_point
        x2, y2 = end_point

        dx, dy = (x2 - x1), (y2 - y1)
        L_actual = math.hypot(dx, dy)
        if L_actual <= 1e-9:
            return

        angle_deg = math.degrees(math.atan2(dy, dx))
        mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0

        circ_blk = self._ensure_end_circle_block(radius=end_circle_radius)
        self.msp.add_blockref(circ_blk.name, insert=(x1, y1))
        self.msp.add_blockref(circ_blk.name, insert=(x2, y2))

        body_blk = self._ensure_diagonal_body_fixed(DIAGONAL_PART, thickness=2.0, end_radius=end_circle_radius)
        ins = self.msp.add_blockref(body_blk.name, insert=(mx, my))
        ins.dxf.rotation = angle_deg

    def draw_sign(self, start_point: Sequence[float], text: str,
                  font_name: str = "Arial", line_spacing: float = 1.2):
        x1, y1 = start_point
        name = f"SIGN_{text}"

        def build(blk):
            pts = [
                (-2.5, 32), (-2.5, 26), (4.5, 26),
                (4.5, 6), (-2.5, 6), (-2.5, 0),
                (247.5, 0), (247.5, 6), (254.5, 6),
                (254.5, 26), (247.5, 26), (247.5, 32),
                (-2.5, 32)
            ]
            pl = blk.add_lwpolyline(pts, format='xyseb', close=True)
            pl.dxf.color = TEXT_COLOR

            x_left, x_right = 4.5, 245.5
            y_bot, y_top = 6.0, 26.0
            box_w = (x_right - x_left)
            box_h = (y_top - y_bot)

            char_h, lines = _fit_text_to_box(
                text=text,
                box_w=box_w,
                box_h=box_h,
                font_name=font_name,
                line_spacing=line_spacing,
                h_min=2.0,
                h_max=26.0,
                max_lines=3,
                hard_wrap_long_words=True,
            )

            cx = (x_left + x_right) / 2.0
            cy = (y_bot + y_top) / 2.0
            m = blk.add_mtext("\\P".join(lines))
            m.dxf.insert = (cx, cy, 0.0)
            m.dxf.attachment_point = 5
            m.dxf.char_height = char_h
            m.dxf.line_spacing_factor = line_spacing
            m.dxf.width = 0.0
            m.dxf.color = TEXT_COLOR

            style = self.doc.styles.new("BOLD_ARIAL", dxfattribs={"font": "arialbd.ttf"})
            style.dxf.oblique = 25
            m.dxf.style = "BOLD_ARIAL"

        blk = self._blocks.ensure(name, build)
        self.msp.add_blockref(blk.name, insert=(x1, y1))
