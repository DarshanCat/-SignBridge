# INCLUDE dataset quality audit (v2, complete)

Date: 2026-10-31. Tool: `backend/training/audit_include.py` (read only on the data). Machine readable results: `dataset_quality.json`,
`split_integrity.json`, `class_distribution.csv` in this folder. The earlier audit of the partial v1 and v2 data (result FAIL, 613 listed
videos missing) is kept unchanged in `archive_before_v2_full/`.

## Overall result: PASS, with one documented exception

Integrity passes, the manifest matches the authors' split lists, and 4,284 of the 4,292 listed videos (99.81 percent) are processed.
The 8 that are not processed are not present in the released archives (section 2), so they cannot be recovered by any processing fix.

## 0. Processing completion

All 72 zip part records exist (44 from the first run, 28 from the supplement run; each archive was processed exactly once, no member path
and no feature file name appears twice). The v2 manifest `data/processed/include_v2/manifest.csv` has 4,284 rows; it references the 3,679
v1 feature files (by relative path, nothing was copied or modified) and 605 supplement files. 0 exclusions.

## 1. Integrity: PASS

| Check | Result |
|---|---|
| Manifest rows with a readable feature file | 4,284 of 4,284 |
| Missing, unreadable or empty arrays | 0 |
| Wrong dimensions | 0 (every array is T x 225) |
| NaN or infinite values | 0 |
| Data type | float32 for all |
| Duplicate manifest paths | 0 |
| Byte identical feature arrays (possible duplicate videos) | 0 groups |
| Feature files not in the manifest | 0 |
| Manifest rows without a processing record | 0 |

Sequence length: min 17, median 31, p95 47, max 77 frames (every second frame was extracted). No frame lacks a body pose (such frames were
dropped during extraction). A missing hand is an all zero block: 19.6 percent of frames lack the left hand, 29.6 percent the right hand,
11.9 percent both. Face landmarks are not used.

## 2. Split integrity against the authors' lists: PASS with one exception

| Split | Listed | In manifest | Not processed |
|---|---|---|---|
| train | 3,127 | 3,121 | 6 |
| val | 348 | 347 | 1 |
| test | 817 | 816 | 1 |

- No video appears in two splits; no manifest row is outside the lists; every row carries the split the lists give it; no identical feature
  arrays appear across splits (no detected leakage); the filename fallback was needed for 0 rows.
- The 8 videos not processed are all in one class listed as `Days_and_Time/Second (Number)` (MVI_4647 to MVI_4650 and MVI_5503 to MVI_5506).
  The archives contain no folder of that name: the Days_and_Time zips hold only `81. Second` (checked directly in the kept archives), and
  no file with these stems exists in any zip (the matcher also tries by file name). This is a defect of the released lists, not of the
  processing. Consequence: the class "Second (Number)" has no sample, so there are 262 classes, not 263.
- Classes without a validation sample: 16 (Mean, Nice, Ugly, cheap, deep, expensive, female, hard, high, light, male, rich, strong, thick,
  thin, weak). The authors' lists give these classes no validation video (the listed counts match the expected 3,127 / 348 / 817 exactly),
  so this is inherent in the split. Macro metrics on validation therefore average over 246 classes. Classes without a test sample: 0.
  Classes without a training sample: 0 (the smallest has 3 training samples).

## 3. Class balance

262 classes, 4 to 25 samples per class (median 15). Per class counts are in `class_distribution.csv`. Labels come from the class folder in
the path; nested "Extra" folders were merged into their parent class (see `LABEL_REVIEW.md`).

## 4. What this audit does not establish

- Signer independence: INCLUDE publishes no signer IDs, so the predefined split cannot be checked for signer overlap. Results on it are
  labelled "authors' predefined split, signer independence not verified".
- Label correctness: labels are the authors' class folders; no sign was checked by an ISL signer.
- Licence: unresolved (CC BY 4.0 per Zenodo, CC BY NC SA 4.0 per a third party page). Training is allowed for non-commercial academic use
  with attribution; INCLUDE-derived material may only be shared non-commercially under CC BY-NC-SA 4.0 (`DATA_NOTICE.md`), and data, features, models and clips stay out of git.
