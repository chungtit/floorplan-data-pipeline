"""
TASK 1: Image -> Raw JSON (with HF/LLM)
"""
import requests
import base64
import os
from typing import List, Dict, Tuple, Optional
from dotenv import load_dotenv
from helper import save_json

load_dotenv()

class FloorplanRecognizer:

    def __init__(self, method: str = "hf"):
        """
        Args:
            method: 'rasterscan' for RasterScan API, 'llm' for multimodal LLM
        """
        self.method = method
        
    def recognize_from_image(self, image_path: str, out_path: str) -> Dict:
        if self.method == "rasterscan":
            return self._recognize_rasterscan(image_path, out_path)
        elif self.method == "llm":
            return self._recognize_llm(image_path, out_path)
    
    def _recognize_rasterscan(self, image_path: str, out_path: str) -> Dict:
        """
        This code was adapted from the following publicly available source: 
        https://www.rasterscan.com/#demo
        """

        # Convert image to base64
        def image_to_base64(image_path):
            with open(image_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')

        # Raster to Vector Base64
        image_base64 = image_to_base64(image_path)

        url = "https://backend.rasterscan.com/raster-to-vector-base64"
        payload = {"image": image_base64}
        headers = {
            "x-api-key": os.getenv("RASTER_API_KEY"),
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)

        # Raster to Vector Raw
        with open(image_path, 'rb') as f:
            files = {'image': f}
            headers = {
                "x-api-key": os.getenv("RASTER_API_KEY")
            }
            response = requests.post(
                'https://backend.rasterscan.com/raster-to-vector-raw',
                files=files,
                headers=headers
            )

        # Save raw output
        save_json(response.json(), out_path)
        return response.json()
            
    def _recognize_llm(self, image_path: str) -> Dict:
        """
        Use multimodal LLM for recognition.
        Could use Claude, GPT, or Gemini Vision.
        """
        # see: src/gemini/gemini_processor.py
        # keep this as a placeholder for feature implementation
        pass