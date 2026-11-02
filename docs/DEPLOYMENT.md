# Deployment guide: Vercel (web) and Hugging Face Spaces (API)

Nothing here has been deployed. Everything below is prepared and checked locally; you run the steps. The backend container was built and tested on this machine (section 9). The Vercel build was not run on Vercel.

SignBridge is a research prototype built on the INCLUDE dataset. A public deployment must stay non-commercial and must keep the footer notices (attribution, CC BY-NC-SA 4.0 non-commercial, clips not signer-reviewed, research prototype). They are in `frontend/src/components/Footer.tsx` and cannot be switched off by an environment variable.

## 1. Architecture and what goes where

| Part | Host | What it holds | Where the secrets are |
|---|---|---|---|
| Web app (Next.js) | Vercel | the pages, MediaPipe files (copied from `node_modules` at build), avatar model and clips (fetched at build, section 5) | `HF_TOKEN` for the build only |
| API (FastAPI, PyTorch CPU, spaCy) | Hugging Face Space, Docker | the code; weights and clips are downloaded at start | `HF_TOKEN` as a Space secret |
| Weights, clips, avatar | a PRIVATE Hugging Face dataset repository | `models/`, `animations/`, `avatar/` | a read-only token |

The browser talks to both: HTTPS to Vercel for the page and HTTPS plus a secure WebSocket (`wss://`) to the Space for recognition. Video never leaves the browser; only landmarks are sent.

Things that must not go into the public git repository (already ignored): `data/`, `backend/models/`, `frontend/public/animations/*.json`, `frontend/public/avatar/`.

## 2. Licence and asset decisions you have to make first

1. **INCLUDE-derived material** (the model weights and the clips) may be shared only non-commercially under CC BY-NC-SA 4.0 with attribution (`DATA_NOTICE.md`). A public demo is allowed under that condition: do not put ads, payments or a commercial offer on it. Vercel's free Hobby plan is for non-commercial use too, which fits.
2. **Anything the browser loads is public.** The clips and the avatar GLB are downloaded by every visitor, so "private storage" only keeps them out of git, not out of reach of a visitor. This is why the clips fall under point 1.
3. **Mixamo terms are unconfirmed** for the avatar GLB (`docs/AVATAR_ASSET_AUDIT.md`). Until you have confirmed them, deploy WITHOUT `avatar/signer.glb`: leave it out of the assets repository and the app uses its built-in procedural figure automatically. Add the GLB later only after confirming that embedding the character in a public web app is allowed.

## 3. Accounts

