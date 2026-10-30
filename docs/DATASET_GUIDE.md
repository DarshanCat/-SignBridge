# Dataset guide

**Status: candidate datasets researched on 2026-10-29; no dataset has been downloaded, so no dataset has been
used for training and no result depends on one.** Facts below come from the cited pages; items marked
*unverified* must be checked by hand before any use or publication.

## Candidate ISL datasets

| Dataset | What it is | License (as read) | Signers | Notes |
|---|---|---|---|---|
| [INCLUDE](https://zenodo.org/records/4010759) (Sridhar, Ganesan, Kumar, Khapra; ACM MM 2020, DOI 10.1145/3394171.3413528) | Isolated word-level ISL videos. A search summary reports 263 signs in 15 categories and 4,287 videos, with a 50-sign subset (INCLUDE-50); *counts unverified against the paper*. 56.8 GB total, as zip parts on Zenodo. | Zenodo page: **CC BY 4.0**, record "Open". **Conflict:** an [IEEE DataPort record](https://ieee-dataport.org/documents/silent-voice-mediapipe-holistic-landmark-tensors-261-indian-sign-language-words-derived) derived from INCLUDE says INCLUDE is CC BY-NC-SA 4.0. Confirm on the Zenodo record before use. | Not stated on the record; videos were recorded by deaf students of St. Louis School for the Deaf, Adyar, Chennai. | Authors provide a train/test split (Google Drive file). **Whether that split is signer-independent is unverified**, and no signer IDs were found, which blocks a signer-disjoint split unless the signer is recoverable from the files. Best fit for this project's isolated-sign model. Code repository: [AI4Bharat/INCLUDE](https://github.com/AI4Bharat/INCLUDE) (MIT for code; data terms are on Zenodo). |
| [ISL-CSLTR](https://data.mendeley.com/datasets/kcmpdxky7p/1) (Mendeley Data, 2021, DOI 10.17632/kcmpdxky7p.1) | Continuous sentence-level corpus: 700 annotated videos of 100 sentences, plus 1,036 word-level images. | **CC BY 4.0** (as read). No signer consent process is described on the page. | 7 (2 native signers from a school for the deaf in Andhra Pradesh, 4 student volunteers from SASTRA, Thanjavur) | Sentence-level, so it does not suit an isolated-sign classifier directly. Seven signers would allow a signer-disjoint split. |
| CISLR ([EMNLP 2022](https://aclanthology.org/2022.emnlp-main.707); Hugging Face mirrors under Exploration-Lab and IIT-K) | Word-level ISL corpus. A search summary reports 7,050 videos covering 4,765 words; *unverified*. | **Not verified.** The Hugging Face pages are gated behind an access-conditions form. | Not verified. | Authors are at IIT Kanpur (per the ACL Anthology listing). Its published baseline learns from ASL data for one-shot ISL prediction; **this project must not mix ASL data into ISL training**. Requires logging in and accepting the conditions. Read them first. Many classes with few videos each makes classification hard. |

Other Mendeley sets surfaced in search (hand-gesture images, common phrases) were not examined and are not
recommended without checking license, labels and signer information.

## Blockers

1. **No data on disk.** Downloading is a user decision: INCLUDE is about 57 GB. Nothing has been fetched.
2. **Signer-independent evaluation on INCLUDE** is possible only if signer identity is available; otherwise results
   must be reported as *not signer-independent*. Check the split file and video metadata after download.
3. **License conflict for INCLUDE** (CC BY vs CC BY-NC-SA) must be resolved before publication.

## Pipeline for real data (implemented, tested on synthetic inputs only)

All commands run from `backend/` in the Python 3.11 venv with `requirements-ml.txt` installed.

1. Create `data/raw/<dataset>/index.csv` with columns `video,label,signer_id` (video path relative to the CSV;
   labels are ISL glosses; `signer_id` is pseudonymous).
2. Extract features (reads videos locally, writes only landmark arrays):
   `python -m training.preprocess_videos --index ..\data\raw\<dataset>\index.csv --out ..\data\processed\<dataset>`
   Videos in which no body pose is detected are skipped and listed.
3. Add `data\processed\<dataset>\dataset_info.json`:
   `{"name": "...", "language": "ISL", "license": "...", "source_url": "..."}`. Anything other than `"ISL"` is
   rejected, so ASL or other sign-language data cannot be trained as ISL. Training also records name, license and
   source in `metrics.json`.
4. Validate: `python -m training.validate_dataset --dir ..\data\processed\<dataset>` checks file shapes, finite
   values, class and signer counts, and warns about too few signers (< 3) or classes with < 5 samples.
5. Train: see `MODEL_TRAINING.md`.

## Consent-based custom recordings

`python -m training.record_sample --dir ..\data\custom --signer-id S01 --label HELLO --consent-confirmed`

- Refuses to run without `--consent-confirmed`, an explicit statement that the signer gave informed consent.
- Saves only landmark features (no video or image), adds a row to `manifest.csv`, and records the signer's consent
  date and scope once in `consent.csv`.
- Creates `dataset_info.json` with `consent_required: true`; `validate_dataset` then fails if any signer has no
  consent record.
- Use pseudonymous signer IDs. `data/` is git-ignored. Signers must be able to withdraw: delete their rows and
  files. Camera capture itself is **not tested** (no webcam in the test environment); only the file-writing logic
  is.
- Custom data from a handful of signers will not support strong claims. Signer-independent evaluation needs at
  least 3 signers, preferably many more.

## Phase 11 investigation (2026-10-29): INCLUDE, from the Zenodo API record

Source: https://zenodo.org/api/records/4010759 (machine-readable metadata of the record).

| Question | Finding |
|---|---|
| Access | `access_right: open`; no login or application. 46 files, 56,751,823,082 bytes (about 56.75 GB) |
| License | `metadata.license: cc-by-4.0` (CC BY 4.0). Still in conflict with a third-party derived record that says CC BY-NC-SA 4.0 (see above); the Zenodo record is the primary source, but the conflict is unresolved until you decide |
| Content | Record description: 4,292 videos (the paper cites 4,287; five were added later), 263 word signs in 15 categories; INCLUDE-50 is a 50-sign subset |
| Annotations | Class = sign word, from the folder structure; no signer metadata |
| Signers | Description says the videos show deaf students from St. Louis School for the Deaf, Adyar, Chennai. **No signer IDs or count are published**, so a signer-disjoint split cannot be made from metadata |
| Provided split | `train.csv` (3,475 videos) and `test.csv` (817). INCLUDE-50: 766 train / 192 test. **No validation split; signer independence of the authors' split is not documented** |
| Format | Video files (zip parts per category, e.g. `Adjectives_8of8.zip`) |
| Compatibility | Isolated word-level signs match this project's classifier. Words are English labels of Indian signs; label review by an ISL signer is advisable |
| Redistribution | CC BY 4.0 requires attribution; the NC variant, if it applied, would forbid commercial use. Do not redistribute the videos or derived landmark tensors until the license is settled |

**Decision paused:** no download was started. It needs your approval because of (a) the license conflict, (b) the 56.75 GB
size, (c) disk space. INCLUDE-50 alone cannot be downloaded separately from the zip parts without knowing which categories
contain its 50 signs (the authors' `train.csv`/`test.csv` list the videos).

How the new tools handle the missing pieces: use `training.make_manifest --split-file` with the authors' split (add a
validation portion yourself and **label the result "predefined split, signer independence unverified"**, which
`metrics.json` and `evaluate` do automatically). Do not claim signer-independent evaluation on INCLUDE unless signer
identity is recovered and checked.

## Phase 11 download (2026-10-29): approved by you, in progress

You approved downloading INCLUDE. Facts found while starting it:

- Zenodo serves each zip whole (no HTTP range support), and this machine has about 63 GB free, so the full 56.75 GB
  cannot be unpacked on disk. `training/include_stream.py` therefore downloads each zip, extracts only the videos in
  the authors' split lists, converts them to normalized landmark features with the same code the API uses, and then
  **deletes the zip and the videos**. Only the small `.npy` feature files and a manifest are kept in
  `data/processed/include`. This also means the raw videos are not retained locally.
- The authors' split lists (train 3,126 / val 347 / test 816 videos, plus INCLUDE-50 lists) were found in the
  AI4Bharat/INCLUDE GitHub repository (`train_test_paths/`); the Google Drive copy linked on Zenodo returns 404. The split
  is predefined, **signer independence is unverified** (no signer IDs exist), and results must say so.
- Throughput measured at about 0.7 to 1.3 MB/s per connection, so the whole download takes hours. Preprocessing speed
  (measured on one zip): 55 videos in 27 s with 6 workers, about 0.5 s per video.
- Python 3.11 had vanished from the machine (the Microsoft Store install was removed), breaking `backend/.venv`; it was
  rebuilt with Python 3.11.15 installed via `uv` (old venv kept as `backend/.venv_broken_py311_9`).
