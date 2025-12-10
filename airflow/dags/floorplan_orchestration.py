from datetime import datetime
from pathlib import Path
import sys

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

from src.rasterscan.helper import project_src_rasterscan_path

DEFAULT_ARGS = {
    'owner': 'floorplan-team',
    'depends_on_past': False,
}


def run_recognizer(**context):
    """
    Task 1 : run recognizer (RasterScan implementation)
    """
    rasterscan_path = project_src_rasterscan_path()
    sys.path.insert(0, str(rasterscan_path))

    from src.rasterscan.recognizer import FloorplanRecognizer
    from src.rasterscan.helper import save_json

    project_root = Path(__file__).resolve().parents[1]
    outputs_dir = project_root / 'outputs' / 'rasterscan'
    outputs_dir.mkdir(parents=True, exist_ok=True)

    # Determine image path from dag_run conf or default
    dag_run = context.get('dag_run')
    image_path = None
    if dag_run and getattr(dag_run, 'conf', None):
        image_path = dag_run.conf.get('image_path')
    if not image_path:
        image_path = str(project_root / 'floorplan-images' / 'floorplan_raw.png')

    output_raw = outputs_dir / 'recognizer_raw.json'

    # If recognizer output already exists, skip recognition and return path
    if output_raw.exists():
        # load/verify minimal content could be added here if desired
        print(f"recognizer_raw.json already exists at {output_raw}; skipping recognition")
        return str(output_raw)

    # Run recognizer and save output
    recognizer = FloorplanRecognizer(method='rasterscan')
    raw = recognizer.recognize_from_image(image_path, str(output_raw))

    # Ensure file saved (recognizer may already save but we save defensively)
    save_json(raw, str(output_raw))

    return str(output_raw)


def run_cleaner(**context):
    """
    Task 2: load raw JSON and clean it with FloorplanCleaner
    """
    rasterscan_path = project_src_rasterscan_path()
    sys.path.insert(0, str(rasterscan_path))

    from src.rasterscan.helper import load_json, save_json
    from src.rasterscan.cleaner import FloorplanCleaner

    project_root = Path(__file__).resolve().parents[1]
    outputs_dir = project_root / 'outputs' / 'rasterscan'
    outputs_dir.mkdir(parents=True, exist_ok=True)

    # Get raw path either from XCom or default
    ti = context['ti']
    raw_path = ti.xcom_pull(task_ids='recognize_floorplan') or str(outputs_dir / 'recognizer_raw.json')

    raw = load_json(raw_path)
    cleaner = FloorplanCleaner(snap_threshold=5.0)
    cleaned = cleaner.clean(raw)

    cleaned_path = outputs_dir / 'cleaned_canonical.json'
    save_json(cleaned.to_dict(), str(cleaned_path))

    return str(cleaned_path)


def run_optimizer(**context):
    """Task: apply optimizer to cleaned floorplan."""
    rasterscan_path = project_src_rasterscan_path()
    sys.path.insert(0, str(rasterscan_path))

    from src.rasterscan.helper import load_json, save_json
    from src.rasterscan.optimizer import FloorplanOptimizer
    from src.rasterscan.canonical_schema import Floorplan as CSFloorplan
    # Note: optimizer implementations are expected to operate on Floorplan dataclass

    project_root = Path(__file__).resolve().parents[1]
    outputs_dir = project_root / 'outputs' / 'rasterscan'
    outputs_dir.mkdir(parents=True, exist_ok=True)

    ti = context['ti']
    cleaned_path = ti.xcom_pull(task_ids='clean_floorplan') or str(outputs_dir / 'cleaned_canonical.json')

    cleaned_json = load_json(cleaned_path)

    # If cleaner produced a dataclass object instead of JSON, adapt accordingly.
    # Here we expect cleaned_json to be a dict matching the schema; the optimizer
    # implementation may include helpers to convert dict->dataclass. If not,
    # some implementations accept dict input directly.

    optimizer = FloorplanOptimizer()

    # The rasterscan optimizer expects a dataclass Floorplan; try to import helper conversion
    try:
        from src.rasterscan.helper import dict_to_floorplan
        cleaned_fp = dict_to_floorplan(cleaned_json)
    except Exception:
        # Fallback: pass dict directly if optimizer accepts it
        cleaned_fp = cleaned_json

    # Apply optimizations
    optimized = optimizer.split_bedroom(cleaned_fp) if hasattr(optimizer, 'split_bedroom') else cleaned_fp
    if hasattr(optimizer, 'add_new_room'):
        optimized = optimizer.add_new_room(optimized)

    optimized_path = outputs_dir / 'optimized.json'

    # If optimized has to_dict method, use it
    if hasattr(optimized, 'to_dict'):
        save_json(optimized.to_dict(), str(optimized_path))
    else:
        save_json(optimized, str(optimized_path))

    return str(optimized_path)


# DAG definition
with DAG(
    dag_id='rasterscan_floorplan_pipeline',
    start_date=datetime(2025, 12, 1),
    schedule=None,
    default_args=DEFAULT_ARGS,
    catchup=False,
    tags=['floorplan', 'rasterscan'],
) as dag:

    recognize_task = PythonOperator(
        task_id='recognize_floorplan',
        python_callable=run_recognizer,

    )

    clean_task = PythonOperator(
        task_id='clean_floorplan',
        python_callable=run_cleaner,
    )

    optimize_task = PythonOperator(
        task_id='optimize_floorplan',
        python_callable=run_optimizer,
    )

    recognize_task >> clean_task >> optimize_task
