# Floorplan Data Pipeline - Design Document

**Author:** Chung Luong  
**Date:** December 2025  
**Version:** 1.0

---

## 1. Executive Summary

This document describes the design of a data pipeline for floorplan. The pipeline converts floorplan images into structured data, applies cleaning and optimizing.

### Key Capabilities
- Automated floorplan recognition from images (raster/vector)
- Geometric data cleaning and canonicalization
- Room adjacency graph construction
- AI-powered floorplan optimization
- Full data lineage and versioning

---

## 2. Pipeline Architecture

### 2.1 High-Level Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│   Image/    │────▶│  Recognizer  │────▶│   Cleaner   │────▶│  Optimizer   │
│   SVG       │     │   (ML/LLM)   │     │ (Geometry)  │     │   (AI)       │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
                           │                    │                    │
                           ▼                    ▼                    ▼
                    ┌──────────────────────────────────────────────────┐
                    │          Storage Layers (Bronze/Silver/Gold)     │
                    └──────────────────────────────────────────────────┘
```

### 2.2 Pipeline Stages

#### Stage 1: Recognition (Bronze Layer - Raw Ingestion)
- Input: Floorplan images (PNG, JPG) or SVG files
- Process: 
  - ML-based recognition (Computer Vision models such as RasterScan) OR LLM-based multimodal understanding (Gemini)
  - Extract rooms, walls, doors, windows
- Output: Raw JSON with noisy geometric data
- Storage: `bronze.raw_recognitions` table (Assume that we have a database with 3 tables: bronze, silver, gold)

#### Stage 2: Cleaning & Post-Processing (Silver Layer - Filted, cleaned, or augmented)
- Input: Raw recognition JSON
- Process:
  - Snap vertices to grid, close polygon gaps, normalize wall thickness, validate topology
- Output: Cleaned JSON
- Storage: `silver.cleaned_floorplans` table

#### Stage 3: Optimization (Gold Layer - Business-level aggregates)
- Input: cleaned JSON + user action
- Process:
  - Optimization (add/remove/resize rooms), constraint satisfaction, adjacency preservation
- Output: Optimized floorplan
- **Storage:** `gold.optimized_floorplans` table

---

## 3. Data Storage Model

### 3.1 Storage Layers (Medallion Architecture)

#### Bronze Layer (Raw)
```sql
CREATE TABLE bronze.raw_recognitions (
    recognition_id UUID PRIMARY KEY,
    upload_id UUID REFERENCES uploads(upload_id),
    created_at TIMESTAMP,
    recognizer_version VARCHAR(50),
    raw_json JSONB,
    image_url TEXT,
    metadata JSONB
);

CREATE INDEX idx_raw_upload ON bronze.raw_recognitions(upload_id);
CREATE INDEX idx_raw_created ON bronze.raw_recognitions(created_at);
```

#### Silver Layer (Cleaned)
```sql
CREATE TABLE silver.cleaned_floorplans (
    cleaned_id UUID PRIMARY KEY,
    recognition_id UUID REFERENCES bronze.raw_recognitions(recognition_id),
    created_at TIMESTAMP,
    cleaner_version VARCHAR(50),
    cleaned_json JSONB,
    validation_passed BOOLEAN,
    cleaning_stats JSONB, -- snaps applied, gaps closed, etc.
    metadata JSONB
);

CREATE INDEX idx_cleaned_recognition ON silver.cleaned_floorplans(recognition_id);
```

#### Gold Layer (Optimized)
```sql
CREATE TABLE gold.optimized_floorplans (
    optimization_id UUID PRIMARY KEY,
    floorplan_id UUID REFERENCES gold.canonical_floorplans(floorplan_id),
    parent_optimization_id UUID, -- for optimization chains
    created_at TIMESTAMP,
    optimizer_version VARCHAR(50),
    action JSONB, -- {"action": "add_room", "room_type": "bedroom", ...}
    optimized_json JSONB,
    metadata JSONB
);

CREATE INDEX idx_optimized_floorplan ON gold.optimized_floorplans(floorplan_id);
CREATE INDEX idx_optimized_parent ON gold.optimized_floorplans(parent_optimization_id);
```

### 3.2 Event Store (ML Training Data - Optional)

```sql
CREATE TABLE events.recognition_events (
    event_id UUID PRIMARY KEY,
    event_type VARCHAR(50), -- 'recognition_started', 'recognition_completed', etc.
    user_id UUID,
    recognition_id UUID,
    timestamp TIMESTAMP,
    payload JSONB
);

CREATE TABLE events.optimization_events (
    event_id UUID PRIMARY KEY,
    event_type VARCHAR(50), -- 'optimization_requested', 'optimization_completed'
    user_id UUID,
    optimization_id UUID,
    timestamp TIMESTAMP,
    action JSONB,
    result JSONB
);

-- Partitioned by month for efficient querying
CREATE INDEX idx_events_timestamp ON events.recognition_events(timestamp);
CREATE INDEX idx_events_user ON events.recognition_events(user_id);
```
---

## 4. Pipeline Orchestration (Airflow Setup)

We use an event-driven architecture supported by Apache Airflow to coordinate the workflow of the pipeline.

### Run with Apache Airflow (part 2 - task 4)
1. Find the DAG file for the workflow definition in `airflow/dags/floorplan_orchestration.py`
2. Configure PYTHONPATH to ensure Airflow can import modules from the project:
```
export PYTHONPATH=<path-to>/floorplan-data-pipeline
```

3. Set AIRFLOW_HOME
```
export AIRFLOW_HOME=<path-to>/floorplan-data-pipeline/airflow
```
4. Start Airflow locally by running the following command line. Airflow will auto-generate default login credentials (username and password) in `airflow/logs/simple_auth_manager_passwords.json.generated`. You can find the directory in your terminal.
```
airflow standalone
```

5. Open the Airflow UI by visiting http://localhost:8080

7. In the Airflow UI, search for `rasterscan_floorplan_pipeline` to locate Your DAG

The orchestration for this project is defined within the `floorplan-data-pipeline` Airflow setup. Once Airflow is configured and running, you will be able to trigger, monitor, and debug the pipeline directly through the Airflow UI.


## 5. Versioning & Reproducibility

**Immutable Storage:**
- Bronze layer: Never modified
- Silver layer: Append-only
- Gold layer: Versioned (SCD Type 2)

**Lineage Tracking:**
```sql
-- Full lineage query
SELECT 
    r.recognition_id,
    r.recognizer_version,
    c.cleaned_id,
    c.cleaner_version,
    f.floorplan_id,
    f.version AS floorplan_version,
    o.optimization_id,
    o.optimizer_version
FROM bronze.raw_recognitions r
JOIN silver.cleaned_floorplans c ON r.recognition_id = c.recognition_id
JOIN gold.canonical_floorplans f ON c.cleaned_id = f.cleaned_id
LEFT JOIN gold.optimized_floorplans o ON f.floorplan_id = o.floorplan_id
WHERE r.upload_id = ?;
```
---
**End of Document**