# Avatar route: Mixamo rig with clips retargeted from INCLUDE landmarks (chosen 2026-10-30)

## What you need to do (I cannot: Mixamo needs an Adobe login)

1. Sign in to mixamo.com with a free Adobe ID. In the Characters tab pick a humanoid (for example "Y Bot" or "X Bot"; a plain bot avoids
   face and clothing licence questions). Download with format FBX binary, pose T-pose, and with skin. No animation is needed.
2. Mixamo exports FBX, not GLB. Convert it to GLB with Blender (import the FBX, export glTF 2.0 as .glb with the armature included) or with a
   command line FBX to glTF converter. Check that the finger bones survive (three joints per finger, names like `mixamorig:LeftHandIndex1`;
   Blender may rename the colon to an underscore, which is fine).
3. Put the file at `frontend/public/avatar/signer.glb` and add `frontend/public/avatar/SOURCE.md` with the download page URL, the date, the exact
   terms text you relied on, and the Adobe account name (never the password). I did not verify Mixamo's current terms. Read them yourself,
   especially the limits on redistributing the raw model, and do not publish the GLB in a public repository unless the terms allow it.
4. Tell me when it is there. I will not create accounts, log in or download from Mixamo.

Ready Player Me is the other named option. It exports GLB directly, but its terms and any developer account requirements are unchecked; Mixamo
is the safer default.

## What I already built (works without the asset)

`backend/retarget/` turns a landmark sequence into a SignBridge clip: shoulder and elbow direction, forearm direction, hand orientation
(wrist to middle knuckle and index to pinky knuckle) and one curl angle per finger, then smoothing, hand dropout handling (hold briefly, then relax
to rest) and a 0.25 s ramp from and to the rest pose. 16 unit tests check it with forward kinematics under the same three.js Euler convention
the avatar uses, including a left and right mirror test. A small command line tool reads one feature file and writes one clip JSON.

Visual check on the existing procedural avatar: the first INCLUDE "Hello" training sample, retargeted and played, raised the signer's right
forearm and hand to head height with a clip length of 2.9 s. That confirms the geometry and conventions work end to end. It does **not** show that
the motion is a correct ISL "Hello", and the temporary test clip was removed afterwards (`frontend/public/animations` is empty again).

## What I will do when the GLB arrives

1. A GLB avatar component (React Three Fiber) with a bone map from Mixamo names to the 20 SignBridge bones, skeleton validation, the T-pose
   to arms-down rest conversion computed from the loaded skeleton (not assumed), and finger curl spread over the three Mixamo joints.
2. Check it by playing the retargeted Hello clip on the real rig and by tests on the bone map.
3. Retarget a first small vocabulary from INCLUDE samples (sign choices and sample selection to be agreed with you), register each clip as
   `clip_unreviewed` with its provenance.

## Known limits of retargeting from landmarks

- Roll of the upper arm and forearm is not recovered, and finger spread and thumb opposition are not modelled.
- Landmark depth (z) is noisy, so arm and hand directions toward the camera are the least reliable.
- No head, torso or facial motion; facial expression for negation and questions has to be authored separately.
- Frame rate is assumed (30 fps source, every second frame), not read from the videos.
- One sample is not a sign model: choosing a representative sample, or averaging several, needs a decision and a signer's judgement.
- INCLUDE signers are not identified and the licence conflict is unresolved, so retargeted clips are derivative works to keep private for now.
- No clip counts as a verified sign until a visual check and an ISL signer review are recorded in the sign registry.

## Update 2026-10-30: Mixamo avatar integrated

`frontend/public/avatar/signer.glb` (1,794,604 bytes, 1.79 MB) was converted from your `T-Pose.fbx` by `tools/avatar/convert_fbx.py` (Blender 5.2.3 LTS,
skin on, animation off). `tools/avatar/verify_glb.py` parses the file (no string search): 68 nodes, 1 skin, 65 skeleton joints, 2 meshes, 2 materials, no images, no animations.
Both hands have the wrist (Hand), and Thumb, Index, Middle, Ring and Pinky each with joints 1, 2 and 3 plus a fingertip end bone (4). Mixamo names are kept
(`mixamorig:` prefix). The armature node carries a 90 degree X rotation and a 0.01 scale, which the loader handles.

Rest pose: derived from the loaded skeleton, not assumed (`frontend/src/lib/avatar/mixamo.ts`). The arm direction and palm normal are measured from the T-pose bones; each
arm is turned down and rolled so the palm faces forward, which is the canonical rest the clips assume. With no clip the avatar stands with arms down. Finger curl from a clip
is split over the three joints (index to pinky 40, 40 and 20 percent; thumb 30, 40 and 30 percent). Face expression and head tilt are not driven (the Y Bot has no face).

Checks run: 6 tests parse the real GLB with three.js and check forward kinematics (rest arms down, thumbs outward, forward raise, outward lift, elbow bend, finger curl split),
and a browser run played the retargeted Hello sample on it: right hand raised to head height. Every clip is marked `not_signer_reviewed` in its JSON and in the UI.
If the GLB is missing or lacks a required bone, the viewer falls back to the procedural humanoid. The model is git-ignored and excluded from the Docker image until the terms are confirmed.
