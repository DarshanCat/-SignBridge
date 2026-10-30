"""Dataset provenance record. Every dataset directory must carry a dataset_info.json.

Required keys: name, language ("ISL"), license, source_url. Anything other than ISL is rejected so
that ASL (or other sign language) labels can never be trained as ISL by accident.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from training.data import DatasetError

INFO_FILE = "dataset_info.json"
REQUIRED_KEYS = ("name", "language", "license", "source_url")


@dataclass(frozen=True)
class DatasetInfo:
    name: str
    language: str
    license: str
    source_url: str
    consent_required: bool = False


def read_dataset_info(directory: Path) -> DatasetInfo:
    path = directory / INFO_FILE
    if not path.is_file():
        raise DatasetError(f"{INFO_FILE} not found in {directory}. Record the dataset name, language, license and source.")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DatasetError(f"{INFO_FILE} is not valid JSON: {exc}") from exc
    missing = [k for k in REQUIRED_KEYS if not str(raw.get(k, "")).strip()]
    if missing:
        raise DatasetError(f"{INFO_FILE} is missing values for: {missing}")
    if str(raw["language"]).strip().upper() != "ISL":
        raise DatasetError(
            f"Dataset language is {raw['language']!r}; only Indian Sign Language (ISL) data may be used. "
            "ASL and other sign-language labels are not ISL."
        )
    return DatasetInfo(
        raw["name"], "ISL", raw["license"], raw["source_url"], bool(raw.get("consent_required", False))
    )
