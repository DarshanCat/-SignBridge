# Generation scoring and signer review

Two tools for people who are not the authors: a signer who writes reference glosses, and a signer who judges the avatar's clips. Neither changes a model, a clip or a label. No sign is signer reviewed today.

## 1. Scoring English to gloss and gloss to English (BLEU, gloss accuracy)

Code: `backend/nlp/generation_metrics.py` (metrics, no library), `backend/nlp/score_generation.py` (command line). Tests: `backend/tests/test_generation_metrics.py`, which check BLEU and the gloss scores against hand worked values.

**Reference file** (CSV, UTF-8, one sentence per row). A ready template with 13 sentences and no references is `docs/evaluation/generation_references_template.csv`.

| Column | Who fills it | Meaning |
|---|---|---|
| `id` | template | unique text, for example S01 |
| `english` | template | the English sentence |
| `reference_gloss` | **the signer** | the gloss sequence a signer would use: tokens separated by spaces, upper case, a fingerspelled word as `FS:WORD`; several acceptable answers separated by ` \| `. Empty means "not known": the row is skipped and counted |
| `english_alternatives` | optional | other acceptable English renderings of the sign sequence, separated by ` \| ` |
| `signer_id` | the signer | P01, never a name |
| `notes` | anyone | free text |

**Commands** (from `backend/`, with the virtual environment):

```bash
python -m nlp.score_generation --make-template ..\docs\evaluation\generation_references_template.csv
python -m nlp.score_generation --references my_references.csv --out ..\docs\evaluation\generation_scores
```

Task A, English to gloss: the system's gloss for `english` against `reference_gloss`: exact match, gloss word error rate (edit distance to the closest reference over its length), F1 of the bag of gloss tokens, and BLEU-4. Task B, gloss to English: the system's English for the first `reference_gloss` against `english` plus `english_alternatives`: BLEU-4 and exact match. To score another system, pass its output with `--hyp-gloss` and `--hyp-english` (CSV with the columns `id,hypothesis`).

BLEU is corpus level, 4-gram, brevity penalty, several references per sentence, sacreBLEU style "exp" smoothing (sentences of 3 to 6 tokens rarely share a 4-gram, unsmoothed BLEU would be 0). BLEU of very short sentences is unstable: read it with exact match and word error rate. The scorer refuses an unfilled file and never invents a reference. The scores are only as good as the references; with one signer they describe that signer's wording.

## 2. Signer review page

Tab **Signer review** (local use; hidden when `NEXT_PUBLIC_DISABLE_RECORDING` is set, and the endpoints answer 403 when `SIGNBRIDGE_RECORDING_ENABLED=false`, because it writes to the disk like the recorder).

A signer enters a reviewer ID (R01, never a name), picks a sign, watches the avatar (speed control and the source skeleton as in English to Sign), rates the clarity from 1 to 5, marks the sign correct or wrong, optionally writes a comment and saves. The page moves on to the next sign that reviewer has not reviewed.

- **Where it is saved:** `data/reviews/<REVIEWER>.jsonl` (git-ignored), one JSON line per review: reviewer ID, sign, clarity, verdict, comment, time (UTC) and the SHA-256 of the clip file that was reviewed. Records are only appended; a second review of a sign is a new line and the latest counts. Reviewers see only their own records.
- **Who may set a review flag:** only this page, through `POST /api/review/submit` (`backend/app/api/review_routes.py`). Nothing else writes a review, and **no code sets, infers or derives that a sign is reviewed or verified**: a review changes no clip file, no sign registry entry and no label (`Clip not signer-reviewed` stays everywhere). `backend/tests/test_review.py` checks that the clip and registry files are byte for byte unchanged after a review, that only the review route references the writer, and that no app code assigns `signer_reviewed` or `review_status`. What a set of reviews means for a clip's status is a decision for people, taken after real reviews exist.
- **Validation:** the sign must have a clip, clarity is a whole number 1 to 5, the verdict is `correct` or `wrong`, a comment is at most 500 characters.
