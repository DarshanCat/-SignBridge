# Demo guide

What can honestly be shown today, what cannot, and how to run it. Updated 2026-10-29.

## Start

```powershell
.\scripts\dev.ps1 -ApiPort 8010 -WebPort 3011     # or default ports 8000 and 3000 if free
```

Open the frontend URL; backend docs are at `<backend>/docs`.

## Can be demonstrated (verified in this repository)

1. **Status panel**: backend connected, webcam detected, landmark extraction not loaded until the camera starts, "Model not
   trained", animation unavailable. The panel is derived from real checks.
2. **English to gloss**: type "Hello, what is your name?" on the English to Sign tab. Shows the original sentence, the gloss
   `HELLO YOU NAME WHAT`, unsupported words (for example `quantum`), and coverage. Say clearly that the vocabulary is a
   13-gloss placeholder and the ordering rules are unvalidated.
3. **Honest degradation**: every gloss is flagged "(unsupported: no animation)", the avatar says nothing can be played, the
   vocabulary panel shows 0 verified signs.
4. **Avatar and playback infrastructure**: the "Run rig self-test" link plays a generic arm motion to show the skeleton, the
   player, play/pause/replay/stop/restart and speed. State plainly that this is **not a sign**.
5. **Webcam capture** (needs a real camera and a Chromium browser; not yet verified on this project): Start camera, landmark
   overlay, counters, "Validate landmarks on server". Do a dry run first.
6. **Failure handling**: stop the backend and show "Backend unreachable"; deny camera permission and show the message.

## Cannot be demonstrated (do not imply otherwise)

- Recognition of any sign: no dataset, no trained model; the Recognize button is disabled with an explanation.
- Any ISL sign performed by the avatar: no clips; no sign has been reviewed by an ISL signer.
- Full sentence translation, continuous signing, non-manual features.
- Any accuracy or latency claim for the full system.

## Suggested script (5 minutes)

1. Architecture in one slide (`docs/PROJECT_REPORT.md` section 5).
2. Live: English to gloss with a supported and an unsupported word.
3. Live: show that the avatar refuses to sign without a clip, then the rig self-test labelled as not a sign.
4. Live: camera and landmark overlay (if the dry run worked).
5. State what is missing: dataset, model, reviewed clips, and the plan (`docs/PROJECT_STATUS.md`).

## If a clip set exists in the future

Put clips in `frontend/public/animations` and register them in `backend/config/sign_registry.json` (see
`docs/AVATAR_ASSET_AUDIT.md`). The UI separates "clip not signer-reviewed" from verified signs; demonstrate only verified
ones as correct ISL.
