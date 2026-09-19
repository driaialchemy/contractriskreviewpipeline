import os
from pathlib import Path

import pytest

from src.config import ENV_DATASET_ZIP, get_dataset_zip_path


def test_dataset_path_missing_env_raises_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_DATASET_ZIP, raising=False)
    with pytest.raises(ValueError, match="CUAD dataset zip not configured"):
        get_dataset_zip_path()


def test_dataset_path_invalid_file_raises_clear_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing.zip"
    monkeypatch.setenv(ENV_DATASET_ZIP, str(missing))
    with pytest.raises(ValueError, match="CUAD dataset zip not found"):
        get_dataset_zip_path()


def test_dataset_path_resolves_from_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    dataset_zip = tmp_path / "data.zip"
    dataset_zip.write_bytes(b"PK\x05\x06" + b"\x00" * 16)
    monkeypatch.setenv(ENV_DATASET_ZIP, str(dataset_zip))
    assert get_dataset_zip_path() == dataset_zip


def test_dataset_path_expands_user_home(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    dataset_zip = tmp_path / "data.zip"
    dataset_zip.write_bytes(b"PK\x05\x06" + b"\x00" * 16)
    monkeypatch.setenv(ENV_DATASET_ZIP, str(dataset_zip))
    resolved = get_dataset_zip_path()
    assert resolved.is_file()
