# Training plan: INCLUDE plus self-recorded signs

Status: plan only. Nothing has been trained and no self-recorded data exists yet. Every number below that is not a measurement from this project is
marked as an assumption.

## 1. What this is for

The live recognizer knows the 262 INCLUDE classes. It cannot output the 50 grammar words (WHERE, GO, LIKE, NOT, HELP, WHAT, YES, NO and 42 more),
so sentences with questions, negation and verbs cannot be recognized, only typed. The plan adds those words from signs you record, and at the same
time measures how the model behaves on a webcam instead of INCLUDE's camera, which has never been measured.

## 2. Data

| Part | Source | Used for | Split |
|---|---|---|---|
| INCLUDE | 4,284 samples, 262 classes (`data/processed/include_v2`) | everything it already does | the authors' predefined split, kept exactly; signer independence not verified |
| New classes | takes of the 50 grammar words from the guided session | training, validation and test of the new classes | by signer (section 5) |
| Overlap words | takes of about 20 INCLUDE words (for example HELLO, THANK-YOU, DOCTOR) recorded by the same signers | measuring the INCLUDE to webcam domain shift, and as extra training data | by signer (section 5) |

Overlap words are not optional if you want to know whether the existing model works on a webcam: they are the only way to compare "INCLUDE model on
INCLUDE test samples" with "INCLUDE model on the same class recorded on a webcam by an unseen person".

## 3. How to collect

Use the Record sign tab, Guided session. One signer per session: enter a signer ID (P01, P02, and so on, never a name), takes per sign, and the list
of signs (the 50 grammar words are preloaded with WHERE, GO, LIKE, NOT, HELP, WHAT, YES, NO first). Each take is a 3 second landmark recording after a
3-2-1 countdown. Only landmarks are stored, under `data/recorded/<signer ID>/<SIGN>/`; rejected takes are explained and not saved. Stopping and
starting again with the same signer ID continues where that signer stopped.

A take is accepted when it has at least 20 frames, the body was seen in at least 90 percent of the frames, a hand in at least 70 percent, and the live
segmenter finds a sign in it (hands raised and moving at some point). Ask each signer to start with the hands down, sign once, and lower the hands.

Collection rules that matter for the result:
- **Who signs.** The labels are whatever the signer does. A hearing person guessing a sign teaches the model that guess. At least one fluent ISL signer
  has to show the signs (or review the takes) before the recorded data is called ISL. Until then every result is "recognizes what these recorders did".
- **Variety.** Different people (height, hand size, handedness; include a left-handed signer if possible), different days, lighting and distances, the
  camera at the height you will actually use. Do not record one signer's whole set in one burst of identical takes.
- **Consent and privacy.** Record only people who agreed, use IDs, keep `data/recorded/` out of git (it already is). No video is stored.
- **Same landmarks as live.** Recordings use the browser's MediaPipe, so they carry the browser's behaviour. Run the Landmark check tab once to know how
  far the browser differs from the Python MediaPipe that produced INCLUDE's features.

## 4. Pre-processing

`python -m training.make_combined_manifest` (already written and tested on synthetic data) builds the combined manifest in a new folder:
- INCLUDE rows are referenced unchanged with the authors' split and `signer_id` unknown.
- Each take loses frames without a body pose and is cut to the sign with the live segmenter and its rest padding, so training sees what live
  recognition classifies. Takes without sign movement are left out and listed; takes with several segments are kept (first to last) and counted.
- Recorded INCLUDE glosses are labelled with the INCLUDE class name; grammar words keep their gloss.
- Classes with fewer than 5 training takes are left out and listed rather than trained on.
- It refuses to write into an existing folder and never changes the recordings or the INCLUDE data.

The model input stays what it is today: 225 features per frame, normalized to the shoulders, resampled to 32 frames, hand gaps filled up to 3 frames.

## 5. Split (the part that makes the result mean something)

INCLUDE keeps the authors' train, validation and test. For the self-recorded data the unit of splitting is the **signer**:
- **Test signer(s):** every take of this person is test. The model never trains on, validates on or is tuned on them. Choose them before looking at any
  result and do not change the choice afterwards.
- **Validation signer(s):** used for early stopping, picking hyperparameters and the confidence threshold. Not test.
- **Training signers:** everyone else.

### Signer roles (fixed on 2026-11-02, before any recording was used)

| Role | Signer IDs | Notes |
|---|---|---|
| Training | S01, S02, S03 | S01 also did the smoke test; the smoke test takes are ordinary S01 takes (same signer ID) and the session resumes up to the full count |
| Validation | S04 | early stopping, hyperparameters, confidence threshold |
| Test | S05 | never trained on, validated on or tuned on; evaluated once per trained model |

This is the "minimum meaningful" level of section 8 (5 signers, 3 / 1 / 1): one unseen test person, so the result describes how the model does for S05 and
says little about people in general. The roles are stored in `backend/config/signer_roles.json`. The builder reads that file and refuses a
different test or validation signer on the command line, and refuses a recorded signer that has no role (more training signers can be added to the
file; the validation and test signers are not to be changed after a result has been seen). Signer IDs are stored in upper case (typing s01 saves S01).

