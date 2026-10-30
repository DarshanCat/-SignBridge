# Translation services (Phase 5)

All translation is a **rule-based baseline** driven by `backend/config/translation.json`
(override the path with `SIGNBRIDGE_TRANSLATION_CONFIG`). It is not ISL understanding.

## Services (`backend/app/translation`, `backend/app/services`)

| Service | Function | Behaviour |
|---|---|---|
| Sign labels to gloss | `labels.labels_to_gloss` | Upper-cases, hyphenates spaces/underscores, drops empties, collapses immediate repeats; reports labels missing from the vocabulary. Not wired into the API yet (Phase 7). |
| Gloss to English | `gloss_to_english` | Longest-match configured gloss phrases, otherwise one English word or phrase per gloss; unknown glosses listed as unsupported and omitted; ends with `?` if a question gloss or question phrase is present, otherwise `.`. Token-by-token, no grammar. |
| English to gloss | `english_to_gloss` | Lowercase tokenization, longest-match English phrases, word lookup (inflections must be listed per gloss), stopword removal, optional rule moving question glosses to the end. Words not in the vocabulary are returned as unsupported (no fingerspelling). Coverage = mapped words / (mapped + unsupported words). |
| Gloss to animation | `services.avatar_plan.plan_animations` | Matches each gloss to a `*.glb` clip in `frontend/public/animations` (filename stem = gloss, upper-cased). Missing clips are reported and the plan is marked not playable. |

## Configuration format

`stopwords`, `glosses` (`GLOSS: {english, words[]}`), `english_phrases` (`words[]` to `gloss[]`), `gloss_phrases`
(`gloss[]` to `english`), `rules` (`question_words_to_end`, `question_glosses`). Invalid or missing config makes the
translation endpoints return 503.

## What the shipped vocabulary is

13 glosses and a handful of phrases, written as an **illustrative placeholder**. The gloss labels, the
question-word-last rule and the sample phrase orders are assumptions that **have not been validated by ISL signers
or linguists**, and the sign for each gloss has not been checked. Do not present them as correct ISL.

## Limitations

- No morphology, tense, agreement, classifiers, facial grammar or non-manual markers.
- Exact word match only; synonyms and inflections must be added by hand.
- English output from glosses is a literal join of words.
- Translation coverage and unsupported-phrase rate should be measured on a held-out sentence set before being
  reported; none has been measured.
- No animation clips exist, so every avatar plan currently reports all signs as missing.
