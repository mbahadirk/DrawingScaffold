from drawscaffold.diagonal.patterns.zigzag_pattern import draw_zigzag_pair_length_constrained


def draw_x_diagonal_pattern(connection_centers, drawer, module_count,
                               DIAGONAL_PART, VERTICAL_PART, material_count=None):
    # Compute diagonal indexes locally (3 on 6 pattern as before)
    diagonal_indexes = []
    group_size = 5
    for i in range(0, module_count, group_size):
        diagonal_indexes.append(i)
        if i + 5 <= module_count:
            diagonal_indexes.append((i + i + 6) // 2)
            diagonal_indexes.append(i + 5)
    diagonal_indexes.append(module_count - 1)

    diagonal_indexes = sorted(set(diagonal_indexes))

    # Draw using the original routine
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