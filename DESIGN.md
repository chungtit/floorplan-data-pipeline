# Floorplan Data Pipeline - Design Document

**Author:** Chung Luong  
**Date:** December 2025  
**Version:** 1.0

## Table of Contents
- [1. Pipeline Architecture](#1-pipeline-architecture)
  - [1.1 High-Level Overview](#11-high-level-overview)
  - [1.2 Pipeline Stages](#12-pipeline-stages)
    - [Stage 1: Recognition (Bronze Layer - Raw Ingestion)](#stage-1-recognition-bronze-layer---raw-ingestion)
    - [Stage 2: Cleaning & Post-Processing (Silver Layer - Filted, cleaned, or augmented)](#stage-2-cleaning--post-processing-silver-layer---filted-cleaned-or-augmented)
    - [Stage 3: Optimization (Gold Layer - Business-level aggregates)](#stage-3-optimization-gold-layer---business-level-aggregates)
- [2. Data Storage Model](#2-data-storage-model)
  - [2.1 Storage Layers (Medallion Architecture)](#21-storage-layers-medallion-architecture)
  - [2.2 Event Store (ML Training Data)](#22-event-store-ml-training-data---optional)
- [3. Pipeline Orchestration (Airflow Setup)](#3-pipeline-orchestration-airflow-setup)
- [4. Versioning & Reproducibility](#4-versioning--reproducibility)

---

## 1. Pipeline Architecture

### 1.1 High-Level Overview

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

### 1.2 Pipeline Stages

#### Stage 1: Recognition (Bronze Layer - Raw Ingestion)
- Input: raw floorplan images (PNG, JPG) or SVG files
- Process: 
  - ML-based recognition (Computer Vision models such as RasterScan) OR llm-based recognition (Gemini, openAI, Claude, etc)
  - Extract rooms, walls, doors, windows
- Output: Raw JSON with noisy geometric data
- Storage: `bronze.raw_recognitions` table (Assume that we have a database with 3 tables: bronze, silver, gold)

#### Stage 2: Cleaning & Post-Processing (Silver Layer - Filted, cleaned, or augmented)
- Input: The raw recognition JSON produced in Stage 1
- Process:
  - Snap vertices to grid, close polygon gaps, normalize wall thickness, validate topology
- Output: Cleaned JSON
- Storage: `silver.cleaned_floorplans` table

#### Stage 3: Optimization (Gold Layer - Business-level aggregates)
- Input: cleaned JSON produced in Stage 2
- Process:
  - Optimization (add/remove/resize rooms), constraint satisfaction, adjacency preservation
- Output: Optimized floorplan
- **Storage:** `gold.optimized_floorplans` table

---

## 2. Data Storage Model
Our data can be stored using either cloud-based or in-memory solutions. To provide clear guidance on structuring the data, SQL table definitions are provided below. They are designed to support both **short-term** and **long-term** use, allowing us to leverage historical data for training our models

### 2.1 Storage Layers 

#### Bronze Layer (Raw)
This layer stores the raw recognition results exactly as they are received, including any metadata and associated image references
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
This layer contains data that has been cleaned, post-processed, or otherwise processed from the raw Bronze layer. Each entry links back to its original recognition record and includes information on the cleaning process, validation status, and relevant metadata.

```sql
CREATE TABLE silver.cleaned_floorplans (
    cleaned_id UUID PRIMARY KEY,
    recognition_id UUID REFERENCES bronze.raw_recognitions(recognition_id),
    created_at TIMESTAMP,
    cleaner_version VARCHAR(50),
    cleaned_json JSONB,
    validation_passed BOOLEAN,
    cleaning_stats JSONB, 
    metadata JSONB
);

CREATE INDEX idx_cleaned_recognition ON silver.cleaned_floorplans(recognition_id);
```

#### Gold Layer (Optimized)
This layer stores the final, optimized floorplan data. Each record references its canonical floorplan and can optionally link to a parent optimization. The action field captures the specific changes applied during optimization, while optimized_json contains the resulting processed data
```sql
CREATE TABLE gold.optimized_floorplans (
    optimization_id UUID PRIMARY KEY,
    floorplan_id UUID REFERENCES gold.canonical_floorplans(floorplan_id),
    parent_optimization_id UUID, 
    created_at TIMESTAMP,
    optimizer_version VARCHAR(50),
    action JSONB, -- {"action": "add_room", "room_type": "bedroom", ...}
    optimized_json JSONB,
    metadata JSONB
);

CREATE INDEX idx_optimized_floorplan ON gold.optimized_floorplans(floorplan_id);
CREATE INDEX idx_optimized_parent ON gold.optimized_floorplans(parent_optimization_id);
```

### 2.2 Event Store (ML Training Data)
The following code was designed to captures all recognition and optimization actions, providing a detailed history for machine learning training and analytics. Each event includes the user, timestamp, and relevant payloads to reconstruct workflows or track performance

```sql
CREATE TABLE events.recognition_events (
    event_id UUID PRIMARY KEY,
    event_type VARCHAR(50),
    user_id UUID,
    recognition_id UUID,
    timestamp TIMESTAMP,
    payload JSONB
);

CREATE TABLE events.optimization_events (
    event_id UUID PRIMARY KEY,
    event_type VARCHAR(50),
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
We partition tables by month and add indexes on timestamp and user_id, allowing queries to scan only the relevant month and quickly locate the needed rows. This makes data retrieval much faster and ensures efficient access to historical events, which is valuable when preparing large datasets for training or fine-tuning machine learning models in the future

---

## 3. Pipeline Orchestration (Airflow Setup)

We use an event-driven architecture supported by Apache Airflow to coordinate the workflow of the pipeline. The following the steps to set up Airflow

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


## 4. Versioning & Reproducibility

**Immutable Storage:**
- Bronze layer: Never modified
- Silver layer: Append-only
- Gold layer: SCD Type 2 (to track the history of dimension table changes by creating a new record for each change, rather than overwriting the old one)

**Lineage Tracking:**
```sql
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