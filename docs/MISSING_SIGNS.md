# Signs without a clip

Generated from `backend/config/gloss_dictionary.json` and `backend/config/sign_registry.json` on 2026-10-31.

Every clip that exists is an automatic retarget of one INCLUDE training sample (the one with the fewest frames without a hand) and is marked
`not_signer_reviewed`. 262 glosses have such a clip. The glosses below have none; text to gloss can still produce them and the English to
Sign panel shows "no clip for X" instead of inventing one.

## Status of your own recordings (2026-10-31)

No recordings exist yet: `data/recorded/` has not been created, the backend log shows no `/api/record/sign` request, and no
`signbridge_check_*` download was found. So nothing was promoted and the coverage below is unchanged (262 glosses with a clip, 51 without).
After recording, promote the best take per sign with `python -m retarget.promote --clip ..\data\recorded\<GLOSS>\<stamp>.clip.json`
(add `--replace` only to overwrite an existing clip); this list will be regenerated then.

Current results for the three example sentences (262 clips):

| Sentence | Gloss | Plays | No clip |
|---|---|---|---|
| Where is the hospital? | HOSPITAL WHERE | HOSPITAL | WHERE |
| I went to the hospital yesterday | YESTERDAY I HOSPITAL GO | YESTERDAY, I, HOSPITAL | GO |
| I do not like the hospital | I HOSPITAL LIKE NOT | I, HOSPITAL | LIKE, NOT |

The words that would complete these sentences are WHERE, GO, LIKE and NOT, all in the list of 50 grammar words below.

## INCLUDE class without data (1)

- SECOND-NUMBER: the authors' lists name a class folder `Second (Number)` that does not exist in the released archives (8 listed videos
  missing, see the dataset audit). Record it with the Record sign tab if it is needed.

## Grammar words that are not INCLUDE classes (50)

ALL, BEFORE, BUT, BUY, CAN, COME, DRINK, EAT, FOOD, GIVE, GO, HAVE, HELP, HOME, HOW, KNOW, LAST, LIKE, LIVE, LOVE, MEET, MUST, NAME, NEED, NEXT,
NO, NOT, NOW, OR, PLEASE, READ, SEE, SLEEP, STAY, STUDY, TAKE, THIS, TONIGHT, WALK, WANT, WATER, WHAT, WHEN, WHERE, WHICH, WHO, WHY, WORK, WRITE, YES.

These are in the dictionary as `grammar_placeholder` entries (marked unvalidated in `docs/NLP.md`): the rules need them (negation NOT, question
words, modals) but INCLUDE has no matching class. They need a signer to record or review them (Record sign tab, then `python -m
retarget.promote`).

## Not available at all

Fingerspelling: no `FS-<letter>` clips exist, so any word the dictionary does not know is shown as "no clip for FS:WORD".
