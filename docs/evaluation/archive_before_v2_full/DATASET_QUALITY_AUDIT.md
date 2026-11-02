# INCLUDE dataset quality audit

Date: 2026-10-30. Tool: `backend/training/audit_include.py` (read only on the data; 2 unit tests). Machine readable results:
`dataset_quality.json`, `split_integrity.json`, `class_distribution.csv` in this folder.

## Overall result: FAIL

The feature files themselves are clean (section 1), but the processed set is **not a complete copy of the authors' split**:
613 of the 4,292 listed videos (14.3 percent) are missing from the manifest (section 2). Training on it would silently
use a smaller and differently balanced split than the authors' one. Do not train until this is fixed or knowingly accepted.

## 0. Processing completion

All 44 zip archives have completion records (44 part files) and `data/processed/include/manifest.csv` exists with 3,679 rows
(3,679 feature files on disk, none orphaned). The earlier one zip trial manifest stays renamed
`manifest.trial_1zip_STALE.csv` and was ignored. No archive failed and no video was excluded for being unusable
(0 exclusions).

## 1. Integrity: PASS

| Check | Result |
|---|---|
| Manifest rows with a readable feature file | 3,679 of 3,679 |
| Missing, unreadable or empty arrays | 0 |
| Wrong dimensions | 0 (every array is T x 225) |
| NaN or infinite values | 0 |
| Data type | float32 for all |
| Duplicate manifest paths | 0 |
| Byte identical feature arrays (possible duplicate videos) | 0 groups |
| Feature files not in the manifest | 0 |
| Manifest rows without a processing record | 0 |

Feature layout: pose 33 x 3, left hand 21 x 3, right hand 21 x 3; origin at the shoulder midpoint, scale by shoulder width;
face landmarks are not used. Frames without a body pose were discarded during extraction, and extraction used every second frame.

## 2. Split integrity against the authors' lists: FAIL

The authors' lists (AI4Bharat/INCLUDE `train_test_paths`) contain exactly the expected 3,127 / 348 / 817 videos (4,292 total).
Counts below are from `split_integrity.json`.

| Split | Listed | In manifest | Missing | Missing share |
|---|---|---|---|---|
| train | 3,127 | 2,671 | 456 | 14.6 percent |
| val | 348 | 299 | 49 | 14.1 percent |
| test | 817 | 709 | 108 | 13.2 percent |

What is fine: no video appears in two splits; no manifest row is outside the lists (no unexpected samples); every row carries the
split the lists assign; no identical feature arrays appear across splits (no detected leakage).

What is wrong, and why:
- The lists name videos with the extension `.MOV`. In 28 of the 44 zips, many videos are stored as `.MP4`. My streaming matcher
  compared full paths including the extension, so 605 videos were **skipped as "not in the split lists"**. All 54 skipped examples
  that were logged (for example `Animals/1. Dog/MVI_8560.MP4`) match a listed `.MOV` path once the extension is ignored.
- The affected zips are 28 archives totalling about 36 GB (Animals, Clothes, Colours, Days_and_Time, Electronics, Home, Jobs,
  Means_of_Transportation, People, Seasons and Society). Home (190) and Society (162) lose the most; Days_and_Time loses 83.
- 605 skipped videos versus 613 missing listed videos leaves **8 unexplained**. A likely cause is the folder named
  "Second (Number)" in the list against "81. Second" in the zip, but this is not verified, because the zips were deleted after
  processing.
- Class coverage is damaged: 61 classes have no validation sample, 8 have no test sample, and 1 class has no training sample.
  Many of the classes were hit hardest, so evaluation on this subset is not comparable to published INCLUDE numbers.

Signer independence: **unverified.** The dataset publishes no signer identifiers (every manifest row has signer_id "unknown"), so
the lists are the authors' predefined split and must never be called signer independent.

## 3. Statistics

- Usable samples: 3,679. Classes: 266 (the record states 263 word signs).
- Per split: train 2,671, val 299, test 709.
- Samples per class: min 1, median 11, max 22; 5 classes have fewer than 5 samples and 88 have fewer than 10.
- Sequence length (frames after taking every second frame): min 17, 5th percentile 22, median 30, mean 31.75, 95th percentile 46, max 77.
- Feature shape (225,) per frame, float32; 0 non finite arrays; 0 exclusions.
- Missing landmarks (share of all frames, 116,800 or so frames): no left hand 17.1 percent, no right hand 27.4 percent, no hand at
  all 9.6 percent. Pose is present in every stored frame by construction. Highest per class rates of frames with no hand at
  all are around 31 to 33 percent (narrow, Month, Store or Shop, Week, Wednesday). Per class values are in `class_distribution.csv`.
- Unexpected labels: 266 classes against the stated 263. Four groups named "Extra" appear (Adjectives/Extra, Adjectives/extra,
  Animals/Extra, Places/Extra); the single sample class "Adjectives/Extra" is the one without a training sample. Two labels carry
  a bracket suffix (Race (ethnicity), you (plural)). These look like non vocabulary or duplicate folder names in the source and
  should be reviewed against the authors' label maps before training.
- Missing gloss labels: none (every row has a label), but the labels are the English folder names, not reviewed ISL glosses.

## 4. Risks

**License conflict, still unresolved.** Checked on 2026-10-30 against the Zenodo API record for the dataset
(https://zenodo.org/records/4010759, DOI 10.1145/3394171.3413528, creators Sridhar, Ganesan, Kumar and Khapra):
the record metadata states `"license": {"id": "cc-by-4.0"}` with `"access_right": "open"`. A separate third party page
(IEEE DataPort, a dataset derived from INCLUDE) describes the original as "CC BY-NC-SA 4.0, non-commercial". The creators'
own record says CC BY 4.0, but I cannot confirm the other statement is wrong, and I have not contacted the creators. Until
you settle it: non commercial academic use only, cite Sridhar et al. (ACM MM 2020), do not redistribute the videos or the
derived landmark files, keep `data/` out of Git.

**No signer identifiers.** Signer dependent and signer independent results cannot be separated, which the synopsis lists as a
design principle. Any result must be labelled "authors' predefined split, signer independence unverified". The synopsis
also plans a self recorded multi signer corpus; that corpus is the only route to a signer independent claim.

**Other risks.** Landmarks come from Python MediaPipe at frame stride 2 and the live app uses the browser build, so small
differences are possible. Face landmarks are not stored, so the synopsis ablation with face features needs re-extraction.
The label set is English words, and the first extraction missed 14 percent of the authors' split.

## 5. Blockers to model training

1. **Split completeness (FAIL):** 613 listed videos are missing. Fix: match videos ignoring the extension, then re-download and
   re-process the 28 affected zips (about 36 GB; disk currently has about 47 GB free). The 8 videos not explained by the
   extension need a separate look.
2. License conflict unresolved (use restricted as above).
3. Label review: decide what to do with the "Extra" folders and the two bracketed labels.
4. Signer independence cannot be claimed.
