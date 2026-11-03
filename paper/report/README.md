# Project report

`SignBridge_Project_Report.docx` (and the PDF that Word exports from it) is built by `build_report.py` from the chapter files in `content/` and the figures in `figures/`. Nothing in the Word file is edited by hand; change the content files and rebuild.

```powershell
python paper\report\make_diagrams.py     # architecture, pipelines, gloss hub, data pipeline (matplotlib; Graphviz and Mermaid are not installed here)
python paper\report\make_charts.py       # charts from docs/evaluation and the landmark skeleton figure from stored features
python paper\report\build_report.py      # Word file, table of contents and lists updated by Word, PDF exported, page count printed
```

Screenshots and avatar frames come from `capture_screens.js` (Playwright against the production build on ports 3110 and 8110, with a fake camera that plays a head-masked INCLUDE video made by `mask_video.py`) and `finalize_images.py`.

## Numbers

Every number is typed from a file in `docs/evaluation` or read from one at build time (`{{j:file.json:path:format}}` in the content files). Cells that wait for the three-seed runs show a red PENDING. When `docs/evaluation/three_seed_summary.json` exists, they are filled at the next build. Its keys are `<arch>_<kind>.<metric>` with arch in cnn, bigru, transformer, kind in base, aug, and metric in offline, br16x9, br4x3, br4x3_raw, wrong_accepted, threshold; each value is the text to print, for example "0.79 (sd 0.01)".

## Rules checked at build time

No em dash and no double hyphen in prose (command lines inside code blocks may contain flags), every citation key must exist in `paper/refs.bib`, every figure file must exist. References are formatted in IEEE style from `paper/refs.bib`; each of them still carries its `[VERIFY]` note there.
