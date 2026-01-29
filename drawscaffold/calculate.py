from math import radians, tan

from drawscaffold.calculator.calculator_2d import Calculator2D
from drawscaffold.const.conts import HORIZONTAL_PART, VERTICAL_PART, FOOT_PART, FOOT_INSIDE_PART, \
    ADJUSTMENT_SHAFT1, ADJUSTMENT_SHAFT2, HALF_FOOT_PART, ADJUSTMENT_SHAFT3, COMPLETE_FOOT_PART, HALF_VERTICAL_PART, DIAGONAL_PART
from drawscaffold.diagonal.patterns.x_pattern import draw_x_diagonal_pattern
from drawscaffold.diagonal.patterns.zigzag_pattern import draw_zigzag_diagonal_pattern
from drawscaffold.utils.debug_printer import DebugPrinter

class MaterialCounter:
    def __init__(self):
        self.counter_dict = dict()

    def material_add(self, material_name: str):
        if material_name in self.counter_dict.keys():
            self.counter_dict[material_name] += 1
            return

        self.counter_dict[material_name] = 1

def material_calculator2D(verbose:bool, h: float, w: float,
                          slope: float, toe_text: str | None, r_diagonal: bool,
                          use_x_pattern: bool, use_zigzag_pattern: bool,
                          use_best_pattern: bool, side_count: int) -> dict:
    material_count = MaterialCounter()
    calculator = Calculator2D()

    d = DebugPrinter(verbose)

    floor_count = int(h // (VERTICAL_PART - 20))
    module_count = int(w // HORIZONTAL_PART)

    def y_on_surface(x, width_cm, base_y, slope_deg):
        x0 = width_cm / 2.0
        m = tan(radians(slope_deg))
        return base_y - m * (x - x0)

    # calculate start points if surface have slope
    start_points = []
    surface_horizontal = 0
    for i in range(module_count+1):
        surface_point = y_on_surface(surface_horizontal, w, 0, slope)
        start_points.append(surface_point)

        surface_horizontal += HORIZONTAL_PART

    d.print(start_points)
    biggest_point = max(start_points)

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
            lock_center, name = calculator.foot(foot_start, lock_start_y=start_point+0.5)

            connection_centers[module_idx].append(lock_center)
            material_count.material_add(name)

        elif difference >= (VERTICAL_PART - 20):
            gap = difference % (VERTICAL_PART - 20)
            vertical_count = int(difference // (VERTICAL_PART - 20))

            if gap <= (FOOT_PART - FOOT_INSIDE_PART):
                foot_start = (start_x_points, start_point)
                lock_center, name = calculator.foot(foot_start, lock_start_y=start_point + gap)

                connection_centers[module_idx].append(lock_center)
                material_count.material_add(name)

                last_y = foot_start[1] + gap
            elif gap <= (ADJUSTMENT_SHAFT1*0.8):
                lock_center, name = calculator.adjustment((start_x_points, start_point), ADJUSTMENT_SHAFT1, gap)
                connection_centers[module_idx].append(lock_center)
                material_count.material_add(name)

                last_y = start_point + gap
            elif gap <= (ADJUSTMENT_SHAFT2*0.8):
                lock_center, name = calculator.adjustment((start_x_points, start_point), ADJUSTMENT_SHAFT2, gap)

                connection_centers[module_idx].append(lock_center)
                material_count.material_add(name)
                last_y = start_point + gap
            elif gap <= (HALF_FOOT_PART - FOOT_INSIDE_PART):
                foot_start = (start_x_points, start_point)
                lock_center, name = calculator.foot(foot_start, half_foot=True, lock_start_y=start_point + gap)

                connection_centers[module_idx].append(lock_center)
                material_count.material_add(name)
                last_y = foot_start[1] + gap
            elif gap <= (ADJUSTMENT_SHAFT3*0.8):
                lock_center, name = calculator.adjustment((start_x_points, start_point), ADJUSTMENT_SHAFT3, gap)

                connection_centers[module_idx].append(lock_center)
                material_count.material_add(name)
                last_y = start_point + gap
            elif gap - (HALF_VERTICAL_PART - 20) <= (FOOT_PART - FOOT_INSIDE_PART):
                after_gap = gap - (HALF_VERTICAL_PART - 20)

                lock_y = start_point + after_gap
                lock_center, name = calculator.foot(start_point=(start_x_points, start_point), lock_start_y=lock_y)

                last_y = lock_y

                _, name2 = calculator.vertical(start_point=(start_x_points, last_y), half_vertical=True)
                connection_centers[module_idx].append(lock_center)

                material_count.material_add(name)
                material_count.material_add(name2)

                last_y += (HALF_VERTICAL_PART - 20)

            elif gap - (HALF_VERTICAL_PART - 20) <= (HALF_FOOT_PART - FOOT_INSIDE_PART):
                after_gap = gap - (HALF_VERTICAL_PART - 20)

                lock_y = start_point + after_gap
                lock_center, name = calculator.foot(start_point=(start_x_points, start_point), half_foot=True, lock_start_y=lock_y)

                last_y = lock_y

                _, name2 = calculator.vertical(start_point=(start_x_points, last_y), half_vertical=True)
                connection_centers[module_idx].append(lock_center)

                material_count.material_add(name)
                material_count.material_add(name2)

                last_y += (HALF_VERTICAL_PART - 20)
            elif gap <= (COMPLETE_FOOT_PART - FOOT_INSIDE_PART):
                foot_start = (start_x_points, start_point)
                lock_center, name = calculator.foot(foot_start, complete_foot=True, lock_start_y=start_point + gap)
                connection_centers[module_idx].append(lock_center)
                material_count.material_add(name)

                last_y = foot_start[1] + gap
            else:
                foot_y = COMPLETE_FOOT_PART - FOOT_INSIDE_PART
                slide_cm = gap - foot_y
                foot_start = (start_x_points, start_point + slide_cm)
                lock_center, name = calculator.foot(foot_start, complete_foot=True)
                connection_centers[module_idx].append(lock_center)

                last_y = foot_start[1] + foot_y

                lock_center, name2 = calculator.vertical((start_x_points, last_y))
                connection_centers[module_idx].append(lock_center)

                material_count.material_add(name)
                material_count.material_add(name2)

                last_y += (VERTICAL_PART-20)

            for vertical in range(vertical_count):
                lock_center, name = calculator.vertical((start_x_points, last_y))
                connection_centers[module_idx].append(lock_center)
                material_count.material_add(name)

                last_y += (VERTICAL_PART - 20)

        elif difference <= (FOOT_PART - FOOT_INSIDE_PART):
            foot_start = (start_x_points, start_point)

            lock_center, name = calculator.foot(foot_start, lock_start_y=start_point + difference)
            connection_centers[module_idx].append(lock_center)
            material_count.material_add(name)
        elif difference <= (ADJUSTMENT_SHAFT1*0.8):
            slide_cm = (ADJUSTMENT_SHAFT1*0.8) - difference
            adj_start = (start_x_points, start_point - slide_cm)

            lock_center, name = calculator.adjustment(adj_start, ADJUSTMENT_SHAFT1, difference)
            connection_centers[module_idx].append(lock_center)
            material_count.material_add(name)
        elif difference <= (ADJUSTMENT_SHAFT2*0.8):
            slide_cm = (ADJUSTMENT_SHAFT2*0.8) - difference
            adj_start = (start_x_points, start_point - slide_cm)

            lock_center, name = calculator.adjustment(adj_start, ADJUSTMENT_SHAFT2, difference)
            connection_centers[module_idx].append(lock_center)
            material_count.material_add(name)
        elif difference <= (HALF_FOOT_PART - FOOT_INSIDE_PART):
            foot_start = (start_x_points, start_point)

            lock_center, name = calculator.foot(foot_start, half_foot=True, lock_start_y=start_point + difference)
            connection_centers[module_idx].append(lock_center)
            material_count.material_add(name)
        elif difference <= (ADJUSTMENT_SHAFT3*0.8):
            slide_cm = (ADJUSTMENT_SHAFT3*0.8) - difference
            adj_start = (start_x_points, start_point - slide_cm)

            lock_center, name = calculator.adjustment(adj_start, ADJUSTMENT_SHAFT3, difference)
            connection_centers[module_idx].append(lock_center)
            material_count.material_add(name)
        elif difference <= (COMPLETE_FOOT_PART - FOOT_INSIDE_PART):
            foot_start = (start_x_points, start_point)

            lock_center, name = calculator.foot(foot_start, complete_foot=True, lock_start_y=start_point + difference)
            connection_centers[module_idx].append(lock_center)
            material_count.material_add(name)
        else:
            slide_cm = difference - (COMPLETE_FOOT_PART - FOOT_INSIDE_PART)
            foot_start = (start_x_points, start_point + slide_cm)

            lock_center, name = calculator.foot(foot_start, complete_foot=True)
            connection_centers[module_idx].append(lock_center)
            material_count.material_add(name)

        start_x_points += HORIZONTAL_PART
        module_idx += 1

    vertical_point = biggest_point

    tie_every_module = 2 if module_count%2==0 else 3 if module_count%3==0 else 5
    needed_calculate_tie = floor_count >= 4
    for vertical in range(floor_count):
        horizontal_point = 0
        connection_index = 0
        use_l_part = vertical == floor_count-1
        is_first_floor = vertical==0
        is_tie_needed = needed_calculate_tie and vertical >= 2
        m = 0
        for module in range(module_count):
            should_calc_tie = is_tie_needed and module%tie_every_module==0
            if should_calc_tie:
                tie = calculator.tie()
                material_count.material_add(tie)

            if use_l_part:
                l_part_connection_center, name = calculator.L_part((horizontal_point, vertical_point))
                connection_centers[connection_index].append(l_part_connection_center)
            else:
                vertical_connection_center, name = calculator.vertical((horizontal_point, vertical_point))
                connection_centers[connection_index].append(vertical_connection_center)

            material_count.material_add(name)

            if toe_text and not is_first_floor:
                _, name2 = calculator.sign(toe_text)
                material_count.material_add(name2)

            _, name3 = calculator.horizontal()

            _, name4 = calculator.support()
            _, name5 = calculator.support()

            if not is_first_floor:
                material_count.material_add(name3)

            material_count.material_add(name3)
            material_count.material_add(name4)
            material_count.material_add(name5)

            horizontal_point += HORIZONTAL_PART

            connection_index+=1
            m = module

        m += 1
        if use_l_part:
            l_part, name = calculator.L_part((horizontal_point, vertical_point))
        else:
            vertical_connection_center, name = calculator.vertical((horizontal_point, vertical_point))
            connection_centers[connection_index].append(vertical_connection_center)

        should_calc_tie = is_tie_needed and m % tie_every_module == 0
        if should_calc_tie:
            tie = calculator.tie()
            material_count.material_add(tie)

        material_count.material_add(name)

        vertical_point += (VERTICAL_PART - 20)

    if use_zigzag_pattern:
        diagonal_indexes = draw_zigzag_diagonal_pattern(
            connection_centers, None, module_count, DIAGONAL_PART, VERTICAL_PART, r_diagonal, material_count
        )
        d.print(diagonal_indexes)
    if use_x_pattern:
        draw_x_diagonal_pattern(connection_centers, None, module_count, floor_count, material_count)

    for counter_key in material_count.counter_dict.keys():
        material_count.counter_dict[counter_key] = material_count.counter_dict[counter_key] * side_count

    return material_count.counter_dict
