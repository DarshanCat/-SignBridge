# 3D avatar (Phase 6)

**Status: the avatar, clip format, registry and playback controls work. There are zero sign animations, so the
avatar cannot sign anything yet.** The only motion it can perform is a labelled rig self-test that is not a sign.

## What exists

- **Avatar:** a procedural humanoid built from primitive shapes (`frontend/src/lib/avatar/rig.ts`, rendered by
  `components/avatar/Humanoid.tsx` with React Three Fiber). It is original geometry, so there is no third-party
  asset or license. It has 20 animatable bones: spine, chest, neck, head, and per side upper arm, forearm, hand and
  five single-joint fingers. It has no face, so facial and non-manual ISL grammar cannot be shown.
- **Clip format:** one JSON file per gloss, `frontend/public/animations/<gloss>.json` (filename stem = gloss, any case),
  keyframed Euler XYZ rotations in radians relative to the rest pose. A clip must declare `source.author`,
  `source.license` and `source.description`. Schema and validation: `backend/app/avatar/clip.py` (Pydantic) and
  `frontend/src/lib/avatar/clip.ts` (kept in sync by a test that compares the bone lists). Negative x on an arm bone
  raises it forward. Clips should start and end at the rest pose; no blending is done between signs.
- **Registry:** `GET /api/avatar/animations` lists only valid clips and reports invalid files in `invalid`.
  `POST /api/avatar/plan` marks each gloss as available or missing. `GET /api/translation/vocabulary` shows which
  vocabulary glosses have clips.
- **Playback:** `SequencePlayer` plays clips back to back with play, pause, replay current sign, restart all and a
  0.5x/1x/1.5x speed control. Signs without a clip are skipped and listed as "(no animation)"; if nothing is
  playable the UI says so. Camera orbit and zoom are keyboard-independent mouse/touch controls (OrbitControls).
- **Failure handling:** an error boundary and a WebGL check show a text fallback if the 3D scene cannot render. A clip
  that fails to download or validate is reported by gloss and skipped.
- **Rig self-test:** a button runs a generic arm raise, wave and finger curl to prove the pipeline works. It is
  labelled "not a sign" on screen and is never listed in the registry.

## What is missing

- **Real sign clips.** Producing correct ISL signs needs a Deaf ISL signer or linguist and a capture or authoring
  workflow (for example motion capture retargeted to this rig, or hand-authored keyframes checked with signers).
  No clip in this repository has been validated by ISL signers, and none should be presented as a correct sign until
  that happens.
- A rigged GLB/GLTF humanoid with a verified license (preferred by the project brief) was not added: nothing was
  downloaded and no suitable asset was supplied. The procedural rig is the placeholder; replacing it means loading a
  GLB and mapping its bones to the 20 names above.
- Face, mouth shapes, body blending between signs, and finger joints beyond one per finger.

## Adding a clip

1. Create `frontend/public/animations/hello.json` (see `backend/tests/helpers.py` for the minimal shape).
2. Check it: `GET /api/avatar/animations` should list it, not report it as invalid.
3. Record who made it and its license in `source`; get it reviewed by an ISL signer before use.

## Phase 12 additions

Sign provenance and review status live in `backend/config/sign_registry.json`; see `AVATAR_ASSET_AUDIT.md` for the audit,
the add-a-sign workflow and the missing assets, and `DEMO_GUIDE.md` for what may be shown. The player now has `stop`, `reset`
and `dispose`, and blends 0.2 s between consecutive signs.
