# Task 1: Recognition - Extract floorplan structure from image
RECOGNITION_PROMPT = """You are an AI assistant. 

Analyze this floorplan image and extract its structure as JSON.

Your task:
1. Identify all rooms and their types (bedroom, living_room, kitchen, bathroom, etc.)
2. Determine room boundaries as polygon vertices (x, y coordinates in meters)
3. Locate walls with start/end points and thickness
4. Find doors and windows with their positions and dimensions
5. Calculate room areas

Output requirements:
- Use meters as the unit for all measurements
- Coordinates should be relative to the top-left corner (0,0)
- Estimate typical dimensions (e.g., bedroom ~12-20m², wall thickness ~0.15m)
- Provide confidence scores where uncertain

Return ONLY valid JSON in this exact format (no markdown, no explanations):

{
  "version": "1.0",
  "source": "llm_recognition",
  "timestamp": "ISO-8601",
  "rooms": [
    {
      "id": "r1",
      "type": "bedroom",
      "vertices": [[x1, y1], [x2, y2], [x3, y3], [x4, y4]],
      "area": 15.5,
      "confidence": 0.9
    }
  ],
  "walls": [
    {
      "id": "w1",
      "start": [x1, y1],
      "end": [x2, y2],
      "thickness": 0.15
    }
  ],
  "doors": [
    {
      "id": "d1",
      "position": [x, y],
      "width": 0.9,
      "connects": ["r1", "hallway"]
    }
  ],
  "windows": [
    {
      "id": "win1",
      "position": [x, y],
      "width": 1.2,
      "room": "r1"
    }
  ]
}"""


# Task 2: Cleaning - Validate and normalize floorplan data
CLEANING_PROMPT_TEMPLATE = """You are a geometric data validator for floorplan processing.

Given this raw floorplan data (potentially noisy from computer vision):

{raw_json}

Your tasks:
1. Validate room polygons are closed and properly formed
2. Snap near-coincident vertices to the same coordinate (tolerance: 0.2m)
3. Normalize all wall thickness to 0.15m
4. Ensure room vertices form valid, non-self-intersecting polygons
5. Calculate accurate room areas
6. Identify which rooms are adjacent (sharing walls)
7. Fix any obvious geometric errors

Output requirements:
- Snap coordinates to 0.1m precision (e.g., 10.12 -> 10.1)
- All wall thickness should be 0.15m
- Room polygons should be counter-clockwise
- Include adjacency_graph showing which rooms touch

Return ONLY valid JSON in this format (no markdown):

{{
  "version": "1.0",
  "schema": "canonical_v1",
  "timestamp": "{timestamp}",
  "metadata": {{
    "total_area": <sum of all room areas>,
    "room_count": <number of rooms>,
    "wall_thickness_normalized": 0.15,
    "cleaning_applied": true
  }},
  "rooms": [
    {{
      "id": "r1",
      "type": "bedroom",
      "vertices": [[x, y], ...],
      "area": <calculated area>,
      "adjacent_rooms": ["r2", "r3"],
      "metadata": {{"confidence": 0.9}}
    }}
  ],
  "walls": [...],
  "doors": [...],
  "windows": [...],
  "adjacency_graph": {{
    "r1": ["r2", "r3"],
    "r2": ["r1"]
  }}
}}"""


# Task 3: Optimization - Modify floorplan based on natural language actions
OPTIMIZATION_PROMPT_TEMPLATE = """You are an architectural AI assistant optimizing floorplans.

Current floorplan:
{canonical_json}

User action:
{action}

Your task:
1. Understand the user's intent from the action
2. Apply architectural and spatial reasoning
3. Modify the floorplan accordingly while respecting:
   - Minimum area constraints
   - Room adjacency preferences
   - Structural feasibility
   - Building codes (e.g., bedroom min 7m², bathroom min 2.5m²)

For "add_room":
- Place the new room logically adjacent to existing rooms
- Ensure minimum area is met
- Update adjacency graph
- Add appropriate walls, doors if needed

For "remove_room":
- Remove the specified room
- Update adjacency graph
- Recalculate total area

For "resize_room":
- Adjust room boundaries
- Maintain valid geometry
- Update area calculation

Return ONLY the complete modified floorplan JSON (same schema as input):

{{
  "version": "1.0",
  "schema": "canonical_v1",
  "timestamp": "{timestamp}",
  "metadata": {{
    "total_area": <updated>,
    "room_count": <updated>,
    "optimization_applied": {action}
  }},
  "rooms": [...],
  "walls": [...],
  "doors": [...],
  "windows": [...],
  "adjacency_graph": {{...}}
}}"""