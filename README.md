import math

from drawscaffold.calculator.calculator_2d import Calculator2D


def _within_len(p1, p2, D, tol):
    return abs(math.hypot(p2[0]-p1[0], p2[1]-p1[1]) - D) <= tol

def _is_valid_diagonal(a, b, min_dy=0.0, min_angle_deg=None):
    x1, y1 = a; x2, y2 = b
    dx = abs(x2 - x1); dy = abs(y2 - y1)
    if dy < (min_dy or 0.0):
        return False
    if min_angle_deg is not None:
        # 0 = tamamen yatay, 90 = tamamen dikey
        angle = math.degrees(math.atan2(dy, dx if dx != 0 else 1e-9))
        if angle < min_angle_deg:
            return False
    return True

def _best_index_by_length(from_pt, target_col, guess_idx, D, tol,
                          min_idx_strict=None,
                          min_dy=0.0, min_angle_deg=None, direction="down"):
    xL, yL = from_pt
    best_j, best_err = None, float('inf')

    search_range = 2  # ±2

    start_j = max(0, guess_idx - search_range)
    end_j = min(len(target_col), guess_idx + search_range + 1)

    indices_to_check = range(start_j, end_j)
    if direction == "up":
        indices_to_check = reversed(list(indices_to_check))

    for j in indices_to_check:
        if (min_idx_strict is not None) and (j <= min_idx_strict):
            continue

        cand = target_col[j]

        # yön koruması
        if direction == "down" and cand[1] < from_pt[1]:
            continue
        if direction == "up" and cand[1] > from_pt[1]:
            continue

        # açı/dy validasyonu
        if not _is_valid_diagonal(from_pt, cand, min_dy=min_dy, min_angle_deg=min_angle_deg):
            continue

        # --- UZUNLUK TOLERANSI KAPISI (eklenen kısım) ---
        if not _within_len(from_pt, cand, D, tol):
            continue

        dist = math.hypot(cand[0] - xL, cand[1] - yL)
        err = abs(dist - D)

        if err < best_err:
            best_err, best_j = err, j

    return best_j

def draw_zigzag_pair_length_constrained(left_col, right_col, drawer,
                                        DIAGONAL_PART, VERTICAL_PART,
                                        start_side="left", start_left_idx=0, start_right_idx=0,
                                        tol=10.0,
                                        min_dy=None, min_angle_deg=None, material_count=None):
    calculator = Calculator2D()

    if not left_col or not right_col:
        return

    if min_dy is None:
        min_dy = 0.7 * VERTICAL_PART

    dx = abs(right_col[0][0] - left_col[0][0])
    dy_target = math.sqrt(max(DIAGONAL_PART * DIAGONAL_PART - dx * dx, 0.0))
    step = int(round(dy_target / VERTICAL_PART))
    base = int(round((right_col[0][1] - left_col[0][1]) / VERTICAL_PART))

    last_L, last_R = start_left_idx - 1, start_right_idx - 1

    if start_side == "left":
        i = max(0, start_left_idx)
        while True:
            if i >= len(left_col): break

            # L[i] -> R[j] ( / ) - Aşağı doğru çizim
            j_guess = int(round(i - base + step))
            j = _best_index_by_length(
                left_col[i], right_col, j_guess,
                DIAGONAL_PART, tol, min_idx_strict=last_R,
                min_dy=min_dy, min_angle_deg=min_angle_deg, direction="down"
            )
            if j is None: break
            if drawer:
                if _within_len(left_col[i], right_col[j], DIAGONAL_PART, tol):
                    drawer.draw_diagonal(left_col[i], right_col[j])
            else:
                if _within_len(left_col[i], right_col[j], DIAGONAL_PART, tol):
                    _, name = calculator.diagonal()
                    material_count.material_add(name)

            last_L, last_R = i, j

            # R[j] -> L[i2] ( \ ) - Aşağı doğru çizim
            i2_guess = int(round(j + base + step))
            i2 = _best_index_by_length(
                right_col[j], left_col, i2_guess,
                DIAGONAL_PART, tol, min_idx_strict=last_L,
                min_dy=min_dy, min_angle_deg=min_angle_deg, direction="down"
            )
            if i2 is None: break
            if drawer:
                drawer.draw_diagonal(right_col[j], left_col[i2])
            else:
                _, name = calculator.diagonal()
                material_count.material_add(name)
            last_L = i2
            i = i2
    else:  # start_side == "right"
        j = max(0, start_right_idx)
        while True:
            if j >= len(right_col): break

            # R[j] -> L[i] ( \ ) - Aşağı doğru çizim
            i_guess = int(round(j + base + step))
            i = _best_index_by_length(
                right_col[j], left_col, i_guess,
                DIAGONAL_PART, tol, min_idx_strict=last_L,
                min_dy=min_dy, min_angle_deg=min_angle_deg, direction="down"
            )
            if i is None: break
            if drawer:
                drawer.draw_diagonal(right_col[j], left_col[i])
            else:
                _, name = calculator.diagonal()
                material_count.material_add(name)
            last_R, last_L = j, i

            # L[i] -> R[j2] ( / ) - Aşağı doğru çizim
            j2_guess = int(round(i - base + step))
            j2 = _best_index_by_length(
                left_col[i], right_col, j2_guess,
                DIAGONAL_PART, tol, min_idx_strict=last_R,
                min_dy=min_dy, min_angle_deg=min_angle_deg, direction="down"
            )
            if j2 is None: break
            if drawer:
                drawer.draw_diagonal(left_col[i], right_col[j2])
            else:
                _, name = calculator.diagonal()
                material_count.material_add(name)
            last_R = j2
            j = j2


def draw_zigzag_diagonal_pattern(connection_centers, drawer, module_count,
                               DIAGONAL_PART, VERTICAL_PART, r_diagonal, material_count = None):
    diagonal_indexes = []
    group_size = 5
    for i in range(0, module_count, group_size):
        diagonal_indexes.append(i)
        if i + 5 <= module_count:
            diagonal_indexes.append((i + i + 6) // 2)
            diagonal_indexes.append(i + 5)
    diagonal_indexes.append(module_count - 1)

    diagonal_indexes = sorted(set(diagonal_indexes))

    side = 'right'
    if r_diagonal:
        side = 'left'

    for k in range(len(connection_centers) - 1):
        if k not in diagonal_indexes:
            continue
        L = connection_centers[k]
        R = connection_centers[k + 1]

        draw_zigzag_pair_length_constrained(
            L, R, drawer,
            DIAGONAL_PART=DIAGONAL_PART,
            VERTICAL_PART=VERTICAL_PART,
            start_side=side,
            start_left_idx=0,
            tol=10.0,
            min_angle_deg=20,
            material_count=material_count
        )

        side = 'right' if side == 'left' else 'left'

    return diagonal_indexes