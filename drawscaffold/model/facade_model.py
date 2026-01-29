from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class FacadeFeature:
    feature_type: str  # 'inset', 'outset', 'wall'
    position: int
    length: int
    depth: int
    side: str # 'F', 'R', 'B', 'L'

    @classmethod
    def from_string(cls, data: str):
        # Format: "type,pos,length,depth,side"
        parts = data.split(',')
        if len(parts) < 5:
            raise ValueError(f"Invalid feature string: {data}")
        return cls(
            feature_type=parts[0].lower(),
            position=int(parts[1]),
            length=int(parts[2]),
            depth=int(parts[3]),
            side=parts[4].upper()
        )

@dataclass
class TopDownProject:
    features_by_side: dict[str, List[FacadeFeature]] = field(default_factory=lambda: {'F': [], 'R': [], 'B': [], 'L': []})
    
    def add_feature(self, feature: FacadeFeature):
        self.features_by_side[feature.side].append(feature)

    @classmethod
    def from_args(cls, facades: List[str]):
        project = cls()
        if not facades:
            return project
            
        for f_str in facades:
            # Helper to categorize into F, R, B, L similar to current main
            # Current main logic splits inputs into a dict based on containing char.
            # We should follow that logic carefully or improve it.
            # The current logic: if 'F' in string, put in 'F' list. 
            # "inset,0,1000,0,F" -> contains 'F'
            
            # The current logic is a bit fuzzy, let's look at top_down_main.py again.
            # It iterates keys 'F', 'R'... and checks if key in string.
            
            project._parse_and_add(f_str)
            
        return project

    def _parse_and_add(self, f_str: str):
        # Improved parsing logic logic
        created = False
        parts = f_str.split(',')
        if len(parts) >= 5:
             # The side is the last element usually
             side = parts[-1].strip().upper()
             if side in self.features_by_side:
                 self.add_feature(FacadeFeature.from_string(f_str))
                 created = True
        
        if not created:
             # Fallback to loose matching if strict parsing failed or if format implies different structure?
             # For now assume strict format as per argparse help
             pass
