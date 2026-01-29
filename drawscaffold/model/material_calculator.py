"""
OOP-based material calculator for scaffold assembly.
Refactored from calculate_top_down.py for better maintainability.
"""
from math import tan, radians
from typing import List, Dict, Tuple, Optional

from drawscaffold.calculator.calculator_top_down import CalculatorTopDown
from drawscaffold.const.conts import (
    VERTICAL_PART, HORIZONTAL_PART, FOOT_PART, FOOT_INSIDE_PART,
    ADJUSTMENT_SHAFT1, ADJUSTMENT_SHAFT2, ADJUSTMENT_SHAFT3,
    HALF_FOOT_PART, COMPLETE_FOOT_PART, HALF_VERTICAL_PART, DIAGONAL_PART
)
from drawscaffold.diagonal.diagnoal_drawer import draw_x_diagonal_pattern
from drawscaffold.diagonal.patterns.zigzag_pattern import draw_zigzag_diagonal_pattern
from drawscaffold.utils.debug_printer import DebugPrinter
from drawscaffold.model.direction import (
    Direction, DIRECTIONS, calculate_modules, parse_facade_command
)


class MaterialCounter:
    """Counts materials used in scaffold assembly."""
    
    def __init__(self):
        self.counts: Dict[str, int] = {}
    
    def add(self, material_name: str, count: int = 1):
        """Add material to counter."""
        if material_name in self.counts:
            self.counts[material_name] += count
        else:
            self.counts[material_name] = count
    
    @property
    def counter_dict(self) -> Dict[str, int]:
        """Return counts as dictionary (backward compatibility)."""
        return self.counts