- Hugging Face (https://huggingface.co/join). Create an access token later in section 4.
- Vercel (https://vercel.com/signup), signed in with GitHub so it can see the repository.
- GitHub: the repository has to be pushed by you (`git push`); this session did not push. Keep it public or private as you wish; the assets are not in it.

Installed on your PC: Git, Docker Desktop (only for the local container test), Node 22 and Python 3.11 (already used by the project), and the Hugging Face CLI:

```powershell
pip install -U huggingface_hub
```

## 4. Private assets repository on Hugging Face

1. Create the repository in the web page https://huggingface.co/new-dataset: name `signbridge-assets`, visibility **Private**. Your repository id is `YOUR_NAME/signbridge-assets`.
2. Log in on your PC (paste a token with write access when asked; newer CLI versions use `hf auth login`, older ones `huggingface-cli login`):

```powershell
hf auth login
```

3. Upload the files from the project root. Check `hf upload --help` if your CLI version words it differently.

```powershell
cd "C:\Users\Darshan\Downloads\MONEY Bank\3d project"
hf upload YOUR_NAME/signbridge-assets backend/models/isl_model.pt models/isl_model.pt --repo-type dataset
hf upload YOUR_NAME/signbridge-assets backend/models/labels.json models/labels.json --repo-type dataset
hf upload YOUR_NAME/signbridge-assets backend/models/threshold.json models/threshold.json --repo-type dataset
hf upload YOUR_NAME/signbridge-assets frontend/public/animations animations --repo-type dataset
```

Do not upload `metrics.json` (2 MB, not needed) and, until point 3 of section 2 is settled, not `avatar/signer.glb` either. The layout in the repository must be exactly `models/*`, `animations/*.json`, and optionally `avatar/signer.glb`.

4. Create a **read-only** token for the deployments: https://huggingface.co/settings/tokens, New token, type Fine-grained, give it only "Read access to contents of selected repos" on `YOUR_NAME/signbridge-assets`. Copy it; it is shown once. Call it `HF_TOKEN` below.

## 5. Backend on Hugging Face Spaces

1. Create the Space at https://huggingface.co/new-space: name `signbridge-api`, SDK **Docker** (blank template), hardware **CPU basic (free)**, visibility Public (the web app has to reach it; the weights are not in it). The API URL will be `https://YOUR_NAME-signbridge-api.hf.space`.
2. Assemble the Space folder from the repository (no weights, no data are copied):

```powershell
cd "C:\Users\Darshan\Downloads\MONEY Bank\3d project"
.\scripts\make_space.ps1
```

   The result is `build\hf-space` (it is git-ignored): `Dockerfile`, `README.md` (with the Space settings: Docker, port 7860, and the licence notice), `entrypoint.sh`, `fetch_assets.py`, `requirements.txt`, and the folders `app`, `nlp`, `retarget`, `config`.

3. Set the Space settings first (Space page, Settings, Variables and secrets), then push, so the first start already has them:

| Name | Kind | Value |
|---|---|---|
| `HF_TOKEN` | Secret | the read-only token from section 4 |
| `SIGNBRIDGE_ASSETS_REPO` | Variable | `YOUR_NAME/signbridge-assets` |
| `SIGNBRIDGE_CORS_ORIGINS` | Variable | `["https://YOUR-APP.vercel.app"]` (JSON list; the exact Vercel production domain, no trailing slash; fill in after section 6 and restart the Space) |
| `SIGNBRIDGE_CORS_ORIGIN_REGEX` | Variable, optional | `https://YOUR-APP-.*\.vercel\.app` to also allow Vercel preview deployments |

   Already set inside the image: `SIGNBRIDGE_RECORDING_ENABLED=false` (the recorder endpoints answer 403 and nothing is written), `SIGNBRIDGE_WS_CHECK_ORIGIN=true` (the WebSocket only accepts the origins above, as CORS cannot protect a WebSocket), port 7860, CPU PyTorch, no MediaPipe or OpenCV.

4. Push the folder to the Space repository (use your username and the write token as the password when git asks):

```powershell
cd "C:\Users\Darshan\Downloads\MONEY Bank"
git clone https://huggingface.co/spaces/YOUR_NAME/signbridge-api space-signbridge-api
Copy-Item "3d project\build\hf-space\*" space-signbridge-api -Recurse -Force
cd space-signbridge-api
git add .
git commit -m "SignBridge API"
git push
```

   The Space builds (about 5 to 10 minutes the first time: CPU PyTorch is the large download). Watch the Logs tab. A healthy start prints the downloaded model files and clip count, `Recognition model state at startup: loaded (Model loaded with 262 sign class(es).)`, and `Application startup complete`.

5. Check it from your PC:

```powershell
curl https://YOUR_NAME-signbridge-api.hf.space/api/health
curl https://YOUR_NAME-signbridge-api.hf.space/api/model/status
```

   The second must say `loaded`, 262 classes. The free CPU Space goes to sleep after a period without visitors and wakes on the next request (about a minute, longer after a rebuild); the first visitor waits.

## 6. Frontend on Vercel

1. Vercel, Add New, Project, import the GitHub repository.
2. **Root Directory: `frontend`**. Framework: Next.js (detected). The build command and install command come from `frontend/vercel.json` (`npm ci`; `node scripts/fetch-assets.mjs && npm run build`). Node 22.
3. Environment variables (Project Settings, Environment Variables, tick Production and Preview):

| Name | Value | Notes |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `https://YOUR_NAME-signbridge-api.hf.space` | baked into the browser bundle; no trailing slash |
| `NEXT_PUBLIC_WS_URL` | leave unset | the WebSocket URL is derived as `wss://YOUR_NAME-signbridge-api.hf.space/ws/predict`; set it only if the WebSocket lives elsewhere (full URL including `/ws/predict`) |
| `NEXT_PUBLIC_DISABLE_RECORDING` | `1` | hides the Record sign tab |
| `SIGNBRIDGE_ASSETS_REPO` | `YOUR_NAME/signbridge-assets` | build time only |
| `HF_TOKEN` | the read-only token | build time only; do NOT name it `NEXT_PUBLIC_...`, that would publish it |

4. Deploy. The build log must show `fetch-assets: 262 clips ... written to public/`. If it says `skipping`, the two build-only variables are missing and the English to Sign tab will have nothing to sign. If the GLB is not in the assets repository the avatar is the built-in figure, which is expected until Mixamo is settled.
5. Copy the production domain (for example `https://signbridge-xyz.vercel.app`) into the Space variable `SIGNBRIDGE_CORS_ORIGINS` (section 5, step 3) and restart the Space (Settings, Factory reboot or Restart).

Changing a `NEXT_PUBLIC_` value needs a redeploy of the web app, not just a restart.

## 7. Smoke test of the public site

1. Open the Vercel URL. The footer shows the four notices. The tab list has no Record sign.
2. The status panel shows backend connected, 262 sign classes, 262 clips.
3. English to Sign: type "Where is the hospital", the avatar signs the available glosses and names the ones without a clip.
4. Sign to English or Conversation, Start camera: the camera panel shows the actual resolution (1280 x 720 if the camera has it) and the dashed framing guide. Sign one word; the answer appears or says UNRECOGNIZED. The browser console must show no CORS or WebSocket errors.
5. From a page on another origin, a WebSocket to the Space must be refused (HTTP 403); this is the origin check.

## 8. Operating notes

- **Updating the model or clips:** upload the new files to the assets repository (section 4), restart the Space (it downloads at start) and redeploy Vercel (it downloads at build).
- **Cost:** HF free CPU basic and the Vercel Hobby plan are free. Free Spaces have no uptime guarantee.
- **Privacy:** the API stores nothing; landmark frames are processed and dropped. The site loads no analytics. Vercel and Hugging Face keep their own request logs.
- **Abuse:** there is no rate limit and no login. The origin check stops other websites from using the API in a browser, not a script. If you need more, put a rate limiter in front (for example Cloudflare) before sharing the link widely.
- **Token safety:** the token in Vercel and in the Space is read-only for one repository. If it leaks, revoke it at https://huggingface.co/settings/tokens and create a new one.
- **Recognition caveat to tell users:** recognition is trained on INCLUDE (262 signs, authors' predefined split, signer independence not verified) and on a webcam it is less reliable than on the dataset (`docs/evaluation/BROWSER_PATH.md`). The 50 grammar words cannot be recognized yet.

## 9. What was tested locally

On this machine, with Docker Desktop:

```powershell
cd "C:\Users\Darshan\Downloads\MONEY Bank\3d project"
.\scripts\make_space.ps1
docker build -t signbridge-space-test build\hf-space
docker run -d --name signbridge-space-test -p 7860:7860 `
  -e 'SIGNBRIDGE_CORS_ORIGINS=["https://signbridge-test.vercel.app"]' `
  -v "${PWD}\backend\models:/home/user/app/models:ro" `
  -v "${PWD}\frontend\public\animations:/home/user/app/animations:ro" signbridge-space-test
```

Results: the image is about 1.6 GB on disk (CPU PyTorch 0.6 GB, spaCy 0.1 GB; it is smaller when pulled, because layers are compressed); the container serves `/api/health`; with the allowed origin the CORS header is returned and with a foreign origin it is not; `/ws/predict` accepted a connection from the allowed origin, announced 262 classes, threshold 0.7, and classified browser landmarks of a test video correctly (Technology, 0.994); a foreign origin got HTTP 403 on the WebSocket; `/api/record/plan` answered 403 (recorder off). The test container was removed afterwards. Not tested: the download step against a real private Hugging Face repository (`fetch_assets.py`, `frontend/scripts/fetch-assets.mjs`; both were only run with the repository variable unset), the Hugging Face build itself, and Vercel.

## 10. Variable reference

| Variable | Where | Meaning | Default |
|---|---|---|---|
| `SIGNBRIDGE_CORS_ORIGINS` | API | JSON list of allowed web origins | localhost:3000 |
| `SIGNBRIDGE_CORS_ORIGIN_REGEX` | API | one regular expression for more origins (preview deployments) | none |
| `SIGNBRIDGE_WS_CHECK_ORIGIN` | API | refuse WebSocket connections from other origins | false (true in the Space image) |
| `SIGNBRIDGE_RECORDING_ENABLED` | API | recorder endpoints on or off | true (false in the Space image) |
| `SIGNBRIDGE_ASSETS_REPO`, `SIGNBRIDGE_ASSETS_TYPE`, `HF_TOKEN` | API start, Vercel build | where to download weights, clips and avatar from; type is `dataset` or `model` | unset: skip |
| `SIGNBRIDGE_MODEL_DIR`, `SIGNBRIDGE_ANIMATION_DIR` | API | where the files are read | set in the image |
| `NEXT_PUBLIC_API_URL` | web build | API base URL | http://127.0.0.1:8000 |
| `NEXT_PUBLIC_WS_URL` | web build | full WebSocket URL, if not derived from the API URL | derived |
| `NEXT_PUBLIC_DISABLE_RECORDING` | web build | `1` hides the Record sign tab | recorder shown |
| `NEXT_PUBLIC_MEDIAPIPE_DELEGATE` | web build | `gpu` to use the GPU delegate | CPU |

## 11. Troubleshooting

- **Browser says the backend is unreachable:** the Space is asleep or building, or `NEXT_PUBLIC_API_URL` is wrong (redeploy after changing it), or the Vercel domain is missing from `SIGNBRIDGE_CORS_ORIGINS`.
- **Live recognition never connects but the page loads:** the WebSocket origin is not in `SIGNBRIDGE_CORS_ORIGINS` (check the Space log for the 403), or a corporate proxy blocks `wss://`.
- **Space log says `fetch_assets: download failed`:** wrong repository id, the token cannot read that repository, or the repository is a model repository (set `SIGNBRIDGE_ASSETS_TYPE=model`).
- **Status panel says model not trained:** the three model files are not in `models/` of the assets repository.
- **English to Sign says no clip for every word:** `fetch-assets` was skipped during the Vercel build.
- **Camera does not start on the public site:** the page must be HTTPS (Vercel is) and the browser permission must be allowed for the site.