The builder fails if a signer would land in two splits. Taking validation and test takes at random from every signer would leak the person into
training and report an optimistic number (that is what INCLUDE's predefined split may also do, which is why its numbers carry the label "signer
independence not verified").

## 6. Training

Start from the settings already chosen on INCLUDE: 1D CNN, up to 60 epochs, patience 10, hand gap 3, learning rate 0.001, hidden 128, 2 layers, dropout
0.3, batch 16, seed 0. Two things are decided on the validation signer only:
1. **From scratch on the combined data, or fine-tune the current INCLUDE model** with a larger output layer (312 classes). Train both, keep the better
   by validation macro F1.
2. **Imbalance and augmentation.** INCLUDE classes have 4 to 25 samples (median 15); a new class with 3 training signers and 8 takes has 24. Compare plain
   training, class weights, and landmark augmentation (rotation, scale, speed). On INCLUDE the pilot found augmentation within noise; with few signers it
   may help, so test it rather than assume.

BiGRU and Transformer are retrained for the comparison table with identical settings. The test split is evaluated once per trained model.

## 7. What gets reported

Always labelled: INCLUDE part "authors' predefined split, signer independence not verified"; self-recorded part "signer-level split, N training
signers, M validation, K test signer(s) never used in training or tuning".

| Table | Content |
|---|---|
| A | INCLUDE test (816 samples, authors' split): top-1, top-5, macro F1. Must stay close to today's 91.3 / 99.0 / 91.1 (a regression here means the new classes hurt the old ones) |
| B | Self-recorded test signer(s): pooled top-1, top-5, macro F1 over the new classes, and the 8 priority words; confusion matrix; UNRECOGNIZED rate at the live threshold |
| C | Overlap words on the test signer: the current INCLUDE-only model versus the combined model, same takes (the webcam domain shift) |
| D | Threshold chosen on the validation signer, with accuracy and coverage on the test signer at that threshold |
| E | Continuous mode: real recorded takes joined into streams (as in `docs/evaluation/SEGMENTATION.md`) with real rather than synthetic pauses |

Per-sign accuracies are shown for information only: with 10 test takes of one sign, 8 correct has a 95 percent interval of 49 to 94 percent, so single
signs cannot be ranked. Pooled numbers and the 8 priority words together are interpretable.

A grouped evaluation script for tables B to D does not exist yet and is the first thing to write once data exists.

## 8. How much data is needed (sizes)

Interval widths below come from the binomial formula at 85 percent accuracy and count only the sampling noise of the test takes. They assume the takes of
a test signer are independent, which is generous; they say nothing about how much accuracy varies from one person to the next, and that variation
(unknown here) is usually the larger error. One test signer therefore describes one person.

| Level | Signers (train / val / test) | Takes per sign per signer | Takes per sign | Total for 50 signs | What it can support |
|---|---|---|---|---|---|
| Smoke test | 2 (1 / 0 / 1), your own recordings | 5 | 10 | 500 | the pipeline works; not a result |
| Minimum meaningful | 5 (3 / 1 / 1) | 8 | 40 | 2,000 | pooled accuracy on one unseen person, interval of about plus or minus 3 points from take sampling alone (n = 500 test takes) |
| Recommended | 8 (5 / 1 / 2) | 10 | 80 | 4,000 | two unseen people (a first look at between-person spread), n = 1,000 test takes, about plus or minus 2 points sampling noise |

Effort (assumption: about 8 seconds per take including the countdown and a glance at the result, 20 percent of takes retried): 400 takes for one signer at
8 takes per sign is about 45 to 55 minutes; the minimum level is roughly 4 to 5 hours in total across signers, the recommended level roughly 9 to 11. Add
about 20 overlap words by 5 takes per signer (100 more takes each).

## 9. Risks and open points

- Few signers: anything below about 5 trained signers mostly learns the recorders.
- Unreviewed signs: no ISL signer has checked the recordings; the model cannot be better than the demonstrations.
- Browser versus Python landmarks: unmeasured until the Landmark check is run on a real camera.
- Left and right: the features keep MediaPipe's left and right; a left-handed signer swaps the roles of the hands.
- Rest pose: the segmenter assumes the hands go down or stop between signs; signers who never do will not segment.
- The 8 INCLUDE videos that do not exist and the 16 classes without validation samples (audit) are unchanged by this plan.
- Licence: INCLUDE-derived material stays under CC BY-NC-SA 4.0 handling (`DATA_NOTICE.md`); the self-recorded takes are your own material and are not in git.

## 9a. Commands once data exists

```powershell
# 1. record with the guided session (Record sign tab), one signer ID per person

# 2. build the combined manifest in a NEW folder (the roles come from config\signer_roles.json: train S01 S02 S03, validation S04, test S05)
cd backend
.\.venv\Scripts\python -m training.make_combined_manifest --include-manifest ..\data\processed\include_v2\manifest.csv `
    --recorded ..\data\recorded --out ..\data\processed\combined_v1

# 3. train and compare (same settings for every model); the test split is evaluated once per model
.\.venv\Scripts\python -m training.compare_models --manifest ..\data\processed\combined_v1\manifest.csv --out ..\data\models_combined_v1 `
    --results ..\docs\evaluation\results_combined_v1.md --epochs 60 --patience 10 --max-gap 3 --threads 8
```

The results file has its own name on purpose: `docs/evaluation/results.md` (INCLUDE only) is never overwritten.
