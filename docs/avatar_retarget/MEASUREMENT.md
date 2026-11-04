# Retarget measurement: avatar against the source landmarks

Real `signer.vrm` (shoulder width 0.217 m, mouth read from the model's own mouth morph) and 10 real clips (hello, thank-you, good, doctor, hospital, market, yesterday, book, bank, teacher), every source frame of every clip, both hands where the source has them (n = 467 hand frames). Forward kinematics of the pose each method produces, applied to the avatar's skeleton, against the source landmarks of the same frame. Authors' predefined split is not involved (no model is evaluated); the recognition model and its results were not touched.

Methods: **legacy** = the clips' own rotation tracks (what the avatar played before). **new** = the retargeter of this change (aspect correction, depth from bone length, face anchored mapping, IK with an elbow hinge, collision, full palm orientation, per joint finger and thumb directions). **plain** and **no collision** are the new retargeter with parts switched off, to show where the change comes from.

Units: position error in shoulder widths of each body measured from the shoulder midpoint (so arm length and proportions count); direction error in degrees between a bone of the avatar and the same segment of the source. The **picture plane (2D)** error ignores depth: the depth of the source is its least reliable number, so the 2D error is the one to trust; the 3D error is given for completeness and is worse for the new retargeter by construction (it replaces the noisy source depth by one that respects bone lengths).

## Position error per joint (shoulder widths, mean and 90th percentile)

| Joint | legacy 2D | new 2D | legacy 2D p90 | new 2D p90 | legacy 3D | new 3D |
|---|---|---|---|---|---|---|
| elbow | 0.13 | 0.07 | 0.22 | 0.13 | 0.40 | 0.39 |
| wrist | 0.23 | 0.00 | 0.33 | 0.00 | 0.77 | 0.84 |
| thumb.CMC | 0.22 | 0.05 | 0.32 | 0.08 | 0.78 | 0.85 |
| thumb.MCP | 0.26 | 0.06 | 0.38 | 0.08 | 0.84 | 0.85 |
| thumb.IP | 0.28 | 0.09 | 0.40 | 0.12 | 0.87 | 0.86 |
| thumb.tip | 0.32 | 0.14 | 0.44 | 0.19 | 0.92 | 0.88 |
| index.MCP | 0.28 | 0.06 | 0.40 | 0.09 | 0.81 | 0.86 |
| index.PIP | 0.30 | 0.09 | 0.42 | 0.13 | 0.84 | 0.86 |
| index.DIP | 0.32 | 0.11 | 0.46 | 0.16 | 0.87 | 0.86 |
| index.tip | 0.35 | 0.14 | 0.50 | 0.20 | 0.90 | 0.86 |
| middle.tip | 0.36 | 0.16 | 0.52 | 0.23 | 0.90 | 0.87 |
| ring.tip | 0.35 | 0.15 | 0.50 | 0.21 | 0.89 | 0.86 |
| pinky.tip | 0.35 | 0.16 | 0.51 | 0.22 | 0.88 | 0.85 |

## Direction error per bone (degrees, mean and 90th percentile)

| Bone | legacy | new | legacy p90 | new p90 |
|---|---|---|---|---|
| upperArm | 12.36 | 12.13 | 16.55 | 28.29 |
| foreArm | 12.28 | 16.68 | 15.51 | 27.88 |
| hand | 11.31 | 0.01 | 20.68 | 0.00 |
| thumb.CMC-MCP | 24.50 | 0.00 | 40.00 | 0.00 |
| thumb.MCP-IP | 41.54 | 0.00 | 56.73 | 0.00 |
| index.MCP-PIP | 28.34 | 3.56 | 55.79 | 6.62 |
| index.PIP-DIP | 35.76 | 15.71 | 73.01 | 39.71 |
| middle.MCP-PIP | 28.18 | 4.12 | 56.82 | 10.29 |
| middle.PIP-DIP | 36.22 | 17.63 | 69.00 | 39.09 |
| ring.MCP-PIP | 28.69 | 4.22 | 60.63 | 10.63 |
| ring.PIP-DIP | 36.25 | 16.86 | 70.60 | 38.82 |
| pinky.MCP-PIP | 28.77 | 3.83 | 60.14 | 9.81 |
| pinky.PIP-DIP | 36.17 | 16.43 | 64.19 | 36.91 |

The forearm direction is measured against the raw source depth and is the one bone where the new number is higher: see the note on depth above (2D wrist error 0.23 to 0.004 shoulder widths).

## Hands near the face: wrist and index tip relative to the mouth (shoulder widths, difference of the vectors from the mouth)

| | legacy | new |
|---|---|---|
| wrist (n = 4) | 0.23 | 0.17 |
| indexTip (n = 4) | 0.30 | 0.20 |

## Hands inside the body (share of hand frames in which the wrist, the palm or a fingertip is inside the head or torso)

| Method | any | head | torso |
|---|---|---|---|
| legacy | 0.0 % | 0.0 % | 0.0 % |
| solver_plain | 27.0 % | 0.0 % | 27.0 % |
| solver_no_collision | 36.6 % | 0.6 % | 36.0 % |
| solver | 0.9 % | 0.6 % | 0.2 % |

## Where the improvement comes from

| Method | wrist 2D | index tip 2D | index knuckle direction | hand direction | inside the body |
|---|---|---|---|---|---|
| legacy | 0.23 | 0.35 | 28.34 | 11.31 | 0.0 % |
| solver_plain | 0.06 | 0.17 | 3.55 | 0.33 | 27.0 % |
| solver_no_collision | 0.00 | 0.14 | 3.56 | 0.00 | 36.6 % |
| solver | 0.00 | 0.14 | 3.56 | 0.01 | 0.9 % |
