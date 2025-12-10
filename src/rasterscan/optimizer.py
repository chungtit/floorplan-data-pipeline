from typing import List
from canonical_schema import Point2D, Wall, Room, Door, Floorplan
from shapely.geometry import Polygon


class FloorplanOptimizer:
    """
    Optimize floorplan based on user actions (add a bedroom, etc.)
    """
    
    def split_bedroom(self, floorplan: Floorplan, 
                    min_area: float = 10000) -> Floorplan:
        """
        Add a new bedroom to the floorplan by splitting the largest room
        It is a simple way to add a bedroom
        """
        # Find largest room and split it
        largest_room = max(floorplan.rooms, key=lambda r: r.area)
        
        # Split the largest room
        new_rooms = self._split_room(largest_room)
        
        # Replace old room with new rooms
        updated_rooms = [r for r in floorplan.rooms if r.id != largest_room.id]
        updated_rooms.extend(new_rooms)
        
        # Recalculate total area
        total_area = sum(r.area for r in updated_rooms)
        
        return Floorplan(
            rooms=updated_rooms,
            walls=floorplan.walls,
            total_area=total_area,
            perimeter=floorplan.perimeter,
            metadata={
                **floorplan.metadata,
                'optimized': True,
                'action': 'add_bedroom'
            }
        )
    
    def _split_room(self, room: Room) -> List[Room]:
        """
        Split a room into two rooms (one becomes new bedroom)
        """
        poly = room.get_polygon()
        if not poly:
            return [room]
        
        # Get bounding box
        minx, miny, maxx, maxy = poly.bounds
        
        # Split along longer dimension
        width = maxx - minx
        height = maxy - miny
        
        if width > height:
            # Split vertically
            mid_x = (minx + maxx) / 2
            room1_vertices = [
                Point2D(minx, miny),
                Point2D(mid_x, miny),
                Point2D(mid_x, maxy),
                Point2D(minx, maxy)
            ]
            room2_vertices = [
                Point2D(mid_x, miny),
                Point2D(maxx, miny),
                Point2D(maxx, maxy),
                Point2D(mid_x, maxy)
            ]
        else:
            # Split horizontally
            mid_y = (miny + maxy) / 2
            room1_vertices = [
                Point2D(minx, miny),
                Point2D(maxx, miny),
                Point2D(maxx, mid_y),
                Point2D(minx, mid_y)
            ]
            room2_vertices = [
                Point2D(minx, mid_y),
                Point2D(maxx, mid_y),
                Point2D(maxx, maxy),
                Point2D(minx, maxy)
            ]
        
        # Create new rooms
        room1 = Room(
            id=f"{room.id}_1",
            room_type=room.room_type,
            vertices=room1_vertices,
            area=Polygon([(v.x, v.y) for v in room1_vertices]).area,
            doors=[],
            windows=[]
        )
        
        room2 = Room(
            id=f"{room.id}_2_bedroom",
            room_type="bedroom",
            vertices=room2_vertices,
            area=Polygon([(v.x, v.y) for v in room2_vertices]).area,
            doors=[],
            windows=[]
        )
        
        return [room1, room2]
    