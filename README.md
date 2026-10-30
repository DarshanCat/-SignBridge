<div align="center">

  <img src="assets/hero-banner.svg" alt="SignBridge Banner" width="100%" />

  <br/><br/>

  <!-- Dynamic Typing SVG -->
  <a href="https://github.com/DarshanCat/-SignBridge">
    <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=20&duration=3000&pause=1200&color=6366F1&center=true&vCenter=true&multiline=false&width=750&height=45&lines=%E2%9A%A1+Bidirectional+Indian+Sign+Language+(ISL)+%E2%87%84+English;%F0%9F%96%90%EF%B8%8F+Real-time+MediaPipe+Holistic+75-Point+Landmark+Extraction;%F0%9F%A7%A0+PyTorch+BiGRU+Deep+Temporal+Neural+Recognition;%F0%9F%8E%AD+Real-time+3D+Avatar+Skeletal+Rig+Playback+(Three.js+%2F+R3F);%F0%9F%8C%90+Empowering+Accessible+Communication+Everywhere" alt="Animated Typing Subtitle" />
  </a>

  <br/>

  <!-- Badges -->
  <p align="center">
    <a href="https://github.com/DarshanCat/-SignBridge/blob/main/LICENSE">
      <img src="https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge&logo=opensourceinitiative&logoColor=white" alt="MIT License" />
    </a>
    <img src="https://img.shields.io/badge/Next.js-16-black?style=for-the-badge&logo=nextdotjs&logoColor=white" alt="Next.js 16" />
    <img src="https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React 19" />
    <img src="https://img.shields.io/badge/Three.js-R3F-black?style=for-the-badge&logo=threedotjs&logoColor=white" alt="Three.js" />
    <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
    <img src="https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white" alt="PyTorch" />
    <img src="https://img.shields.io/badge/MediaPipe-0075FF?style=for-the-badge&logo=google&logoColor=white" alt="MediaPipe" />
    <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  </p>

  <p align="center">
    <a href="#-key-features">Key Features</a> •
    <a href="#-system-architecture">Architecture</a> •
    <a href="#-quick-start">Quick Start</a> •
    <a href="#-project-layout">Project Layout</a> •
    <a href="#-dataset--training-pipeline">Dataset & Training</a> •
    <a href="#-research-documentation">Research Docs</a>
  </p>

  <img src="assets/features-banner.svg" alt="SignBridge Key Capabilities" width="100%" />

</div>

---

## 📖 Overview

**SignBridge** is an advanced academic and engineering prototype for **bidirectional Indian Sign Language (ISL) and English** communication. It couples computer vision landmark tracking, recurrent deep learning networks, natural language processing, and modern WebGL 3D avatar rendering into an accessible, end-to-end web system.

> [!NOTE]
> **ISL is a distinct language with its own grammar, spatial morphology, and Subject-Object-Verb (SOV) sentence order.** It is not American Sign Language (ASL) and cannot be accurately represented by verbatim word-for-word substitution. SignBridge is built from the ground up with dedicated ISL grammar rules and gloss mappings.

---

## ⚡ System Architecture

<div align="center">
  <img src="assets/pipeline.svg" alt="Bidirectional Pipeline Flow" width="100%" />
</div>

The platform operates across two complementary bidirectional pathways:

### 1. Sign ➔ English Recognition
1. **Webcam Feed & Landmark Tracking**: Live video frames are processed client-side via **MediaPipe Holistic**, extracting 75 normalized landmark coordinates (pose + left hand + right hand) at up to 30 FPS.
2. **Temporal BiGRU Inference**: Sequence features are streamed to a FastAPI backend powered by a bidirectional Gated Recurrent Unit (**BiGRU**) in PyTorch.
3. **Gloss & Translation Mapping**: Recognized ISL gloss sequences are resolved to grammatical English sentences through vocabulary rules.

