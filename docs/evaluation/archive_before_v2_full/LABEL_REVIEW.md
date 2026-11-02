# INCLUDE label review (merge approved 2026-10-30)

Counts below come from the authors' split lists, so they are final regardless of how many videos the supplement run recovers.
Status: **approved by you: merge the 27 nested Extra videos into their parent classes; keep the three bracketed classes separate.**
The v2 manifest builder now merges by default and keeps each video's authors' split. Nothing is dropped. The first manifest is untouched.

## Finding that changes the earlier audit

The four "Extra" labels reported in the first audit were a labelling bug of mine, not four real classes. In the authors' data
the "Extra" folders are **nested inside a class folder**, for example `Animals/4. Bird/Extra/MVI_3042.MOV`. My first run took the
last folder name as the label, so these 27 videos were labelled "Extra". Training labels must come from the class folder (the
second path component). The extraction code now does this (`label_of`), and the first manifest is left as it was.

## 1. Nested "Extra" folders (27 videos, all in the authors' lists)

| Parent class | Nested folder | train | val | test | Total |
|---|---|---|---|---|---|
| Adjectives / 5. Beautiful | Extra | 0 | 1 | 0 | 1 |
| Adjectives / 79. short | extra | 1 | 0 | 0 | 1 |
| Adjectives / 84. small little | extra | 1 | 0 | 0 | 1 |
| Animals / 4. Bird | Extra | 3 | 2 | 0 | 5 |
| Places / 19. House | Extra | 1 | 0 | 0 | 1 |
| Places / 21. Train Station | Extra | 2 | 0 | 0 | 2 |
| Places / 23. Court | Extra | 2 | 1 | 0 | 3 |
| Places / 26. University | Extra | 0 | 1 | 0 | 1 |
| Places / 27. Park | Extra | 1 | 1 | 0 | 2 |
| Places / 28. Store or Shop | Extra | 2 | 0 | 0 | 2 |
| Places / 31. Temple | Extra | 1 | 0 | 0 | 1 |
| Places / 32. Market | Extra | 0 | 1 | 0 | 1 |
| Places / 33. India | Extra | 1 | 0 | 0 | 1 |
| Places / 34. Ground | Extra | 1 | 0 | 0 | 1 |
| Places / 35. Bank | Extra | 2 | 0 | 0 | 2 |
| Places / 36. Location | Extra | 2 | 0 | 0 | 2 |
| **Total** | | 20 | 7 | 0 | 27 |

Proposal: **merge each nested folder into its parent class**, keeping the authors' split for every video (so Bird gains 3 train
and 2 val videos, and so on). Reason: the path nests them under the class, and treating them as 16 new classes with 1 to 5 videos
each would create classes that cannot be learned or evaluated. Caveat I cannot verify: the authors do not say what "Extra"
means (spare takes, retakes, or rejects). Alternatives: (b) exclude all 27 and report that, (c) keep them as separate classes
(not recommended). Approved: merged into the parent class (policy merge). The separate policy remains available as an option.

## 2. Bracketed labels (genuine class folders, 43 videos)

| Folder in the lists | train | val | test | Total | Proposal |
|---|---|---|---|---|---|
| Pronouns / 46. you (plural) | 15 | 2 | 4 | 21 | Keep as its own class; gloss form YOU-PLURAL |
| Society / 8. Race (ethnicity) | 10 | 1 | 3 | 14 | Keep; gloss form RACE-ETHNICITY |
| Days_and_Time / Second (Number) | 6 | 1 | 1 | 8 | Keep as its own class; gloss form SECOND-NUMBER |

These are the authors' own class names, so they are not errors. "Second (Number)" is a different class from "81. Second" (the time
unit, 12 videos in the lists) and must not be merged with it. It is also the only class folder without a number prefix, which may explain the 8 videos
that the first run could not account for (to be confirmed by the supplement run). The brackets only matter for the gloss strings used by translation: proposal is to
convert labels to upper case with hyphens, dropping the brackets. Nothing is renamed in the manifest yet.

## 3. Class count

The record states 263 word signs. The final class count after the supplement run and after any approved merge will be reported
with the final audit. It is not asserted here.

## Decision

Approved: (1) merge the 27 nested "Extra" videos into their parent classes. (2) The three bracketed classes stay separate; their
gloss strings (YOU-PLURAL, RACE-ETHNICITY, SECOND-NUMBER) are applied when labels are converted to glosses in Phase 3, not in the
manifest.
