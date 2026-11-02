# Continuous signing: sign segmentation results

Authors' predefined split, signer independence not verified. Rule used: tune on validation, report test once.

## Method

`/ws/predict` accepts a stream of landmark frames (`{"type":"frames"}`) in chunks. The segmenter (`backend/app/recognition/segmenter.py`) works on the
normalized features: a frame is "engaged" when a wrist is above the rest line (2.0 shoulder widths below the shoulder midpoint; resting hands sit at
about 2.8) and the wrists moved in the last 10 frames. A sign opens after 2 engaged frames and closes after 6 rest frames (hands down, or raised but
still for 10 frames). The segment keeps 5 frames before and 4 after, because training samples start and end with the hands down. Segments with fewer
than 6 engaged frames are dropped as noise. Each segment goes through the same classifier and threshold (0.7) as the isolated mode; accepted signs
are added to the sentence, UNRECOGNIZED ones are not. `undo` removes the last sign, `reset` clears everything, `flush` closes an open sign.

## Test design

Streams join 3 to 5 real INCLUDE samples of different classes (80 streams per row, fixed seed). Between two samples `gap` extra rest frames are
inserted (a copy of the last frame of the earlier sample, still, hands down, 0.003 noise); the INCLUDE samples already carry a short rest margin. The
rest frames are synthetic; real people may pause differently. Ground truth is the span of each sample. The tuning on validation covered `rest_y`
(1.4 to 2.4), `end_frames` (3 to 6), the padding, `still_frames` and `still_speed`; only `rest_y` (1.6 to 2.0) and the padding mattered. The test split
was run once with the final settings.

## Results (signs: correctly split / recognized correctly / accepted but wrong / UNRECOGNIZED)

| Split | Rest frames between signs | Real signs | Split correctly | Recognized correctly | Accepted but wrong | UNRECOGNIZED | Whole sentence right |
|---|---|---|---|---|---|---|---|
| validation | 0 (natural margins only) | 313 | 203 (64.9%) | 161 (51.4%) | 10 (3.2%) | 32 (10.2%) | 34 of 80 |
| validation | 10 | 313 | 308 (98.4%) | 250 (79.9%) | 13 (4.2%) | 45 (14.4%) | 36 of 80 |
| validation | 20 | 313 | 310 (99.0%) | 252 (80.5%) | 13 (4.2%) | 45 (14.4%) | 36 of 80 |
| test | 0 (natural margins only) | 322 | 242 (75.2%) | 188 (58.4%) | 20 (6.2%) | 34 (10.6%) | 28 of 80 |
| test | 10 | 322 | 316 (98.1%) | 247 (76.7%) | 22 (6.8%) | 47 (14.6%) | 28 of 80 |
| test | 20 | 322 | 320 (99.4%) | 248 (77.0%) | 23 (7.1%) | 49 (15.2%) | 28 of 80 |

With 10 or more rest frames the segmenter finds nearly every sign (98 to 99 percent split correctly, no missed sign, 4 or fewer merged or fragmented
on test). With only the natural margins (a few frames of rest) 24 to 33 percent of the signs are merged with a neighbour or fragmented: signs signed
back to back without a pause cannot be separated by this method.

For comparison, the isolated mode on whole test samples (from the single test evaluation in `results.md`) accepts 86.8 percent at the live threshold with
95.5 percent of those correct, which is about 82.8 percent right, 3.9 percent wrong and 13.2 percent unrecognized. Segmentation costs about 6 points of
"recognized correctly" (77.0 versus 82.8) and nearly doubles the wrong accepted signs (7.1 versus 3.9 percent), because the cut segment is not exactly
the span the model was trained on.

Whole sentences are exactly right in 28 of 80 test streams (35 percent): with 3 to 5 signs per stream and about 77 percent per sign this is what the per
sign numbers imply.

Raw numbers: `segmentation_val.json`, `segmentation_test.json` in this folder. Reproduce: `python -m training.eval_segmentation --manifest ..\data\processed\include_v2\manifest.csv --split val`.

## Not covered

Real webcam streams (the browser landmark extraction was not compared with Python on a real take; see the Landmark check tab), signers who never lower or
pause their hands, and false segments from non-signing movement (the streams contain no such movement).
