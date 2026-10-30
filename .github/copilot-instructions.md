# SignBridge: ISL ⇄ English Translation AI System

SignBridge is an end-to-end bidirectional Indian Sign Language (ISL) and English communication platform.

## Architecture Guidelines
- **Frontend (`frontend/`)**: Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS, Three.js / React Three Fiber (`@react-three/fiber`), MediaPipe Holistic runtime.
- **Backend (`backend/`)**: FastAPI, Pydantic v2 schemas, PyTorch BiGRU sequential temporal model for landmark recognition, rule-based gloss translation engine.
- **3D Avatar**: Bone hierarchy and skeletal animation player in `frontend/src/lib/avatar/`.
- **Dataset & ML**: 75 Holistic landmarks (pose + hands), normalized coordinates.
