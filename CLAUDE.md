# SignBridge AI Context

SignBridge is an end-to-end bidirectional Indian Sign Language (ISL) and English communication platform.

## Architecture
- **Frontend**: Next.js 16, React 19, TypeScript, Tailwind CSS, React Three Fiber (R3F) for 3D avatar rendering, and MediaPipe Holistic for landmark tracking.
- **Backend**: FastAPI, PyTorch BiGRU sequential landmark classifier, and rule-based ISL ⇄ English translation services.
- **Data & Models**: MediaPipe 75 landmarks (Pose + Left Hand + Right Hand).
