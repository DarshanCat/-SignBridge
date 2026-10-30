# English and ISL gloss rules (Phase 4)

Code: `backend/nlp/` (rules, dictionary loader, fingerspelling), dictionary: `backend/config/gloss_dictionary.json`
(built by `nlp/build_dictionary.py`), API: `POST /api/nlp/text-to-gloss` and `POST /api/nlp/gloss-to-text`.
Tests: `backend/tests/test_nlp.py` (80 cases, 36 English to gloss pairs, 20 gloss to English pairs, 8 round trips) and
`test_nlp_api.py`. spaCy 3.8.7 with `en_core_web_sm` 3.8.0 (see `backend/requirements-nlp.txt`).

**These are simplified, assumed rules for a prototype. No ISL signer or linguist has validated them, and they cover simple single
clause sentences. They are not a model of ISL grammar.** The expected glosses in the tests document the rules; they are not
linguistic ground truth.

## Rules, in output order for each clause

1. Time signs first (yesterday, today, tomorrow, morning, days, "last week", "next year").
2. Subject and other content in English order (possessives use the pronoun sign, so "my brother" gives I BROTHER).
3. Verbs after their objects (subject object verb), lemmatized (went becomes GO).
4. NOT after the verbs, then modals (CAN, MUST).
5. Question words (WHAT, WHERE, WHO, WHY, WHEN, HOW, WHICH) last.

Dropped, and reported with a reason in the response: articles and determiners, the copula and auxiliaries, prepositions, the infinitive
"to", "and", punctuation, and intensifiers such as "very". Sentences are split into clauses at "but" or "and" when a verb follows.

Non manual markers are returned as tags for the avatar: `negation`, `wh-question`, `yes-no-question`. Tense is not marked on verbs; it is
reported from time signs and verb forms.

## Dictionary

313 entries: 263 INCLUDE class names (the signs a recognition model can learn from this dataset; part of speech from the INCLUDE
category) and 50 grammar placeholders that INCLUDE does not contain (GO, WHERE, WHAT, NOT, NAME, WATER, HOME and so on). The
placeholders are assumed ISL lexicon items: they have no recognition data and no animation and are unvalidated.

Gloss forms: upper case, words joined by hyphens, brackets become part of the name: YOU-PLURAL, RACE-ETHNICITY, SECOND-NUMBER (a different
sign from SECOND, the time unit), STORE-OR-SHOP, THANK-YOU.

## Fingerspelling fallback

A word that is not in the dictionary (names, rare words, digits) becomes a token such as `FS:RAVI` with its letters. Each letter would be
a manual alphabet clip; none exist yet.

## Gloss to English (Module A output)

Reverses the order, inserts articles, the copula and auxiliaries, adds "to the" after motion verbs and place nouns, conjugates verbs from
time signs (YESTERDAY or BEFORE give past, TOMORROW or NEXT give future, otherwise present), turns "pronoun NAME name" into "My name is X",
and writes fingerspelled tokens as names. Limits: a tiny verb list, no plural handling, "the" is inserted by heuristics, and a missing time sign
leaves the tense in the present.

## Known limitations

No non manual grammar beyond the three tags, no classifiers, no role shift, no agreement, no adjective ordering rules, no multi sentence
discourse. Words are matched by lemma against the dictionary. Output has never been judged by ISL users.

## Non-manual markers on the avatar (rule-based approximation)

The text to gloss output carries tags (negation, yes-no-question, wh-question). The avatar has no face animation, so the player adds a small offset to the head bone only: negation is a head shake (0.22 rad about the vertical axis, 2.5 Hz), a yes/no question is a 0.12 rad forward tilt, a WH question is a 0.12 rad sideways tilt, each eased in and out over 0.3 s across the whole sentence. These values are assumptions chosen to be subtle, not taken from signer validated data, and real ISL non-manual markers also use eyebrows, eyes and mouth, which are not modelled. Code: `frontend/src/lib/avatar/nmm.ts`.
