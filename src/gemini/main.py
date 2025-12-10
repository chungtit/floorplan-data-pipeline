import os
import json
from pathlib import Path
from typing import Dict
from gemini_processor import GeminiFloorplanProcessor


def save_json(data: Dict, filepath: Path):
    """Save data to JSON file with pretty formatting"""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"  Saved: {filepath}")


def main():
    
    # Configuration
    API_KEY = os.environ.get('GOOGLE_API_KEY')
    
    if not API_KEY:
        print("ERROR: No API key found!")
        return
    
    # Setup
    output_dir = Path("output/gemini")
    output_dir.mkdir(exist_ok=True)
    
    input_image = "floorplan-images/floorplan_raw.png"
    
    # Initialize processor
    processor = GeminiFloorplanProcessor(api_key=API_KEY)
    
    # TASK 1: recognize
    try:
        raw_output = processor.recognize(input_image)
        raw_path = output_dir / "recognition_raw.json"
        save_json(raw_output, raw_path)
    except Exception as e:
        print(f"\nPipeline failed at recognition stage: {e}")
        return
    
    # TASK 2: clean
    try:
        cleaned_output = processor.clean(raw_output)
        cleaned_path = output_dir / "cleaned_canonical.json"
        save_json(cleaned_output, cleaned_path)
    except Exception as e:
        print(f"\nPipeline failed at cleaning stage: {e}")
        return
    
    # TASK 3: optimize
    try:
        # Example optimization action
        action = {
            "action": "add_room",
            "room_type": "bedroom",
            "constraints": {
                "min_area_m2": 12.0,
                "natural_light": True,
                "adjacent_to": "living_room"
            },
            "user_request": "Add a bedroom with natural light, at least 12 square meters, next to the living room"
        }
        
        optimized_output = processor.optimize(cleaned_output, action)
        optimized_path = output_dir / "optimized.json"
        save_json(optimized_output, optimized_path)
    except Exception as e:
        print(f"\nPipeline failed at optimization stage: {e}")
        return

if __name__ == "__main__":
    main()