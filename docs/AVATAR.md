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

## Anime avatar (VRM), 2026-11-04

The avatar loader now tries three models in order: `frontend/public/avatar/signer.vrm` (anime, VRM 1.0 or 0.x, via `@pixiv/three-vrm` 3.5.5, pinned), then the Mixamo `signer.glb`, then the built-in procedural figure. A model that is missing, is not a VRM or lacks the humanoid bones is skipped and the reason is written to the browser console. The label under the avatar names the model in use.

What is the same as before, so no clip, retarget or evaluation result changed: the clips (`frontend/public/animations/*.json`), the sequence player, the idle layer (breathing, weight shift, relaxed hands) and the pose smoothing are shared by all three models.

- **Bone mapping** (`frontend/src/lib/avatar/vrmRig.ts`): the 20 clip bones (torso, arms, three joints per finger) map to the VRM 1.0 humanoid bones (`Spine2` to `chest`, `LeftArm` to `leftUpperArm`, thumb to `Metacarpal`, `Proximal`, `Distal`, little finger for the pinky, and so on). The rig drives the VRM's normalized humanoid, and `vrm.update()` copies the pose to the real skeleton.
- **Rest pose** is derived from the loaded model, not assumed: the arms-down pose is measured from the arm, forearm, hand and finger base positions (the same function as for the Mixamo model, `armsDownFromBones`).
- **Forward kinematics tests** (`vrmRig.test.ts`): the Mixamo checks (arms down at rest, thumbs outward, arm raise and lift directions for both sides, elbow bend, finger curl split over three joints, torso and head) run against a synthetic VRM T-pose skeleton always, and against the real `signer.vrm` when it is present.
- **Materials**: the VRM's own MToon materials are used. The outline is softened (about 1.8 times the model's width, coloured from the base colour instead of black) and the scene gets anime style lighting (soft key, pink fill, cool rim, high ambient) with tone mapping switched off while a VRM is shown.
- **Camera**: the anime avatar is framed from the waist up so that the face and both hands fill the stage.

### Face (rule-based approximations, not validated)

The face of the VRM is driven by rules and is **not taken from signer-validated data** and not tracked from a person (`frontend/src/lib/avatar/face.ts`):

- Natural blinking: a blink every 2.6 to 6 s (seeded random), about a quarter of a second long, with an occasional quick double blink.
- A neutral expression while signing; only the markers below change it.
- Non-manual markers, on top of the existing head movements (`nmm.ts`): yes-no questions raise the brows and widen the eyes with the VRM `surprised` preset at 0.4, negation frowns with the `sad` preset at 0.45, both eased in and out with the same envelope as the head movement. A VRM has no eyebrow preset, so these whole-face presets are the closest available; each weight is kept small. Wh-questions keep only the head tilt. There is no lip sync and no mouth shapes for signs.

### Model and licence

The development model is the sample `VRM1_Constraint_Twist_Sample.vrm` of pixiv Inc. (from `github.com/pixiv/three-vrm`, 10,776,032 bytes). Its own metadata states author pixiv Inc., licence URL `https://vrm.dev/licenses/1.0/`, redistribution and modification allowed, credit notation unnecessary. Like the Mixamo model it is kept out of git (`frontend/public/avatar/` is ignored); replace the file with any VRM to change the character. This is a stand-in character, not a signer, and no clip is signer reviewed.

## Sign clarity on the VRM avatar, 2026-11-04

The signing motion is now retargeted at run time from the source landmarks of each clip, onto the avatar's own body. The recognition model, its data and every evaluation result are untouched, and no clip's motion tracks changed (the clips only gained an optional `landmarks` block, written by `backend/retarget/add_source_landmarks.py` from the INCLUDE feature files; clips without it play as before). No clip is signer reviewed.

- **Measurement first** (`frontend/src/lib/avatar/retargetMeasure.test.ts`, report in `docs/avatar_retarget/MEASUREMENT.md`): forward kinematics on the real `signer.vrm` for 10 clips against the source landmarks, per joint, before (the clips' own tracks) and after.
- **Source correction**: stored features are normalized by picture width and height, and INCLUDE is 16:9, so vertical distances are 16/9 too long; the retarget corrects them (`sourceLandmarks.ts`). Hand points are re-anchored at the pose wrist because the hand model's depth is relative to its own wrist.
- **Retarget** (`retarget.ts`, `anatomy.ts`): hand positions are mapped relative to the avatar's own shoulders and face (the avatar's mouth is read from its mouth morph), two bone IK with an anatomical elbow, forearm and wrist twist from the palm orientation, finger directions and thumb opposition per joint, and a head sphere and torso ellipse collision.
- **Player** (`player.ts`, `peak.ts`, `solverSampler.ts`): less smoothing inside a sign (time constant 0.025 s) than between signs (0.07 s), a hold of 0.28 s of clip time at the slowest moment of the stroke (a repeat of the pose the clip already has, nothing invented), and a default speed of 0.75x with the speed control kept (0.5, 0.75, 1, 1.5).
- **Visibility**: the camera eases to a hands and upper body framing while signing (it stops once the viewer orbits), a soft light rides on each hand, and the hands have a warm outline.
- **Source skeleton toggle** ("Show source skeleton" in English to Sign and in the conversation): draws the source landmarks of the playing sign, on the avatar's clock, next to the avatar.
- `?legacy-retarget` in the URL plays the clips' own tracks, for comparison.
- Frame sheets, source skeleton against avatar, before and after, for five signs: `docs/screenshots/avatar_retarget/`.
