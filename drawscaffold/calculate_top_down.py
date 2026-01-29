"""
Slim version of calculate_top_down.
Only contains essential imports/exports used by other modules.

For detailed material calculation, use:
- drawscaffold.model.material_calculator.FacadeMaterialCalculator
"""
from math import tan, radians

from drawscaffold.calculator.calculator_top_down import CalculatorTopDown
from drawscaffold.const.conts import (
    VERTICAL_PART, HORIZONTAL_PART, FOOT_PART, FOOT_INSIDE_PART,
    ADJUSTMENT_SHAFT1, ADJUSTMENT_SHAFT2, HALF_FOOT_PART, 
    COMPLETE_FOOT_PART, ADJUSTMENT_SHAFT3, HALF_VERTICAL_PART, DIAGONAL_PART
)
from drawscaffold.diagonal.diagnoal_drawer import draw_x_diagonal_pattern
from drawscaffold.diagonal.patterns.zigzag_pattern import draw_zigzag_diagonal_pattern
from drawscaffold.utils.debug_printer import DebugPrinter


class MaterialCounterTopDown:
    """Counts materials for scaffold assembly."""
    
    def __init__(self):
        self.counter_dict = dict()

    def material_add(self, material_name: str):
        if material_name in self.counter_dict.keys():
            self.counter_dict[material_name] += 1
            return
        self.counter_dict[material_name] = 1


