import json
import os
from typing import Dict, Optional
from datetime import datetime
from PIL import Image
import google.generativeai as genai

from prompts import (
    RECOGNITION_PROMPT,
    CLEANING_PROMPT_TEMPLATE,
    OPTIMIZATION_PROMPT_TEMPLATE
)


class GeminiFloorplanProcessor:
    """
    Main processor class that handles all three tasks:
    1. Recognition (image -> JSON)
    2. Cleaning 
    3. Optimization
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('GOOGLE_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "No API key provided. Set GOOGLE_API_KEY environment variable "
                "or pass api_key parameter"
            )
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(os.environ.get('GEMINI_MODEL'))
        
    
    def recognize(self, image_path: str) -> Dict:
        """
        Task 1: Extract floorplan structure from image
        """
        print(f"\nTASK 1: Recognition Processing Floorplan")
        # Load image
        img = Image.open(image_path)
        
        try:
            response = self.model.generate_content([RECOGNITION_PROMPT, img])
            result = self._extract_json(response.text)
            
            print(f"TASK 1: Recognition complete!")
            return result
            
        except Exception as e:
            print(f"Error during recognition: {e}")
            raise
    
    def clean(self, raw_json: Dict) -> Dict:
        """
        Task 2: Clean and validate floorplan data
        """
        print(f"\nTASK 2: Cleaning Floorplan Data")
        # Format prompt with data
        prompt = CLEANING_PROMPT_TEMPLATE.format(
            raw_json=json.dumps(raw_json, indent=2),
            timestamp=datetime.now().isoformat()
        )
        
        try:
            response = self.model.generate_content(prompt)
            result = self._extract_json(response.text)
            print(f"TASK 2: Cleaning complete!")
            return result
            
        except Exception as e:
            print(f"Error during cleaning: {e}")
            raise
    
    def optimize(self, canonical_json: Dict, action: Dict) -> Dict:
        """
        Task 3: Optimize floorplan based on natural language action
        """
        print(f"\nTASK 3: Optimizing Floorplan")

        # Format prompt with data
        prompt = OPTIMIZATION_PROMPT_TEMPLATE.format(
            canonical_json=json.dumps(canonical_json, indent=2),
            action=json.dumps(action, indent=2),
            timestamp=datetime.now().isoformat()
        )
        
        try:
            response = self.model.generate_content(prompt)
            result = self._extract_json(response.text)
            print(f"TASK 3: Optimization complete")
            return result
            
        except Exception as e:
            print(f"Error during optimization: {e}")
            raise
    
    def _extract_json(self, response_text: str) -> Dict:
        """
        Extract JSON from Gemini response
        """
        text = response_text.strip()
        
        # Remove markdown code blocks if present
        if text.startswith('```'):
            parts = text.split('```')
            if len(parts) >= 3:
                text = parts[1]
                if text.startswith('json'):
                    text = text[4:]
                text = text.strip()
        
        # Parse JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"\n[ERROR] Failed to parse JSON response:")
            print(f"Response text: {text[:500]}...")
            raise ValueError(f"Invalid JSON from Gemini: {e}")

