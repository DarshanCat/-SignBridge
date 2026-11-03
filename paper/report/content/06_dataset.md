# Dataset

## The INCLUDE dataset

INCLUDE is a word-level Indian Sign Language dataset published by Sridhar, Ganesan, Kumar and Khapra at ACM Multimedia 2020 [@sridhar2020include]. The authors' lists name 4,292 videos in 263 classes grouped by category, with a predefined split into training, validation and test. The data is distributed as zip archives on Zenodo (record 4010759). This project downloaded the archives with a resumable streaming tool, processed each archive exactly once, and audited the result.

## Processing and audit

Every video was converted into a sequence of 225 landmark values per frame (Section 6.4), taking every second frame. The audit (`backend/training/audit_include.py`, read-only on the data) checks the integrity of the result and its match to the authors' lists. Its overall result is PASS, with one documented exception.

Table: Audit of the processed INCLUDE data. {#tab:audit}
| Check | Result |
|---|---|
| Videos listed by the authors, processed | 4,292 listed, 4,284 processed (99.81 percent) |
| Manifest rows with a readable feature file | 4,284 of 4,284 |
| Missing, unreadable, empty arrays or wrong dimensions | 0 |
| NaN or infinite values | 0 |
| Duplicate manifest paths | 0 |
| Byte-identical feature arrays across files | 0 groups |
| Videos in two splits, or in the wrong split | 0 |
| Classes with a sample | 262 of 263 listed |
| Sequence length (frames) | minimum 17, median 31, 95th percentile 47, maximum 77 |
| Frames without a left hand, without a right hand, without both | 19.6, 29.6 and 11.9 percent |
| Samples per class | 4 to 25, median 15 |

The eight videos that are not processed all belong to one class, "Second (Number)". The released archives contain no folder of that name (they hold only "Second"), and no file with those names exists in any archive, so this is a defect of the released lists and not of the processing. The consequence is that the class has no sample and the project uses 262 of the 263 listed classes. Face landmarks are not used.

## Split

The authors' predefined split is kept exactly and is never re-split.

Table: Samples per split. {#tab:split}
| Split | Listed | Processed | Not processed |
|---|---|---|---|
| Training | 3,127 | 3,121 | 6 |
| Validation | 348 | 347 | 1 |
| Test | 817 | 816 | 1 |

Sixteen classes have no validation sample because the authors' lists give them none, so macro metrics on validation average over 246 classes. No class lacks a test sample or a training sample (the smallest has 3 training samples). INCLUDE publishes no signer identifiers, so the split cannot be checked for signer overlap. **Every result in this report is on the authors' predefined split, signer independence not verified**, and absolute accuracies are probably optimistic for new signers.

## Preprocessing and normalization

Landmarks come from MediaPipe Holistic (Python 0.10.14, model complexity 0) for the dataset, and from the WebAssembly build of the same family in the browser. Each frame contains 33 pose landmarks, 21 left-hand and 21 right-hand landmarks with coordinates x, y and z, which gives 75 x 3 = 225 values.

The normalization removes camera position and signer distance. With the left and right shoulder points s_L and s_R, the origin is their midpoint and the scale is the two-dimensional distance between them, so each landmark p becomes (p - origin) / scale. A missing hand is an all-zero block, and a frame without a usable pose is invalid and dropped. A short gap of at most three frames in a hand block is filled by linear interpolation when a hand is detected on both sides; longer gaps and gaps at the ends stay zero, so a hand that is absent is never invented. Finally the sequence is resampled linearly to 32 frames. The same functions serve training, the REST endpoints and the WebSocket, and the live path was checked to reproduce the offline predictions of 80 test samples exactly (within 1e-4).

[[fig:skeleton]] shows one stored test sample drawn only from its features, to illustrate what the classifier sees. It contains no image of any person.

![One INCLUDE test sample of the sign Hello drawn from its 225 stored features at eight of its 32 resampled frames. Only landmarks are drawn; the circle marks the nose position and is not a face.](figures/skeleton_sign.png){#fig:skeleton w=6.2}

[[fig:data]] summarizes the offline pipeline from the archives to the trained models.

![The offline data and training pipeline.](figures/diagram_data_pipeline.png){#fig:data w=6.4}

## Licence

The dataset's own licence is stated inconsistently: CC BY 4.0 in the Zenodo record and CC BY-NC-SA 4.0 on a third-party page. The project follows the stricter reading. INCLUDE-derived material (features, statistics, models and clips) may be shared only non-commercially under CC BY-NC-SA 4.0 with attribution, and the data, the features, the trained weights and the clips are kept out of the public repository (`DATA_NOTICE.md`). The code is under the MIT licence, which does not cover INCLUDE or anything derived from it. Eleven early clips remain in the history of the git repository. The avatar model is a Mixamo asset whose terms have not been confirmed; it is not distributed.

## What the dataset cannot show

The labels are the authors' class folders and no sign was checked by an ISL signer. The recordings come from one capture setup, so they do not show the variety of cameras, lighting and signers of real use. These are the reasons for the browser-path benchmark of Chapter 9 and for the recorder of Section 7.11.