### 2. English ➔ Sign 3D Avatar Synthesis
1. **Rule-Based Gloss Translation**: English text input undergoes lemmatization, stop-word reduction, and SOV grammar transformation.
2. **Sign Registry Lookup**: Target gloss tokens are retrieved from the sign registry, pointing to keyframed skeletal animation sequences.
3. **3D Avatar Player**: Rendered inside **Three.js / React Three Fiber**, applying real-time skeletal quaternion and bone transformations to articulate signs smoothly.

---

## 📊 Current System State

SignBridge’s software engineering foundation is complete, verified, and audited:

| Component | Status | Details |
| :--- | :---: | :--- |
| **Frontend UI (Next.js 16 + React 19)** | 🟢 Verified | Full modern responsive dashboard with status telemetry, webcam panel, and 3D viewer. |
| **Backend API (FastAPI + Pydantic v2)** | 🟢 Verified | Health probes, landmark validation, inference endpoints, and translation routes. |
| **MediaPipe Holistic Tracking** | 🟢 Complete | Client-side 75-landmark extraction pipeline with unit test suite. |
| **Deep Learning Pipeline (BiGRU)** | 🟢 Ready | Complete PyTorch architecture, training loop, evaluation metrics, and manifest tools. |
| **3D Avatar Rigging & Player** | 🟢 Ready | React Three Fiber bone hierarchy, keyframe interpolator, and fallback idle motion. |
| **Model Weights & Video Datasets** | 🟡 Training Ready | Git-clean repository; datasets and model weights are ready to be trained using bundled scripts. |

See [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) and [docs/PROJECT_COMPLETION_AUDIT.md](docs/PROJECT_COMPLETION_AUDIT.md) for complete audit checklists.

---

## 🚀 Quick Start

### Prerequisites
- **Node.js** 20+ and `npm`
- **Python** 3.11 (`py -3.11` or `python3.11`)
- **Git**

### Automated Setup (Windows PowerShell)

```powershell
# 1. Clone repository
git clone https://github.com/DarshanCat/-SignBridge.git
cd -SignBridge

# 2. Run automated environment setup
.\scripts\setup.ps1
```

This automated script creates `backend/.venv`, installs dependencies (`requirements.txt`, `requirements-dev.txt`, `requirements-ml.txt` with PyTorch CPU, MediaPipe, OpenCV), and installs frontend npm packages.

### Run Development Servers

```powershell
# Start both Backend (:8000) and Frontend (:3000) concurrently
.\scripts\dev.ps1

# Custom ports if 8000 or 3000 are in use:
.\scripts\dev.ps1 -ApiPort 8010 -WebPort 3011
```

