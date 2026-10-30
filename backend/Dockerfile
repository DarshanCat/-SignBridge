# SignBridge API. Build from the repository root:  docker build -f backend/Dockerfile -t signbridge-api .
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv/backend

COPY backend/requirements.txt ./requirements.txt
# CPU-only PyTorch (the API loads the recognition model); version pinned to requirements-ml.txt
ARG TORCH_VERSION=2.13.0
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir "torch==${TORCH_VERSION}" --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple

COPY backend/app ./app
COPY backend/config ./config
RUN useradd --create-home --uid 10001 signbridge && mkdir -p /srv/backend/models /srv/animations && chown -R signbridge /srv
USER signbridge

# Provide trained weights and sign clips by mounting volumes (see docs/DEPLOYMENT_READINESS.md)
ENV SIGNBRIDGE_MODEL_DIR=/srv/backend/models SIGNBRIDGE_ANIMATION_DIR=/srv/animations
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
