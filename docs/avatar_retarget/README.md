# Avatar sign clarity: measurement and frame sheet

- `MEASUREMENT.md`: per joint error of the avatar against the source landmarks, before (the clips' own tracks) and after (the retargeter). Regenerate: run `retargetMeasure.test.ts` with `RETARGET_REPORT_DIR` set to this folder, then `python -I tools/avatar/summarize_retarget.py`.
- `measurement_*.json`: the raw numbers behind it.
- `../screenshots/avatar_retarget/frame_sheet.jpg`: five signs (hello, doctor, hospital, book, market), two moments each, before (left) and after (right, with the source landmark skeleton toggle on). Software GL capture, so colours differ slightly from a real GPU.

No model, data split or evaluation result is involved. No clip is signer reviewed.
