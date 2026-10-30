# IEEE paper checklist

Target conference and template: **not selected.** Nothing in this repository claims compliance with an IEEE template. Choose a
conference, download its official template and author instructions, then re-check every item below against them.

## Status legend
Done = evidence exists in the repository. Pending = requires work or data. Blocked = needs an external resource.

## A. Evidence needed for a defensible paper

| Item | Status | Evidence or what is missing |
|---|---|---|
| Authorized ISL dataset with documented license | Blocked | None downloaded; INCLUDE license conflict unresolved (`DATASET_GUIDE.md`) |
| Signer-independent train/val/test split | Pending | Tool exists (`training/data.py`); needs signer IDs or an author split |
| Trained model with reproducible config and seeds | Pending | Pipeline exists (`training/train.py`); no real run |
| Accuracy, macro-F1, per-class, confusion matrix | Pending | `training/metrics.py` ready; no real data |
| Baselines (majority class, nearest neighbour) | Pending | Not implemented |
| Multiple seeds, mean and std | Pending | Plan in `EXPERIMENT_PLAN.md` |
| Real-camera landmark extraction check | Pending | Never run on a physical webcam |
| Browser vs Python landmark consistency | Pending | Not measured |
| Latency: extraction, preprocessing, API, inference, end to end | Partial | Phase 9 partial timings only (`docs/benchmarks/phase9_latency.json`) |
| Translation coverage on a stated sentence set | Pending | No sentence set |
| ISL signer or linguist review of vocabulary and rules | Blocked | None done |
| Verified sign animations and animation coverage | Blocked | Zero clips |
| User study or expert evaluation | Pending | Not planned in detail |
| Ethics: consent for any recordings, data statement | Pending | Consent tooling exists (`record_sample.py`); no data collected |

## B. Manuscript content

| Item | Status |
|---|---|
| Abstract written without unmeasured claims | Draft in `PROJECT_REPORT.md`, update with results |
| Related work from sources actually read | Pending (`PROJECT_REPORT.md` section 4 says so) |
| Novelty statement | Not made. Do not claim novelty without a literature review |
| Method sections (landmarks, model, translation, avatar) | Draft, matched to code |
| Results section | Pending, empty by design |
| Limitations | Draft |
| References verified | 6 verified for existence and bibliographic data; author lists for [4], [5] to confirm |
| Figures: architecture diagram | Mermaid in `PROJECT_REPORT.md`; redraw in the venue's style |
| Author, affiliation, supervisor, acknowledgements | Placeholders |

## C. Template and submission (after choosing a venue)

Page limit; two-column IEEE template check; reference style (IEEE numeric); figure resolution and accessibility; anonymization if
double-blind; copyright form; keywords; plagiarism check; dataset and code availability statement; license compliance for any
dataset (attribution, non-commercial terms).

## D. Do not write

Accuracy or latency numbers that were not measured; "state of the art"; "real-time" without measured frame rate and
latency; "fully ISL translation"; any claim that an avatar clip is a correct sign without signer review; any use of ASL
data as ISL.

## E. Verdict today

**Insufficient evidence for submission.** The software foundation exists; the experiments the paper would report have not
been run.
