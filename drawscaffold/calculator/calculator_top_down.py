from typing import Sequence

from drawscaffold.const.conts import VERTICAL_PART, HALF_VERTICAL_PART, HORIZONTAL_PART, SMALL_HORIZONTAL_PART


class CalculatorTopDown:
    def L_part(self, start_point: Sequence[float]):
        x, y = start_point
        height = VERTICAL_PART
        name = "l_part"
        conn_center = (x, y + ((height - 24) + (height - 21)) / 2)
        return conn_center, name

    def tie(self):
        name = "tie"
        return name

    def start(self):
        name = "start"
        return name

    def vertical(self, start_point: Sequence[float], half_vertical: bool = False):
        x, y = start_point
        height = HALF_VERTICAL_PART if half_vertical else VERTICAL_PART
        name = f"vert_{int(height)}cm"
        conn_center = (x, y + ((height-24) + (height-21)) / 2)
        return conn_center, name

    def horizontal(self, small: bool):
        L = HORIZONTAL_PART
        if small:
            L = SMALL_HORIZONTAL_PART

        name = f"PLATFORM_{int(L)}"
        return None, name

    def support(self, small: bool):
        L = HORIZONTAL_PART
        if small:
            L = SMALL_HORIZONTAL_PART
        name = f"SUPPORT_{int(L)}"
        return None, name

    def foot(self, start_point: Sequence[float],
                  half_foot: bool = False, complete_foot: bool = False,
                  lock_start_y: float = 0.0):
        x, y = start_point
        name = "FOOT_STD"
        if half_foot:
            name = "FOOT_HALF"
        elif complete_foot:
            name = "FOOT_FULL"
        lock_cy = lock_start_y - 2.0
        return (x, lock_cy), name

    def adjustment(self, start_point: Sequence[float],
                        adjustment_height: float, lock_height: float):
        x, y = start_point
        name = f"ADJ_{int(adjustment_height)}"
        lock_space = 0.5
        lock_start_y = y + (lock_height - lock_space)
        lock_cy = lock_start_y - 2.0
        return (x, lock_cy), name

    def diagonal(self):
        name = "DIAGONAL"
        return None, name

    def sign(self, text: str):
        name = f"SIGN_{text}"
        return None, name