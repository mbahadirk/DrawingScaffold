import math
from enum import Enum

from drawscaffold.calculator.calculator_2d import Calculator2D
from drawscaffold.const.conts import DIAGONAL_PART
from drawscaffold.shapes.shapes_2d import Drawer2D


class SIDE(Enum):
    LEFT = 'left'
    BOTH = 'both'
    RIGHT = 'right'
    BOTTOM = 'bottom'
    TOP = 'top'
    NONE = None


def dist2d(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    return math.hypot(x2 - x1, y2 - y1)


def _estimate_vstep(column_points):
    if not column_points or len(column_points) < 2:
        return None
    ys = [p[1] for p in column_points]
    ys.sort()
    diffs = [abs(ys[i + 1] - ys[i]) for i in range(len(ys) - 1)]
    diffs = [d for d in diffs if d > 1e-6]
    if not diffs:
        return None
    diffs.sort()
    mid = len(diffs) // 2
    if len(diffs) % 2 == 1:
        return diffs[mid]
    return 0.5 * (diffs[mid - 1] + diffs[mid])


def _find_next(centers, module_idx, bottom_side, value, max_y, tolerance=5.0, module_add_num=1):
    if not centers[module_idx]:
        return None, bottom_side

    y_value = value[1]
    candidates = []

    target_idx = module_idx + module_add_num
    if target_idx < 0 or target_idx >= len(centers):
        return None, bottom_side

    target_col = centers[target_idx]
    vstep = _estimate_vstep(centers[module_idx]) or _estimate_vstep(target_col)

    for point in target_col:
        if point[1] > max_y + tolerance:
            continue
        d = dist2d(point, value)
        if abs(d - DIAGONAL_PART) < tolerance:
            if vstep is not None:
                if abs(abs(point[1] - y_value) - vstep) > max(8.0, tolerance):
                    continue
            candidates.append(point)

    if not candidates:
        return None, bottom_side

    if len(candidates) == 1:
        the_one = candidates[0]
        new_direction = SIDE.BOTTOM if the_one[1] > y_value else SIDE.TOP
        return the_one, new_direction

    for point in candidates:
        is_going_up = point[1] > y_value
        if bottom_side == SIDE.BOTTOM and is_going_up:
            return point, bottom_side
        if bottom_side == SIDE.TOP and not is_going_up:
            return point, bottom_side

    the_one = candidates[0]
    new_direction = SIDE.BOTTOM if the_one[1] > y_value else SIDE.TOP
    return the_one, new_direction


def draw_x_diagonal_pattern(connection_centers, drawer: Drawer2D | None, module_count, vertical_count,
                            material_counter=None):
    calculator = Calculator2D()
    max_y_per_col = [max(p[1] for p in col) if col else None for col in connection_centers]
    min_y_per_col = [min(p[1] for p in col) if col else None for col in connection_centers]

    vert_idx = 0
    vert_add_num = 1
    last_vert_add_num = 1

    mod_idx = 0
    mod_add_num = 1
    last_mod_add_num = 1

    side = SIDE.LEFT

    biggest_side = max(module_count, vertical_count)
    diagonal_indexes = [[] for _ in range(biggest_side)]

    slope_side = SIDE.RIGHT
    if len(connection_centers[0]) - vertical_count > len(connection_centers[-1]) - vertical_count:
        slope_side = SIDE.LEFT

    s_mod_idx = 0 if slope_side == SIDE.LEFT else -1
    s_add_module_num = 1 if slope_side == SIDE.LEFT else -1
    s_last_add_module_num = s_add_module_num

    if s_mod_idx < 0:
        s_mod_idx = len(connection_centers) - 1

    s_extra = len(connection_centers[s_mod_idx]) - vertical_count - 1
    s_use_both_side = s_extra >= 5

    if slope_side == SIDE.RIGHT:
        s_bot_vert_idx = 0 if s_extra <= 0 else 1
    else:
        s_bot_vert_idx = 0

    s_top_side = SIDE.TOP
    s_top_vert_add_num = -1

    s_bottom_side = SIDE.BOTTOM
    s_bot_vert_add_num = 1

    if not connection_centers[s_mod_idx]:
        return diagonal_indexes

    B_L = connection_centers[s_mod_idx][s_bot_vert_idx]

    top_idx = max(0, s_extra)
    if top_idx >= len(connection_centers[s_mod_idx]):
        top_idx = len(connection_centers[s_mod_idx]) - 1

    b_top_y_point = connection_centers[s_mod_idx][top_idx][1]
    T_L = connection_centers[s_mod_idx][top_idx]

    for _ in range(module_count - 1):
        if s_add_module_num == 0:
            s_add_module_num = s_last_add_module_num
        if s_bot_vert_add_num == 0:
            s_bot_vert_add_num = 1 if s_bottom_side == SIDE.BOTTOM else -1
        if s_top_vert_add_num == 0:
            s_top_vert_add_num = 1 if s_top_side == SIDE.BOTTOM else -1

        B_R, s_bottom_side = _find_next(connection_centers, s_mod_idx, s_bottom_side, B_L, b_top_y_point,
                                        module_add_num=s_add_module_num)

        if B_R and b_top_y_point - B_R[1] >= -3 and b_top_y_point - B_L[1] >= -3:
            if drawer:
                drawer.draw_diagonal(B_L, B_R)

            if material_counter:
                _, name = calculator.diagonal()
                material_counter.material_add(name)

        if B_R and s_bottom_side == SIDE.BOTTOM and (
                B_L[1] >= b_top_y_point or B_R[1] >= b_top_y_point or B_L[1] > B_R[1]):
            s_bottom_side = SIDE.TOP
        elif B_R and s_bottom_side == SIDE.TOP:
            safe_idx = s_mod_idx + s_add_module_num
            target_y = -9999
            if 0 <= safe_idx < len(connection_centers) and connection_centers[safe_idx]:
                target_y = connection_centers[safe_idx][0][1]

            if (B_L[1] == connection_centers[s_mod_idx][0][1] or B_R[1] == target_y or B_L[1] < B_R[1]):
                s_bottom_side = SIDE.BOTTOM

        if s_use_both_side:
            T_R, s_top_side = _find_next(connection_centers, s_mod_idx, s_top_side, T_L, b_top_y_point,
                                         module_add_num=s_add_module_num)

            if T_R and b_top_y_point - T_R[1] >= -3 and b_top_y_point - T_L[1] >= -3:
                if drawer:
                    drawer.draw_diagonal(T_L, T_R)

                if material_counter:
                    _, name = calculator.diagonal()
                    material_counter.material_add(name)
                    material_counter.material_add(name)

            if T_R and s_top_side == SIDE.BOTTOM and (
                    T_L[1] >= b_top_y_point or T_R[1] >= b_top_y_point or T_L[1] > T_R[1]):
                s_top_side = SIDE.TOP
            elif T_R and s_top_side == SIDE.TOP:
                safe_idx = s_mod_idx + s_add_module_num
                target_y = -9999
                if 0 <= safe_idx < len(connection_centers) and connection_centers[safe_idx]:
                    target_y = connection_centers[safe_idx][0][1]

                if (T_L[1] == connection_centers[s_mod_idx][0][1] or T_R[1] == target_y or T_L[1] < T_R[1]):
                    s_top_side = SIDE.BOTTOM

            if T_R:
                T_L = T_R

        if B_R:
            B_L = B_R
        s_mod_idx += s_add_module_num

    for idx in range(biggest_side):
        add_side = side
        if mod_idx < 0 or mod_idx >= len(connection_centers):
            break
        extra = len(connection_centers[mod_idx]) - vertical_count - 1
        idx_w_extra = vert_idx + extra
        data = (add_side, mod_idx, idx_w_extra, extra)
        diagonal_indexes[mod_idx].append(data)

        if mod_add_num == 0:
            mod_add_num = last_mod_add_num
        if vert_add_num == 0:
            vert_add_num = last_vert_add_num

        if mod_idx + mod_add_num == module_count:
            mod_add_num = 0
            last_mod_add_num = -1
            side = SIDE.RIGHT
        if mod_idx + mod_add_num == -1:
            mod_add_num = 0
            last_mod_add_num = 1
            side = SIDE.LEFT

        if vert_idx + last_vert_add_num == vertical_count:
            vert_add_num = 0
            last_vert_add_num = -1
            side = SIDE.RIGHT
        elif vert_idx + last_vert_add_num == -1:
            vert_add_num = 0
            last_vert_add_num = 1
            side = SIDE.LEFT

        vert_idx += vert_add_num
        mod_idx += mod_add_num

    vert_idx = 0
    vert_add_num = 1
    last_vert_add_num = 1

    mod_idx = module_count - 1
    mod_add_num = -1
    last_mod_add_num = -1
    side = SIDE.RIGHT

    for _ in range(biggest_side):
        add_side = side
        if mod_idx < 0 or mod_idx >= len(connection_centers):
            break
        extra = len(connection_centers[mod_idx]) - vertical_count - 1
        idx_w_extra = vert_idx + extra
        data = (add_side, mod_idx, idx_w_extra, extra)
        diagonal_indexes[mod_idx].append(data)

        if mod_add_num == 0:
            mod_add_num = last_mod_add_num
        if vert_add_num == 0:
            vert_add_num = last_vert_add_num

        if mod_idx + mod_add_num == -1:
            mod_add_num = 0
            last_mod_add_num = 1
            side = SIDE.LEFT
        if mod_idx + mod_add_num == module_count:
            mod_add_num = 0
            last_mod_add_num = -1
            side = SIDE.RIGHT

        if vert_idx + last_vert_add_num == vertical_count:
            vert_add_num = 0
            last_vert_add_num = -1
            side = SIDE.LEFT
        elif vert_idx + last_vert_add_num == -1:
            vert_add_num = 0
            last_vert_add_num = 1
            side = SIDE.RIGHT

        vert_idx += vert_add_num
        mod_idx += mod_add_num

    counted_points = set()
    col_offsets = [max(0, len(col) - (vertical_count + 1)) for col in connection_centers]

    for module_index, modules in enumerate(diagonal_indexes):
        if module_index + 1 >= len(connection_centers):
            continue

        left_col = connection_centers[module_index]
        right_col = connection_centers[module_index + 1]

        offL = col_offsets[module_index]
        offR = col_offsets[module_index + 1]

        nL = len(left_col)
        nR = len(right_col)

        ground_y_L = min_y_per_col[module_index]
        ground_y_R = min_y_per_col[module_index + 1]

        for data in modules:
            side = data[0]
            k = data[2] - offL
            if k < 0 or k + 1 > vertical_count:
                continue

            conns = []
            if side == SIDE.LEFT:
                Lidx = k + offL
                Ridx = k + 1 + offR
                if 0 <= Lidx < nL and 0 <= Ridx < nR:
                    conns.append((left_col[Lidx], right_col[Ridx]))
            elif side == SIDE.RIGHT:
                Lidx = k + 1 + offL
                Ridx = k + offR
                if 0 <= Lidx < nL and 0 <= Ridx < nR:
                    conns.append((left_col[Lidx], right_col[Ridx]))
            else:
                Lidx1 = k + offL
                Ridx1 = k + 1 + offR
                if 0 <= Lidx1 < nL and 0 <= Ridx1 < nR:
                    conns.append((left_col[Lidx1], right_col[Ridx1]))
                Lidx2 = k + 1 + offL
                Ridx2 = k + offR
                if 0 <= Lidx2 < nL and 0 <= Ridx2 < nR:
                    conns.append((left_col[Lidx2], right_col[Ridx2]))

            for Lp, Rp in conns:
                is_L_at_bottom = False
                if ground_y_L is not None:
                    is_L_at_bottom = math.isclose(Lp[1], ground_y_L, abs_tol=1e-5)

                is_R_at_bottom = False
                if ground_y_R is not None:
                    is_R_at_bottom = math.isclose(Rp[1], ground_y_R, abs_tol=1e-5)

                if material_counter:
                    if is_L_at_bottom and Lp not in counted_points:
                        starter = calculator.start()
                        material_counter.material_add(starter)
                        counted_points.add(Lp)

                    if is_R_at_bottom and Rp not in counted_points:
                        starter = calculator.start()
                        material_counter.material_add(starter)
                        counted_points.add(Rp)

                if drawer:
                    drawer.draw_diagonal(Lp, Rp)

                if material_counter:
                    _, name = calculator.diagonal()
                    material_counter.material_add(name)

    return diagonal_indexes