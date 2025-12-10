import math
from typing import List, Dict
from dataclasses import dataclass
from shapely.geometry import Polygon

@dataclass
class Point2D:
    x: float
    y: float
    
    def distance_to(self, other: 'Point2D') -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

@dataclass
class Door:
    position: List[Point2D]
    width: float
    connects_rooms: List[str] = None
    
    def get_center(self) -> Point2D:
        bbox = self.position
        center_x = sum(p.x for p in bbox) / len(bbox)
        center_y = sum(p.y for p in bbox) / len(bbox)
        return Point2D(center_x, center_y)

@dataclass
class Window:
    position: List[Point2D]
    width: float

@dataclass
class Wall:
    """
    Wall representation with start/end points
    """
    start: Point2D
    end: Point2D
    
    def length(self) -> float:
        return self.start.distance_to(self.end)
    
    

@dataclass
class Room:
    id: str
    room_type: str
    vertices: List[Point2D]
    area: float
    doors: List[Door]
    windows: List[Window]
    
    def get_polygon(self) -> Polygon:
        coords = [(p.x, p.y) for p in self.vertices]
        if len(coords) < 3:
            return None
        return Polygon(coords)
    

@dataclass
class Floorplan:

    rooms: List[Room]
    walls: List[Wall]
    total_area: float
    perimeter: float
    metadata: Dict = None
    
    def to_dict(self) -> Dict:
        """
        Convert to dictionary for JSON serialization
        """
        return {
            'rooms': [
                {
                    'id': r.id,
                    'room_type': r.room_type,
                    'vertices': [{'x': v.x, 'y': v.y} for v in r.vertices],
                    'area': r.area,
                    'doors': [{'position': [{'x': p.x, 'y': p.y} for p in d.position], 
                              'width': d.width} for d in r.doors],
                    'windows': [{'position': [{'x': p.x, 'y': p.y} for p in w.position], 
                                'width': w.width} for w in r.windows]
                }
                for r in self.rooms
            ],
            'walls': [
                {
                    'start': {'x': w.start.x, 'y': w.start.y},
                    'end': {'x': w.end.x, 'y': w.end.y},
                    'length': w.length()
                }
                for w in self.walls
            ],
            'total_area': self.total_area,
            'perimeter': self.perimeter,
            'metadata': self.metadata or {}
        }
