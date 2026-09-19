import os
from pathlib import Path

CUAD_JSON_NAME = "CUADv1.json"
ENV_DATASET_ZIP = "CUAD_DATASET_ZIP"


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_logs_dir() -> Path:
    return get_project_root() / "data" / "logs"


def get_dataset_zip_path() -> Path:
    raw_value = os.environ.get(ENV_DATASET_ZIP, "").strip()
    if not raw_value:
        raise ValueError(
            "CUAD dataset zip not configured. Set the CUAD_DATASET_ZIP environment "
            "variable to the full path of data.zip (must contain CUADv1.json)."
        )
    dataset_path = Path(raw_value).expanduser()
    if not dataset_path.is_file():
        raise ValueError(
            f"CUAD dataset zip not found at '{dataset_path}'. "
            f"Set {ENV_DATASET_ZIP} to a valid data.zip path."
        )
    return dataset_path


def is_dataset_configured() -> bool:
    try:
        get_dataset_zip_path()
        return True
    except ValueError:
        return False


def get_dataset_configuration_help() -> str:
    return (
        "Contract Review requires the CUAD_DATASET_ZIP environment variable pointing to "
        "your local data.zip file (must contain CUADv1.json). "
        "PowerShell example: $env:CUAD_DATASET_ZIP=\"C:\\path\\to\\data.zip\""
    )
