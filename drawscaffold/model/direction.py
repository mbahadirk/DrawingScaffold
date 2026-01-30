"""
Direction abstraction for facade processing.
Reduces code duplication by providing unified direction vectors.
"""
from dataclasses import dataclass
from typing import Tuple
from drawscaffold.const.top_down_enum import ScaffoldSide


@dataclass
class Direction:
    """Represents a facade direction with movement vectors."""
    key: str  # F, R, B, L
    dx: int   # X movement direction (-1, 0, 1)
    dy: int   # Y movement direction (-1, 0, 1)
    gap_offset: Tuple[int, int]  # Gap offset for this direction
    scaffold_side: ScaffoldSide  # Which side scaffolds face
    is_horizontal: bool  # True for F/B, False for R/L
    
    @property
    def depth_dx(self) -> int:
        """X direction for depth movement (perpendicular to main)."""
        return self.dy  # Perpendicular
    
    @property
    def depth_dy(self) -> int:
        """Y direction for depth movement (perpendicular to main)."""
        return -self.dx  # Perpendicular


# Direction constants
DIRECTIONS = {
    'F': Direction(
        key='F', 
        dx=1, dy=0, 
        gap_offset=(0, -25),
        scaffold_side=ScaffoldSide.FRONT,
        is_horizontal=True
    ),
    'R': Direction(
        key='R', 
        dx=0, dy=1, 
        gap_offset=(25, 0),
        scaffold_side=ScaffoldSide.RIGHT,
        is_horizontal=False
    ),
    'B': Direction(
        key='B', 
        dx=-1, dy=0, 
        gap_offset=(0, 25),
        scaffold_side=ScaffoldSide.BACK,
        is_horizontal=True
    ),
    'L': Direction(
        key='L', 
        dx=0, dy=-1, 
        gap_offset=(-25, 0),
        scaffold_side=ScaffoldSide.LEFT,
        is_horizontal=False
    ),
}

# Neighbor mappings for outset calculations
PREV_DIRECTION = {'F': 'L', 'R': 'F', 'B': 'R', 'L': 'B'}
NEXT_DIRECTION = {'F': 'R', 'R': 'B', 'B': 'L', 'L': 'F'}


def calculate_modules(length: int, prefer_gaps: bool = False) -> list:
    """
    Calculate scaffold modules needed to fill a given length.
    
    Args:
        length: Length in cm
        prefer_gaps: If True, skip 150cm modules
        
    Returns:
        List of module lengths (250 or 150)
    """
    if length < 100:
        return []
    
    modules = []
    remaining = length
    
    # Fill with 250cm modules
    while remaining >= 245:
        modules.append(250)
        remaining -= 250
    
    # Fill remainder with 150cm modules
    if not prefer_gaps:
        while remaining >= 150:
            modules.append(150)
            remaining -= 150
    
    return modules


def parse_facade_command(item: str) -> dict:
    """
    Parse a facade command string into a dictionary.
    
    Args:
        item: Command string like "inset,300,1200,250,F"
        
    Returns:
        Dictionary with func, pos, length, depth, side
    """
    values = str(item).split(',')
    if len(values) < 5:
        return None
    
    return {
        'func': str(values[0]).lower(),
        'pos': int(values[1]),
        'length': int(values[2]),
        'depth': int(values[3]),
        'side': str(values[4]).upper()
    }
