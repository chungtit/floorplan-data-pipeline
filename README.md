# Part 2: Floorplan Data Pipeline

A Python pipeline for extracting, cleaning, and optimizing floorplan data from images

## Table of Contents
- [Overview](#overview)
- [Installation](#installation)
- [Usage](#usage)
  - [Run the pipeline with RasterScan](#run-the-pipeline-with-rasterscan)
  - [Run the pipeline with Gemini](#run-the-pipeline-with-gemini)
  <!-- - [Run with Apache Airflow (part 2 - task 4)](#run-with-apache-airflow-part-2---task-4) -->

## Overview
**Note**: Part 2 mentioned about RasterScan (from Hugging Face) and Gemini, emphasizing 2 things: 1)**prompt engineering** and 2) **the data pipeline**. Because of this, the repository was designed to be more open-ended and to keep RasterScan and Gemini separate. RasterScan produces deterministic outputs, while generative AI is non-deterministic. Keeping them separate is useful for future work, whether we want to use the data to train our own models or monitor hallucinations that could mess our cleaned dataset, or enables AI-driven solution based on user actions.

For ETL / Data Pipeline Design (Part 2, task 4), please find in `DESIGN.md`.

## Installation

1. Clone the repository and navigate to it:
```bash
cd floorplan-data-pipeline
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables (if using RasterScan API, Gemini):
```bash
# Create and edit .env file
RASTER_API_KEY=your_raster_api_key_here
GOOGLE_API_KEY=your_google_ai_api_key_here
GEMINI_MODEL=gemini_model_you_use
```

## Usage

### Run the pipeline with RasterScan:
```bash
python src/rasterscan/main.py
```
This workflow is focused on data flow:
1. Found the canonical schema in `src/rasterscan/canonical_chema.py`
2. Load raw floorplan data and recognize with RasterScan API
3. Clean and validate the geometry with deterministic outputs
4. Apply optimizations (e.g., add bedrooms by splitting the biggest room, or add a new bedroom)
5. Save outputs to `outputs/rasterscan`
6. Airflow orchestration is available in the `airflow/dags` directory

### Run the pipeline with Gemini:
```bash
python src/gemini/main.py
```
This workflow is focused on prompt engineering:
1. Load raw floorplan data and use Gemini API to get JSON output file
2. Clean and validate the geometry by using prompts in `src/gemini/prompy.py`
3. Apply optimizations (e.g., add bedrooms with additional constraints, such as only creating rooms that fit within the property boundary since we cannot extend construction onto a neighbor’s land). Prompt engineering provides more flexibility when defining these constraints
4. Save outputs to `outputs/gemini`


## Outputs
The outputs of Gemini and RasterScan are saved in the `outputs` directory:
- **Gemini**:
The raw recognizer JSON from Gemini contains rich contextual information, including room types. This gives users flexibility to decide how to clean the data and optimize the floorplan (e.g., adding rooms, removing walls). However, the outputs are not always accurate. For example, Gemini might label a room as an ``office`` even when the floorplan is for a family house with no office. To improve reliability, we can extend Gemini with Agents that detect issues and guide users toward final answers

- **RasterScan** (with hardcoded cleaner and optimizer):
RasterScan's raw recognizer JSON does not include room types, so it lacks rich context. All actions (e.g., adding walls, splitting rooms) are predefined, making the outcomes predictable, easy to control, and simple to debug or backtrack. However, users cannot perform actions beyond what has been defined, which limits flexibility but ensures consistency