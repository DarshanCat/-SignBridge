# ISL-CSLTR continuous sentence test: results

Protocol: `ISL_CSLRT_PROTOCOL.md`, written and committed before the first video was fetched. One pass of the live model (1D CNN, 262 classes, trained on the authors' predefined split of INCLUDE v2, validation-chosen threshold 0.7) and of the live segmenter over 235 of 235 selected videos of the ISL-CSLTR corpus (79 sentences that contain at least one corpus gloss that is a class of the model, first three videos of each folder). Authors' predefined split, signer independence not verified: this is a different dataset, no signer IDs exist for either. This is one test use of the live model on external data and is on the disclosure list. The reference glosses are the corpus authors', not checked by a signer of this project. Nothing was tuned on this data and nothing was changed after seeing the results.

The selection rule gave 235 videos, not the 232 written in the protocol: the folder `which collegeschool are you from` (3 videos) matches its sentence once spaces are ignored, which the protocol's count had missed. Extraction transferred 3.71 GB (the range reader fetches 4 MB blocks, so more than the 2.75 GB of the selected files); every video was deleted after its landmarks were extracted.

## Results

- **Segmentation.** The live segmenter found exactly one segment in 231 of 235 videos (median 1 segment against a median of 3 corpus gloss tokens per sentence). Segment count is within one of the gloss count in 14.5 percent of the videos; Spearman correlation between the two counts 0.05. The likely reason (not checked frame by frame) is that the signs of a sentence run into each other without the rest between them that the segmenter looks for, so the sentence ends up as one segment.
- **Recall of covered signs.** 0 of 334 covered gloss tokens appear among the answers (0.0 percent).
- **Answer rate.** 99 of 237 segments were answered at the threshold (41.8 percent); the rest are UNRECOGNIZED.
- **Answer precision against the corpus glosses.** 0 of 99 answers are one of the glosses of their sentence; all 99 are wrong. small files: 34 wrong of 34 answered, 56 segments; camera files: 65 wrong of 65 answered, 181 segments. The most frequent wrong answers: HOSPITAL (33), GRANDMOTHER (10), POCKET (9), MEDICINE (8), WIDE (6), BATHROOM (4).
- **The two fully covered sentences** (you are bad, you are good): 0 of 6 videos exactly right. Too few to be a score.

Reading: the model was trained on isolated signs and answers a whole sentence video (median 48 usable frames at every second frame) with one class, with a confidence that passes the threshold in about 4 of 10 cases, and it never named a sign that is in the sentence. This measures what the live pipeline does with continuous, differently recorded signing; it is not a finding about unseen signers of INCLUDE. It also shows the open vocabulary error: signs outside the 262 classes are answered with some class instead of UNRECOGNIZED.

## English to gloss against the corpus glosses (no video, `nlp.score_generation`)

101 sentences. Exact match 0.030, gloss word error rate 0.782, bag of gloss tokens F1 0.508, BLEU-4 2.5. Gloss to English from the corpus glosses back to the sentence: exact match 0.000, BLEU-4 18.9. The rule based gloss puts time signs first and drops function words in its own way, while the corpus glosses keep English word order and write different spellings (DONOT, FS:WORD); the numbers measure agreement with that convention, not whether either is right ISL.

