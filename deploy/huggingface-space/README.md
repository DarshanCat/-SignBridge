---
title: SignBridge API
emoji: 🤟
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
short_description: API for a research prototype, ISL and English
---

# SignBridge API (research prototype)

Backend of an academic prototype for Indian Sign Language (ISL) and English. It recognizes isolated signs from MediaPipe landmarks sent by the web app and converts English text to ISL gloss. It is not a complete natural-language ISL translator.

- Recognition model trained on the INCLUDE dataset (Sridhar et al., ACM MM 2020, https://zenodo.org/records/4010759). Results are on the authors' predefined split; signer independence is not verified.
- INCLUDE-derived material is shared non-commercially under CC BY-NC-SA 4.0 with attribution. Do not use this Space commercially.
- The avatar clips are automatic retargets from INCLUDE samples and are not signer reviewed.
- No video or image is sent to this API, only landmarks, and nothing is stored (the recorder is disabled here).

Endpoints: `/api/health`, `/docs`, WebSocket `/ws/predict`.
