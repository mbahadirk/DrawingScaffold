class DebugPrinter:
    def __init__(self, debug_mode: bool):
        self.debug_mode = debug_mode

    def print(self, obj):
        if self.debug_mode:
            print(obj)