def frontal_calculator2D(length_list: list[int], h: float, slope: float, toe_board: bool,
                         use_x_pattern: bool, use_zigzag_pattern: bool,
                         material_counter: MaterialCounterTopDown, 
                         counter: CalculatorTopDown, d: DebugPrinter):
    """
    Calculate materials for a frontal (2D profile) scaffold row.
    
    Args:
        length_list: List of module lengths [250, 250, 150, ...]
        h: Height in cm
        slope: Surface slope in degrees
        toe_board: Include toe boards
        use_x_pattern: Use X diagonal pattern
        use_zigzag_pattern: Use zigzag pattern
        material_counter: Counter for materials
        counter: Calculator for positions
        d: Debug printer
    """
    if not length_list:
        return
        
    floor_count = int(h // (VERTICAL_PART - 20))

    def y_on_surface(x, width_cm, base_y, slope_deg):
        x0 = width_cm / 2.0
        m = tan(radians(slope_deg))
        return base_y - m * (x - x0)

    # Calculate start points based on slope
    start_points = []
    surface_horizontal = 0
    for i in range(len(length_list) + 1):
        surface_point = y_on_surface(surface_horizontal, len(length_list), 0, slope)
        start_points.append(surface_point)
        surface_horizontal += HORIZONTAL_PART

    d.print(start_points)
    biggest_point = max(start_points)

    # Process each column
    start_x_points = 0
    module_idx = 0
    connection_centers = [[] for _ in range(len(length_list) + 1)]

    for start_point in start_points:
        difference = biggest_point - start_point

        if difference < 0:
            d.print("Negative difference, skipping")
        elif difference == 0:
            foot_start = (start_x_points, start_point)
            lock_center, name = counter.foot(foot_start, lock_start_y=start_point + 0.5)
            connection_centers[module_idx].append(lock_center)
            material_counter.material_add(name)

        elif difference >= (VERTICAL_PART - 20):
            _process_tall_column(
                start_x_points, start_point, difference,
                material_counter, counter, d, connection_centers, module_idx
            )
        else:
            _process_short_column(
                start_x_points, start_point, difference,
                material_counter, counter, d, connection_centers, module_idx
            )

        start_x_points += 1
        module_idx += 1

    # Add floor materials
    _add_floor_materials(
        length_list, floor_count, h, toe_board,
        use_x_pattern, use_zigzag_pattern,
        material_counter, counter, d, connection_centers
    )


def _process_tall_column(x_pos, start_y, difference, 
                         material_counter, counter, d,
                         connection_centers, module_idx):
    """Process a column that needs vertical parts."""
    gap = difference % (VERTICAL_PART - 20)
    vertical_count = int(difference // (VERTICAL_PART - 20))

    if gap <= (FOOT_PART - FOOT_INSIDE_PART):
        lock_center, name = counter.foot((x_pos, start_y), lock_start_y=start_y + gap)
        connection_centers[module_idx].append(lock_center)
        material_counter.material_add(name)
        last_y = start_y + gap

    elif gap <= (ADJUSTMENT_SHAFT1 * 0.8):
        lock_center, name = counter.adjustment((x_pos, start_y), ADJUSTMENT_SHAFT1, gap)
        connection_centers[module_idx].append(lock_center)
        material_counter.material_add(name)
        last_y = start_y + gap

    elif gap <= (ADJUSTMENT_SHAFT2 * 0.8):
        lock_center, name = counter.adjustment((x_pos, start_y), ADJUSTMENT_SHAFT2, gap)
        connection_centers[module_idx].append(lock_center)
        material_counter.material_add(name)
        last_y = start_y + gap

    elif gap <= (HALF_FOOT_PART - FOOT_INSIDE_PART):
        lock_center, name = counter.foot((x_pos, start_y), half_foot=True, lock_start_y=start_y + gap)
        connection_centers[module_idx].append(lock_center)
        material_counter.material_add(name)
        last_y = start_y + gap

    elif gap <= (ADJUSTMENT_SHAFT3 * 0.8):
        lock_center, name = counter.adjustment((x_pos, start_y), ADJUSTMENT_SHAFT3, gap)
        connection_centers[module_idx].append(lock_center)
        material_counter.material_add(name)
        last_y = start_y + gap

    else:
        # Use half vertical
        after_gap = gap - (HALF_VERTICAL_PART - 20)
        if after_gap <= (FOOT_PART - FOOT_INSIDE_PART):
            lock_y = start_y + after_gap
            lock_center, name = counter.foot((x_pos, start_y), lock_start_y=lock_y)
            _, name2 = counter.vertical((x_pos, lock_y), half_vertical=True)
            connection_centers[module_idx].append(lock_center)
            material_counter.material_add(name)
            material_counter.material_add(name2)
            last_y = lock_y + (HALF_VERTICAL_PART - 20)
        else:
            lock_y = start_y + after_gap
            lock_center, name = counter.foot((x_pos, start_y), half_foot=True, lock_start_y=lock_y)
            _, name2 = counter.vertical((x_pos, lock_y), half_vertical=True)
            connection_centers[module_idx].append(lock_center)
            material_counter.material_add(name)
            material_counter.material_add(name2)
            last_y = lock_y + (HALF_VERTICAL_PART - 20)

    # Add vertical parts
    for v in range(vertical_count):
        _, name = counter.vertical((x_pos, last_y))
        material_counter.material_add(name)
        last_y += (VERTICAL_PART - 20)


def _process_short_column(x_pos, start_y, difference,
                          material_counter, counter, d,
                          connection_centers, module_idx):
    """Process a column shorter than one vertical part."""
    if difference <= (FOOT_PART - FOOT_INSIDE_PART):
        lock_center, name = counter.foot((x_pos, start_y), lock_start_y=start_y + difference)
        connection_centers[module_idx].append(lock_center)
        material_counter.material_add(name)

    elif difference <= (ADJUSTMENT_SHAFT1 * 0.8):
        lock_center, name = counter.adjustment((x_pos, start_y), ADJUSTMENT_SHAFT1, difference)
        connection_centers[module_idx].append(lock_center)
        material_counter.material_add(name)

    elif difference <= (ADJUSTMENT_SHAFT2 * 0.8):
        lock_center, name = counter.adjustment((x_pos, start_y), ADJUSTMENT_SHAFT2, difference)
        connection_centers[module_idx].append(lock_center)
        material_counter.material_add(name)

    else:
        lock_center, name = counter.foot((x_pos, start_y), half_foot=True, lock_start_y=start_y + difference)
        connection_centers[module_idx].append(lock_center)
        material_counter.material_add(name)


def _add_floor_materials(length_list, floor_count, h, toe_board,
                         use_x_pattern, use_zigzag_pattern,
                         material_counter, counter, d, connection_centers):
    """Add floor-level materials (platforms, supports, diagonals)."""
    for floor in range(floor_count):
        for i, module_len in enumerate(length_list):
            # Platforms
            if module_len == 250:
                material_counter.material_add("PLATFORM_250")
                material_counter.material_add("SUPPORT_250")
            else:
                material_counter.material_add("PLATFORM_150")
                material_counter.material_add("SUPPORT_150")

    # Diagonals
    if use_zigzag_pattern:
        for i in range(len(length_list)):
            material_counter.material_add("DIAGONAL")

    # Ties and other parts
    for i in range(len(length_list) + 1):
        material_counter.material_add("tie")
        material_counter.material_add("l_part")

    # Signs
    for floor in range(floor_count):
        for i in range(len(length_list)):
            material_counter.material_add("SIGN_")

    # Start pieces
    material_counter.material_add("start")


def top_down_calc(verbose: bool, facades: dict, h: float, slope: float, 
                  toe_board: bool, use_x_pattern, use_zigzag_pattern):
    """
    Calculate materials for all facades (legacy entry point).
    
    For OOP version, use:
    FacadeMaterialCalculator from drawscaffold.model.material_calculator
    """
    d = DebugPrinter(verbose)
    material_counter = MaterialCounterTopDown()
    top_down_counter = CalculatorTopDown()

    # Process each facade
    from drawscaffold.model.direction import calculate_modules
    
    for key in ['F', 'R', 'B', 'L']:
        if key not in facades or not facades[key]:
            continue
        
        for item in facades[key]:
            values = str(item).split(',')
            if len(values) < 5:
                continue
            
            pos = int(values[1])
            length = int(values[2])
            
            modules = calculate_modules(length)
            use_slope = key in ['F', 'B']  # Horizontal facades get slope
            
            frontal_calculator2D(
                modules, h, slope if use_slope else 0, toe_board,
                use_x_pattern, use_zigzag_pattern,
                material_counter, top_down_counter, d
            )

    return material_counter.counter_dict
