import json
from pathlib import Path

from helper import load_json
from cleaner import FloorplanCleaner
from optimizer import FloorplanOptimizer
from recognizer import FloorplanRecognizer

def run_pipeline(input_image_path: str, output_raw_path: str, output_cleaned_path: str, 
                 output_optimized_path: str):
    
    print("STARTING FLOORPLAN PROCESSING PIPELINE")

    # Task 1: Recognize and load raw data

    # Please add the API key to your .env file before running the recognizer
    # recognizer = FloorplanRecognizer(method="rasterscan")
    # raw_data = recognizer.recognize_from_image(input_image_path, output_raw_path)

    print("\n[Task 1] Loading recognizer output...")
    raw_data = load_json(output_raw_path)
    print(f"Completed Task 1:\n -> Found {len(raw_data.get('rooms', []))} rooms; {len(raw_data.get('walls', []))} walls; {len(raw_data.get('doors', []))} doors")
    
    # Task 2: Clean and post-process
    print("\n[Task 2] Cleaning and post-processing...")
    cleaner = FloorplanCleaner(snap_threshold=5.0)
    cleaned_floorplan = cleaner.clean(raw_data)
    print(f"Completed Task 2:\n -> Cleaned to {len(cleaned_floorplan.rooms)} rooms")
   
    # Save cleaned floorplan
    with open(output_cleaned_path, 'w') as f:
        json.dump(cleaned_floorplan.to_dict(), f, indent=2)
    print(f" -> Saved to: {output_cleaned_path}")
    
    # Task 3: Optimize (add bedroom)
    print("\n[Task3] Optimizing: Adding bedroom...")
    optimizer = FloorplanOptimizer()
    # add a bedroom by splitting the biggest room
    optimized_floorplan = optimizer.split_bedroom(cleaned_floorplan)
    
    bedroom_count = sum(1 for r in optimized_floorplan.rooms 
                       if 'bedroom' in r.room_type.lower())
    print(f"Completed Task 3: \n -> Rooms after optimization: {len(optimized_floorplan.rooms)} \n -> Total bedrooms: {bedroom_count}")
    
    # Save optimized floorplan
    with open(output_optimized_path, 'w') as f:
        json.dump(optimized_floorplan.to_dict(), f, indent=2)
    print(f" -> Saved to: {output_optimized_path}")
    
    print("PIPELINE COMPLETE")
    
    return cleaned_floorplan, optimized_floorplan



if __name__ == "__main__":

    # Create output directory
    output_dir = Path("outputs/rasterscan")
    output_dir.mkdir(exist_ok=True)

    # Run pipeline
    cleaned, optimized = run_pipeline(
        input_image_path = "floorplan-images/floorplan_raw.png",
        output_raw_path= output_dir / "recognizer_raw.json",
        output_cleaned_path=output_dir / "cleaned_canonical.json",
        output_optimized_path=output_dir / "optimized.json"
    )