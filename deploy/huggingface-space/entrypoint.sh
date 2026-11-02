#!/bin/sh
# Download weights and clips (if configured), then serve on the port Spaces expects.
set -e
python fetch_assets.py
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-7860}" --proxy-headers --forwarded-allow-ips="*"
