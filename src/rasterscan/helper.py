"""
Utility functions for floorplan processing
"""
import json
from pathlib import Path
from typing import Dict, List


def load_json(file_path: str) -> Dict:
    with open(file_path, 'r') as f:
        return json.load(f)


def save_json(data: Dict, file_path: str, indent: int = 2):
    output_path = Path(file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=indent)

def project_src_rasterscan_path() -> Path:
    return Path(__file__).resolve().parents[1] / 'src' / 'rasterscan'