- **Frontend App**: [http://localhost:3000](http://localhost:3000)
- **Backend API Docs (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **OpenAPI JSON**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 🧪 Testing & Verification

Run the unified test suite across both frontend and backend:

```powershell
.\scripts\test.ps1
```

This runs:
1. `pytest` unit & integration tests on FastAPI backend.
2. `npm run type-check` for TypeScript strictness.
3. `npm run lint` for ESLint quality rules.
4. `npm test` for avatar rig and landmark transformation tests.
5. `npm run build` production bundle verification.

---

## 🐳 Docker Deployment

Run the complete multi-container stack with a single command:

```powershell
docker compose up --build
```

Container architecture:
- `backend`: FastAPI Uvicorn service on port `8000`
- `frontend`: Next.js production server on port `3000`

---

## 📁 Project Layout

```
.
├── 📂 assets/              # Animated SVGs, banners, and diagrams for documentation
├── 📂 frontend/            # Next.js 16, React 19, TypeScript, Tailwind CSS, React Three Fiber
│   ├── src/app/            # App router pages, layouts, and global styles
│   ├── src/components/     # WebcamPanel, EnglishToSignPanel, StatusPanel, AvatarViewer
│   ├── src/lib/avatar/     # Skeletal rigging, bones definition, keyframe clip player
│   └── public/animations/  # Sign animation keyframe JSON files
├── 📂 backend/             # FastAPI asynchronous microservice
│   ├── app/api/            # REST API endpoints & route handlers
│   ├── app/recognition/    # Landmark normalization & PyTorch BiGRU model
│   ├── app/translation/    # English ⇄ ISL grammar & gloss translation engine
│   ├── app/avatar/         # Sign registry and clip loading services
│   ├── training/           # Preprocessing, validation, manifest builder, training loop
│   └── tests/              # Pytest test suite (100% passing)
├── 📂 data/                # Dataset directory (raw video and processed landmark numpy arrays)
├── 📂 docs/                # Comprehensive academic & engineering documentation
│   ├── ARCHITECTURE.md     # System architecture & component specifications
│   ├── DATASET_GUIDE.md    # ISL datasets, capture protocol, and ethical guidelines
│   ├── MODEL_TRAINING.md   # BiGRU hyperparameter tuning and training procedures
│   ├── AVATAR.md           # 3D avatar bone structure and animation keyframe format
│   ├── IEEE_PAPER_CHECKLIST.md  # Research paper guidelines & publication checklist
│   └── PROJECT_REPORT.md   # Complete technical report
└── 📂 scripts/             # PowerShell automation (setup.ps1, dev.ps1, test.ps1)
```

---

## 🧠 Dataset & Training Pipeline

When ready to train the BiGRU neural model with an ISL video dataset:

```powershell
cd backend

# 1. Preprocess raw video dataset into normalized landmark sequences
.\.venv\Scripts\python -m training.preprocess_videos --index ..\data\raw\<dataset>\index.csv --out ..\data\processed\<dataset>

# 2. Validate extracted landmark dataset integrity
.\.venv\Scripts\python -m training.validate_dataset --dir ..\data\processed\<dataset>

# 3. Train BiGRU sequence classifier
.\.venv\Scripts\python -m training.train --manifest ..\data\processed\<dataset>\manifest.csv --out models
```

For guidelines on acquiring ISL datasets, IRB consent, and annotations, consult [docs/DATASET_GUIDE.md](docs/DATASET_GUIDE.md).

---

## ⏱️ Latency Benchmarking

SignBridge includes a latency measurement harness to profile network roundtrips, inference execution, and UI rendering:

```powershell
cd backend
.\.venv\Scripts\python -m benchmarks.measure --api http://localhost:8000 --out ..\docs\benchmarks\latest.json
```

Results are saved in JSON format for academic reporting. Details in [docs/EXPERIMENT_PLAN.md](docs/EXPERIMENT_PLAN.md).

---

## 📚 Detailed Documentation

| Document | Description |
| :--- | :--- |
| 📘 [ARCHITECTURE.md](docs/ARCHITECTURE.md) | In-depth system design, data flow diagrams, and tech stack details |
| 📗 [DATASET_GUIDE.md](docs/DATASET_GUIDE.md) | ISL candidate datasets, ethics, licensing, and consent protocols |
| 📕 [MODEL_TRAINING.md](docs/MODEL_TRAINING.md) | BiGRU model architecture, hyperparameters, and validation |
| 📙 [AVATAR.md](docs/AVATAR.md) | Skeletal rig bone hierarchy, quaternion rotation, and clip schema |
| 📓 [PROJECT_REPORT.md](docs/PROJECT_REPORT.md) | Academic project report draft and experimental design |
| 📋 [IEEE_PAPER_CHECKLIST.md](docs/IEEE_PAPER_CHECKLIST.md) | Research checklist for academic conference / journal publication |

---

## 👥 Authors & Acknowledgments

- **Darshan BG** ([@DarshanCat](https://github.com/DarshanCat)) - *Creator & Lead Developer*
- Powered by Google **MediaPipe**, **PyTorch**, and the **Three.js** community.

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

<div align="center">
  <sub>Built with ❤️ for accessible, barrier-free communication.</sub>
</div>
