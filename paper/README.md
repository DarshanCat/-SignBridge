# Paper: offline accuracy is not webcam accuracy

Working title: "Offline Accuracy Is Not Webcam Accuracy: Measuring the Deployment Gap in Landmark-Based Indian Sign Language Recognition". Solo author: Darshan BG. IEEE conference format (two columns, IEEEtran 1.8b, downloaded from CTAN).

## Build

```powershell
.\paper\build.ps1
```

This redraws the figures (`figures\make_figures.py`, needs matplotlib, which the backend virtual environment has) and runs pdfLaTeX, BibTeX and pdfLaTeX twice with the MiKTeX installed for this user. That MiKTeX has no PSNFSS definition files and could not download any, so `ot1ptm.fd` (the Times mapping, same content as PSNFSS) sits next to `main.tex`; remove it if PSNFSS is installed. The packages used are only those present: graphicx, amsmath, amssymb, xcolor, url, array.

## What is still open

- Every `\pending{...}` in `main.tex` (red in the PDF) is a number or sentence that needs the three-seed runs (Tables IV, V and VI, the abstract, the results paragraph of Section VI, the conclusion, the last item of the test-split list). Search for `\pending` and `\todo`.
- Every entry of `refs.bib` is marked `[VERIFY]` in a comment: check title, authors, venue, year, pages and DOI of each one against the publisher page. Delete an entry, and the sentence that cites it, if it cannot be confirmed.
- The author email and the acknowledgment are `\todo{...}` placeholders.

## Where the numbers come from

All numbers are from `docs/evaluation/`; nothing was estimated.

| Paper content | File |
|---|---|
| Dataset counts, split, missing hands, sequence statistics | `DATASET_QUALITY_AUDIT.md` |
| Baseline test numbers (Table I), threshold rule, trade-off (Table VI cells) | `results.md` |
| Browser against offline, paired tests, diagnostics (Table II, Fig. 1) | `BROWSER_PATH.md`, `browser_path_rows.json` |
| Vertical scale sweep, noise and dropout (Fig. 2, Table III) | `BROWSER_PATH.md`, `browser_path_validation_sweep.json` |
| Signer size in the picture (Fig. 3, Section VII) | `BROWSER_PATH.md` (framing section) |
| Segmentation figures in the case study | `SEGMENTATION.md` |
| Larger browser corpora (211 validation and 312 test videos, two framings), six seed-0 models, raw per video results | `eval_val.json`, `eval_test.json` (not used in the text yet; they feed the pending tables) |
| The same, as readable validation tables with intervals and paired tests | `validation_tables_seed0.md` |
| Which videos make up those corpora | `browser_corpus_val_samples.json`, `browser_corpus_test_samples.json` |
| Check that every extracted landmark file is readable, complete and unique | `browser_corpus_validation.txt` |
| Test and validation metrics of the six seed-0 models (top-1, top-5, macro-F1, accuracy against coverage) | `seed0_model_metrics.json` |

Scripts that produced these files are in `tools/browser_path/` (`select_all.py`, `browser_harness_corpus.js`, `serve_frames_corpus.py`, `run_harness.sh`, `validate_corpus.py`, `eval_matrix.py`, `report_matrix.py`, `zoom_save.py`). The three-seed runs are driven by a separate script that is not copied until those runs have finished.

Facts about the training settings and the augmentation (ranges, probabilities, the exact y scale) are from the code in `backend/training/` and the notes in `docs/PROJECT_STATUS.md`.
