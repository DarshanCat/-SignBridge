"""Download the trained model files and the avatar clips from a private Hugging Face repository into models/ and animations/.

SIGNBRIDGE_ASSETS_REPO   repository id, for example your-name/signbridge-assets (unset: skip, the API then reports model_not_trained)
SIGNBRIDGE_ASSETS_TYPE   dataset (default) or model
HF_TOKEN                 read token (a Space secret); never printed
Only the files the API needs are fetched: models/isl_model.pt, models/labels.json, models/threshold.json and animations/*.json.
"""
import os
import sys
from pathlib import Path

repo = os.environ.get("SIGNBRIDGE_ASSETS_REPO", "").strip()
if not repo:
    print("fetch_assets: SIGNBRIDGE_ASSETS_REPO is not set, starting without model and clips", flush=True)
    sys.exit(0)

from huggingface_hub import snapshot_download  # noqa: E402

root = Path(__file__).resolve().parent
try:
    snapshot_download(
        repo_id=repo,
        repo_type=os.environ.get("SIGNBRIDGE_ASSETS_TYPE", "dataset"),
        token=os.environ.get("HF_TOKEN") or None,
        allow_patterns=["models/isl_model.pt", "models/labels.json", "models/threshold.json", "animations/*.json"],
        local_dir=str(root),
    )
except Exception as exc:  # noqa: BLE001 - report the type only, never a message that could contain a token
    print(f"fetch_assets: download failed ({type(exc).__name__}); check the repository id and the HF_TOKEN secret", flush=True)
    sys.exit(1)
print("fetch_assets: model files:", sorted(p.name for p in (root / "models").glob("*")), "clips:", len(list((root / "animations").glob("*.json"))), flush=True)
