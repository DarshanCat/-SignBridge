# ISL-CSLTR continuous sentence test: protocol (written before any video was fetched)

Written 2026-11-07, before the first video of the corpus was downloaded or any model output on it was seen. Authors' predefined split, signer independence not verified: this is a different dataset from INCLUDE, so it is not a split of it, and nothing about signer overlap between the two is known (neither publishes signer IDs).

## What is already known (read from the zip's directory and its annotation files, 3.4 MB transferred in total, not the 2.9 MB of the directory alone and not under the 1 MB I first estimated)

- 22,073 entries in the zip: 687 sentence videos (7.62 GB; median 13.3 MB; 492 camera files `.MP4`, 195 small `.mp4`), 19,899 frames, 483 `Thumbs.db`, one gloss CSV, three spreadsheets, one text file.
- The CSV `ISL Corpus sign glosses.csv` gives, for 101 sentences, **a sign gloss sequence written by the corpus authors** (for example `what are you doing` as `WHAT YOU DO`). These glosses are the dataset's own reference. No signer of this project has checked them; their spelling is not normalized (`DONOT`, `CONGRATULATIIONS`), and they use a different gloss convention from ours in places.
- The text file counts 7 signers (2 native signers of a school for the deaf and 5 student volunteers; my earlier "6" was a misreading of the page). No signer ID is attached to any video.
- Only 23 of the 170 distinct corpus glosses are classes of our model (BAD, BEAUTIFUL, BED, COLD, FRIEND, GOOD, HAPPY, HE, I, IT, LIGHT, MEAN, MEDICINE, NICE, OLD, SCHOOL, SHE, SHIRT, TIME, TODAY, TRAIN, WE, YOU), 30.9 percent of the 362 gloss tokens. 27 more are words of our gloss dictionary that have no recognizer class (GO, WHAT, ... ). Only 2 sentences, `you are bad` and `you are good`, consist only of classes of the model. The recognizer therefore cannot be right about most of what is signed: this test measures domain shift and open vocabulary behaviour, not sentence translation.

## Model and settings (fixed, nothing is tuned on this data)

The live model in `backend/models` (1D CNN, 262 classes, trained on the authors' predefined split of INCLUDE v2), its validation-chosen confidence threshold from `backend/models/threshold.json` (0.7), the live segmenter with its default `SegmenterConfig`, and the same preprocessing as training (Python MediaPipe Holistic, every second frame, `normalize_frame`). Not changed after seeing any result. Because nothing is chosen on this data, there is no validation part: the whole subset is one evaluation, and it is one test use of the live model that goes on the disclosure list.

## Which videos (rule fixed now)

Sentences with at least one corpus gloss that is a class of the model (79 of 101 sentences). For each, the first three videos of its folder in alphabetical order of file name. The folder `which collegeschool are you from` is matched to the sentence `which college school are you from` by ignoring spaces. This gives 232 videos, 2.68 GB, read one at a time out of the zip with byte range requests; each video is deleted after its landmarks are extracted. Only the landmark `.npy` files stay, under `data/processed/isl_cslrt` (git-ignored). A video with fewer than 8 usable frames is reported as failed, never replaced.

## What is measured (fixed now)

Corpus glosses are first normalized only by removing commas and full stops and joining neighbouring tokens that form a class gloss with a hyphen (`THANK YOU` becomes `THANK-YOU`). The recognizer's output for a video is the list of segments it finds, each with an answer (a label at or above the threshold) or UNRECOGNIZED.

1. **Segmentation:** segments found per video against the number of corpus gloss tokens of its sentence: share of videos within one of it, and the Spearman correlation. No gloss timing exists, so only the count can be checked.
2. **Recall of covered signs:** over all videos, the share of the covered gloss tokens (corpus glosses that are classes of the model) that appear among the answered labels of the video (multiset, order ignored).
3. **Answer rate:** share of segments that are answered (not UNRECOGNIZED).
4. **Answer precision against the corpus glosses:** among answered segments, the share whose label is one of the glosses of its sentence; the rest are reported as wrong answers (this is the open vocabulary error: signs the model does not know are answered with some class). Reported separately for the large camera files and the small files.
5. **Whole sentence:** for the two fully covered sentences only, whether the answered sequence equals the corpus gloss sequence. Two sentences are an anecdote, not a score.

Not measured: translation quality, gloss word error rate over uncovered signs (it would be 1.0 by construction), anything about signers. A result here says nothing about accuracy on INCLUDE or about unseen signers in general.

## Also computed, no video needed

The project's English to gloss against the corpus authors' glosses with `nlp.score_generation` (Phase 3 tool), using the CSV as the reference. The glosses are the corpus authors', not a signer's of this project, and the conventions differ; the scores describe agreement with that convention.
