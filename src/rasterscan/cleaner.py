from typing import List, Dict
from canonical_schema import Point2D, Wall, Room, Door, Floorplan
from shapely.geometry import Polygon, Point

class FloorplanCleaner:
    """
    Clean and normalize raw recognizer output
    """
    
    def __init__(self, snap_threshold: float = 5.0):
        self.snap_threshold = snap_threshold
    
    def clean(self, raw_data: Dict) -> Floorplan:
        
        # Extract and clean walls
        walls = self._extract_walls(raw_data.get('walls', []))
        walls = self._snap_vertices(walls)
        
        # Extract and clean rooms
        rooms = self._extract_rooms(raw_data.get('rooms', []))
        
        # Extract doors
        doors = self._extract_doors(raw_data.get('doors', []))
        
        # Assign doors to rooms
        self._assign_doors_to_rooms(rooms, doors)
        
        # Calculate metrics
        total_area = sum(r.area for r in rooms)
        perimeter = raw_data.get('perimeter', 0)
        
        metadata = {
            'source': 'RasterScan Recognizer',
            'cleaned': True,
            'room_count': len(rooms)
        }
        
        return Floorplan(
            rooms=rooms,
            walls=walls,
            total_area=total_area,
            perimeter=perimeter,
            metadata=metadata
        )
    
    def _extract_walls(self, wall_data: List[Dict]) -> List[Wall]:
        """
        Extract walls from raw data
        """
        walls = []
        for w in wall_data:
            pos = w.get('position', [])
            if len(pos) >= 2:
                start = Point2D(pos[0][0], pos[0][1])
                end = Point2D(pos[1][0], pos[1][1])
                walls.append(Wall(start, end))
        return walls
    
    def _snap_vertices(self, walls: List[Wall]) -> List[Wall]:
        """
        Snap nearby wall endpoints together by calculating the distance between them
        Update the wall endpoints to the averaged position if they are within the snap threshold
        """
        if not walls:
            return walls
        
        # Collect all endpoints
        points = []
        for w in walls:
            points.append(w.start)
            points.append(w.end)
        
        # Group nearby points
        for i, p in enumerate(points):
            if i % 2 == 0:
                # Find nearby points
                for j, other in enumerate(points[i+1:], i+1):
                    if p.distance_to(other) < self.snap_threshold:
                        # Snap to average position
                        avg_x = (p.x + other.x) / 2
                        avg_y = (p.y + other.y) / 2
                        points[i] = Point2D(avg_x, avg_y)
                        points[j] = Point2D(avg_x, avg_y)
        
        # Reconstruct walls with snapped points
        new_walls = []
        for i in range(0, len(points), 2):
            if i + 1 < len(points):
                new_walls.append(Wall(points[i], points[i+1]))
        
        return new_walls
    
    def _extract_rooms(self, room_data: List[List[Dict]]) -> List[Room]:
        """
        Extract and clean rooms from raw data
        """
        rooms = []
        
        for i, room_vertices in enumerate(room_data):
            if not room_vertices or len(room_vertices) < 3:
                continue
            
            # Extract vertices
            vertices = []
            for v in room_vertices:
                vertices.append(Point2D(v['x'], v['y']))
            
            # Remove duplicate consecutive vertices
            vertices = self._remove_duplicate_vertices(vertices)
            
            if len(vertices) < 3:
                continue
            
            # Calculate area
            poly = Polygon([(v.x, v.y) for v in vertices])
            area = poly.area if poly.is_valid else 0
            
            room_type = self._infer_room_type(area, i)
            
            room = Room(
                id=f"room_{i}",
                room_type=room_type,
                vertices=vertices,
                area=area,
                doors=[],
                windows=[]
            )
            rooms.append(room)
        
        return rooms
    
    def _remove_duplicate_vertices(self, vertices: List[Point2D]) -> List[Point2D]:
        """
        Remove consecutive duplicate vertices
        """
        if not vertices:
            return []
        
        cleaned = [vertices[0]]
        for v in vertices[1:]:
            if v.distance_to(cleaned[-1]) > 1.0:  # Threshold for duplicates
                cleaned.append(v)
        
        return cleaned

    
    def _infer_room_type(self, area: float, index: int) -> str:
        """
        Infer room type based on area (simple heuristic)
        """
        if area < 5000:
            return "bathroom"
        elif area < 15000:
            return "bedroom"
        elif area < 30000:
            return "living_room"
        else:
            return "unknown"
    
    def _extract_doors(self, door_data: List[Dict]) -> List[Door]:
        """
        Extract doors from raw data
        """
        doors = []
        for d in door_data:
            bbox = d.get('bbox', [])
            if len(bbox) >= 4:
                position = [Point2D(bbox[i][0], bbox[i][1]) for i in range(4)]
                # Calculate width
                width = position[0].distance_to(position[1])
                doors.append(Door(position, width))
        return doors
    
    def _assign_doors_to_rooms(self, rooms: List[Room], doors: List[Door]):
        """
        Assign doors to rooms based on proximity
        """
        for door in doors:
            door_center = door.get_center()
            door_point = Point(door_center.x, door_center.y)
            
            # Find rooms that contain or are close to the door
            min_dist = float('inf')
            closest_room = None
            
            for room in rooms:
                poly = room.get_polygon()
                if poly:
                    # Check if door is on room boundary
                    dist = poly.exterior.distance(door_point)
                    if dist < min_dist and dist < 20:  # Threshold
                        min_dist = dist
                        closest_room = room
            
            if closest_room:
                closest_room.doors.append(door)