class FloorCalculator:
    """Calculates floor/height-based materials for a scaffold segment."""
    
    def __init__(self, height: float, slope: float, 
                 material_counter: MaterialCounter,
                 calculator: CalculatorTopDown,
                 debug: DebugPrinter):
        self.height = height
        self.slope = slope
        self.material_counter = material_counter
        self.calculator = calculator
        self.debug = debug
        self.floor_count = int(height // (VERTICAL_PART - 20))
    
    def y_on_surface(self, x: float, width_cm: float, base_y: float, slope_deg: float) -> float:
        """Calculate Y position on sloped surface."""
        x0 = width_cm / 2.0
        m = tan(radians(slope_deg))
        return base_y - m * (x - x0)
    
    def calculate_start_points(self, module_count: int) -> List[float]:
        """Calculate starting Y points for each column based on slope."""
        points = []
        x_pos = 0
        for i in range(module_count + 1):
            y = self.y_on_surface(x_pos, module_count, 0, self.slope)
            points.append(y)
            x_pos += HORIZONTAL_PART
        return points
    
    def process_column(self, x_pos: float, start_y: float, max_y: float) -> Tuple[float, float]:
        """
        Process a single column of scaffold.
        
        Returns:
            Tuple of (lock_center_y, last_y)
        """
        difference = max_y - start_y
        
        if difference < 0:
            self.debug.print("Negative difference, skipping")
            return None, start_y
        
        if difference == 0:
            # Just a foot
            lock_center, name = self.calculator.foot(
                (x_pos, start_y), 
                lock_start_y=start_y + 0.5
            )
            self.material_counter.add(name)
            return lock_center, start_y
        
        if difference >= (VERTICAL_PART - 20):
            return self._process_tall_column(x_pos, start_y, difference)
        else:
            return self._process_short_column(x_pos, start_y, difference)
    
    def _process_tall_column(self, x_pos: float, start_y: float, 
                             difference: float) -> Tuple[float, float]:
        """Process column that needs vertical parts."""
        gap = difference % (VERTICAL_PART - 20)
        vertical_count = int(difference // (VERTICAL_PART - 20))
        
        # Determine foot/adjustment type based on gap size
        if gap <= (FOOT_PART - FOOT_INSIDE_PART):
            lock_center, name = self.calculator.foot(
                (x_pos, start_y), 
                lock_start_y=start_y + gap
            )
            self.material_counter.add(name)
            return lock_center, start_y + gap
        
        elif gap <= (ADJUSTMENT_SHAFT1 * 0.8):
            lock_center, name = self.calculator.adjustment(
                (x_pos, start_y), ADJUSTMENT_SHAFT1, gap
            )
            self.material_counter.add(name)
            return lock_center, start_y + gap
        
        elif gap <= (ADJUSTMENT_SHAFT2 * 0.8):
            lock_center, name = self.calculator.adjustment(
                (x_pos, start_y), ADJUSTMENT_SHAFT2, gap
            )
            self.material_counter.add(name)
            return lock_center, start_y + gap
        
        elif gap <= (HALF_FOOT_PART - FOOT_INSIDE_PART):
            lock_center, name = self.calculator.foot(
                (x_pos, start_y), 
                half_foot=True,
                lock_start_y=start_y + gap
            )
            self.material_counter.add(name)
            return lock_center, start_y + gap
        
        elif gap <= (ADJUSTMENT_SHAFT3 * 0.8):
            lock_center, name = self.calculator.adjustment(
                (x_pos, start_y), ADJUSTMENT_SHAFT3, gap
            )
            self.material_counter.add(name)
            return lock_center, start_y + gap
        
        else:
            return self._process_with_half_vertical(x_pos, start_y, gap)
    
    def _process_short_column(self, x_pos: float, start_y: float,
                              difference: float) -> Tuple[float, float]:
        """Process column shorter than one vertical part."""
        if difference <= (FOOT_PART - FOOT_INSIDE_PART):
            lock_center, name = self.calculator.foot(
                (x_pos, start_y),
                lock_start_y=start_y + difference
            )
            self.material_counter.add(name)
            return lock_center, start_y + difference
        
        elif difference <= (ADJUSTMENT_SHAFT1 * 0.8):
            lock_center, name = self.calculator.adjustment(
                (x_pos, start_y), ADJUSTMENT_SHAFT1, difference
            )
            self.material_counter.add(name)
            return lock_center, start_y + difference
        
        else:
            # Use half foot
            lock_center, name = self.calculator.foot(
                (x_pos, start_y),
                half_foot=True,
                lock_start_y=start_y + difference
            )
            self.material_counter.add(name)
            return lock_center, start_y + difference
    
    def _process_with_half_vertical(self, x_pos: float, start_y: float,
                                    gap: float) -> Tuple[float, float]:
        """Process column that needs half vertical part."""
        after_gap = gap - (HALF_VERTICAL_PART - 20)
        
        if after_gap <= (FOOT_PART - FOOT_INSIDE_PART):
            lock_y = start_y + after_gap
            lock_center, name = self.calculator.foot(
                (x_pos, start_y),
                lock_start_y=lock_y
            )
            _, name2 = self.calculator.vertical(
                (x_pos, lock_y),
                half_vertical=True
            )
            self.material_counter.add(name)
            self.material_counter.add(name2)
            return lock_center, lock_y + (HALF_VERTICAL_PART - 20)
        
        else:
            lock_y = start_y + after_gap
            lock_center, name = self.calculator.foot(
                (x_pos, start_y),
                half_foot=True,
                lock_start_y=lock_y
            )
            _, name2 = self.calculator.vertical(
                (x_pos, lock_y),
                half_vertical=True
            )
            self.material_counter.add(name)
            self.material_counter.add(name2)
            return lock_center, lock_y + (HALF_VERTICAL_PART - 20)


class SegmentMaterialCalculator:
    """Calculates materials for a scaffold segment (row of modules)."""
    
    def __init__(self, height: float, slope: float,
                 material_counter: MaterialCounter,
                 calculator: CalculatorTopDown,
                 debug: DebugPrinter):
        self.height = height
        self.slope = slope
        self.material_counter = material_counter
        self.calculator = calculator
        self.debug = debug
        self.floor_calc = FloorCalculator(
            height, slope, material_counter, calculator, debug
        )
    
    def calculate(self, modules: List[int], use_slope: bool = True):
        """
        Calculate materials for a segment defined by module list.
        
        Args:
            modules: List of module lengths [250, 250, 150, ...]
            use_slope: If True, apply slope to this segment
        """
        if not modules:
            return
        
        effective_slope = self.slope if use_slope else 0
        self.floor_calc.slope = effective_slope
        
        # Calculate start points
        start_points = self.floor_calc.calculate_start_points(len(modules))
        max_point = max(start_points)
        
        # Process each column
        x_pos = 0
        for i, start_y in enumerate(start_points):
            self.floor_calc.process_column(x_pos, start_y, max_point)
            x_pos += HORIZONTAL_PART
        
        # Add floor materials
        self._add_floor_materials(modules)
    
    def _add_floor_materials(self, modules: List[int]):
        """Add floor-level materials (platforms, toe boards, etc.)."""
        floor_count = int(self.height // (VERTICAL_PART - 20))
        
        for module_len in modules:
            # Add platform for each module
            if module_len == 250:
                self.material_counter.add("platform_250")
            else:
                self.material_counter.add("platform_150")


class FacadeMaterialCalculator:
    """
    Calculates materials for all facades.
    Main entry point for material calculation.
    """
    
    def __init__(self, height: float, slope: float, 
                 toe_board: bool = True,
                 use_x_pattern: bool = False,
                 use_zigzag_pattern: bool = True,
                 verbose: bool = False):
        self.height = height
        self.slope = slope
        self.toe_board = toe_board
        self.use_x_pattern = use_x_pattern
        self.use_zigzag_pattern = use_zigzag_pattern
        self.debug = DebugPrinter(verbose)
        
        self.material_counter = MaterialCounter()
        self.calculator = CalculatorTopDown()
        
        self.segment_calc = SegmentMaterialCalculator(
            height, slope, self.material_counter, 
            self.calculator, self.debug
        )
    
    def calculate(self, facades: Dict[str, List]) -> Dict[str, int]:
        """
        Calculate all materials for given facades.
        
        Args:
            facades: Dictionary with F, R, B, L facade commands
            
        Returns:
            Dictionary of material counts
        """
        for key in ['F', 'R', 'B', 'L']:
            if key not in facades or not facades[key]:
                continue
            
            direction = DIRECTIONS[key]
            self._process_facade(facades[key], direction)
        
        return self.material_counter.counter_dict
    
    def _process_facade(self, commands: List[str], direction: Direction):
        """Process all commands for a single facade."""
        for cmd_str in commands:
            cmd = parse_facade_command(cmd_str)
            if cmd is None:
                continue
            
            self.debug.print(f"Processing {cmd['func']} at pos={cmd['pos']}")
            
            # Calculate modules for this segment
            modules = calculate_modules(cmd['length'])
            
            # Apply slope only for horizontal facades
            use_slope = direction.is_horizontal
            self.segment_calc.calculate(modules, use_slope)


# Backward compatibility functions
def top_down_calc(verbose: bool, facades: dict, h: float, slope: float,
                  toe_board: bool, use_x_pattern: bool, use_zigzag_pattern: bool) -> dict:
    """
    Legacy entry point for material calculation.
    Wraps FacadeMaterialCalculator for backward compatibility.
    """
    calculator = FacadeMaterialCalculator(
        height=h,
        slope=slope,
        toe_board=toe_board,
        use_x_pattern=use_x_pattern,
        use_zigzag_pattern=use_zigzag_pattern,
        verbose=verbose
    )
    return calculator.calculate(facades)
