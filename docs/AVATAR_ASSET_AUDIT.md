# Avatar asset audit

Audit date: 2026-10-29. Method: inspection of the repository tree, `frontend/src/lib/avatar/*`,
`frontend/src/components/avatar/*`, `backend/app/avatar/*`, `backend/config/*.json`, and live API calls.

## Findings

| Question | Finding | Evidence |
|---|---|---|
| GLB/GLTF models in the repo | **None** | no `.glb`/`.gltf` under `frontend/` (excluding `node_modules`) |
| Avatar in use | Procedural humanoid built from primitive shapes (box, sphere, capsule) in code, 20 animatable bones | `rig.ts`, `Humanoid.tsx` |
| Skeleton and hand joints | Real `Group` hierarchy; one joint per finger (single curl joint), no finger segments, no face, no eyes/mouth | `rig.ts`; `validateRig` (tested) |
| Embedded animations | None. Motion comes only from JSON clips | `clip.ts`, `player.ts` |
| Animation clips present | **0** valid clips in `frontend/public/animations` | `GET /api/avatar/animations` returned `count: 0` |
| Provenance and license of avatar | Original geometry written for this project; no third-party asset, so no external license applies | source files |
| Provenance of clips | None exist. The clip format requires `source.author/license/description` and review flags are tracked in the sign registry | `clip.py`, `sign_registry.py` |
| Gloss vocabulary | 13 placeholder glosses (`backend/config/translation.json`); each has a registry record with status `no_clip` | `sign_registry.json`; `GET /api/avatar/registry` |
| Visual review done | Only for pipeline checks: a temporary generic arm-raise clip was played through the real UI to confirm clip loading, sequential playback, transition and controls, then deleted. **It was not an ISL sign and no sign was reviewed.** | Phase 12 browser check |

## Verdict

The avatar infrastructure is real (loading, validation, registry, playback with transitions, controls, status reporting).
**The sign content is missing**: zero verified signs, so English-to-ISL signing is not functional. A generic arm motion
must never be presented as an ISL sign.

## What is required to finish

1. **A signer-authored or signer-reviewed motion source** for every vocabulary sign: an ISL signer (preferably Deaf) and a
   capture route, for example (a) motion capture or video-based pose and hand tracking retargeted to this rig, or (b)
   hand-authored keyframes checked frame by frame with the signer. Hand shape, location, movement, orientation and
   non-manual markers all matter; the current rig cannot show non-manual markers.
2. **A rigged humanoid GLB with a verified license** (optional but preferred): required joints must exist under the names in
   `bones.json` (see `validateSkeletonNames`), with finger joints. Candidate sources and licenses need your selection;
   none was downloaded. Importing it needs a GLB loader component that maps clip poses onto the model's bones (not written,
   because it cannot be tested without an asset).
3. **A reviewed vocabulary**: replace the placeholder glosses, meanings and contexts in `translation.json` and
   `sign_registry.json` with reviewed entries, one per sign; do not assume one English word maps to one sign.
4. **Per-clip evidence** in `sign_registry.json`: `asset_id`, `reference_source`, `license`, `attribution`,
   `visually_reviewed`, `signer_reviewed`. The API computes `verified` only when the clip exists and is valid, all three
   provenance fields are present, and both review flags are true.

## Workflow for adding one sign

1. Obtain a reference recording or capture with permission and a license that allows this use.
2. Produce `frontend/public/animations/<asset_id>.json` (format in `AVATAR.md`; start and end at the rest pose).
3. Add or update the sign's record in `backend/config/sign_registry.json`.
4. Check `GET /api/avatar/registry`: status becomes `clip_unreviewed` with no `problems`.
5. Play it in the English to Sign tab; set `visually_reviewed` after you check hand shapes, orientation and timing.
6. Have an ISL signer review it; only then set `signer_reviewed` (status becomes `verified`).
