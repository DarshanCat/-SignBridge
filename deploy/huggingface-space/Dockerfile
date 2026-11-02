# SignBridge API for Hugging Face Spaces (Docker SDK). Assembled by scripts/make_space.ps1; the Space repository root is this folder's content.
# CPU PyTorch only, no MediaPipe or OpenCV (they are for training, not for serving). Weights and clips are NOT in the image: entrypoint.sh
# downloads them from a private Hugging Face repository at start (SIGNBRIDGE_ASSETS_REPO + the HF_TOKEN secret).
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1

# Spaces run the container as user 1000
RUN useradd --create-home --uid 1000 user
WORKDIR /home/user/app

COPY requirements.txt ./
ARG TORCH_VERSION=2.13.0
RUN pip install -r requirements.txt \
 && pip install "torch==${TORCH_VERSION}" --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple \
 && rm -rf /usr/local/lib/python3.11/site-packages/torch/include /usr/local/lib/python3.11/site-packages/torch/test \
 && python -c "import spacy; spacy.load('en_core_web_sm')"

COPY --chown=user:user app ./app
COPY --chown=user:user nlp ./nlp
COPY --chown=user:user retarget ./retarget
COPY --chown=user:user config ./config
COPY --chown=user:user fetch_assets.py entrypoint.sh ./
RUN mkdir -p models animations && chown user:user models animations && sed -i "s/\r$//" entrypoint.sh && chmod +x entrypoint.sh
USER user

ENV SIGNBRIDGE_MODEL_DIR=/home/user/app/models \
    SIGNBRIDGE_ANIMATION_DIR=/home/user/app/animations \
    SIGNBRIDGE_RECORDING_ENABLED=false \
    SIGNBRIDGE_WS_CHECK_ORIGIN=true \
    SIGNBRIDGE_RECORD_DIR=/tmp/signbridge-recorded

EXPOSE 7860
CMD ["./entrypoint.sh"]
