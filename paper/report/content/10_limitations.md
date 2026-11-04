# Limitations and Future Work

## Limitations

This section states the limits of the work with the same honesty as the accompanying paper.

- **Authors' predefined split, signer independence not verified.** INCLUDE has no signer identifiers, so the same person may appear in training and test. Every accuracy in this report is therefore probably optimistic for a new signer, and the deployment gap measured here is a lower bound on the gap for people unseen in training.
- **No face features.** Only pose and hands are tracked. Facial expression carries grammatical information in Indian Sign Language, for example for questions and negation. The recognizer cannot use it and the avatar does not animate a face. The head movements for negation and questions are rule-based approximations that are not taken from signer-validated data.
- **Clips are not signer-reviewed.** All 262 clips are automatic retargets of one training sample each, with an approximate bone mapping and no recovered forearm roll or finger spread. No clip has been reviewed by a signer, the backend registry marks none as verified (an unsupported review claim for the WATER clip was found in a later commit and removed, Section 10.2), and some will look wrong or unnatural. The system is not an interpreting service.
- **Rules are assumptions.** The text to gloss rules and the gloss to English heuristics are simplified assumptions for single-clause sentences that no ISL signer or linguist has validated.
- **Vocabulary.** The recognizer knows 262 INCLUDE classes. Fifty grammar words (NOT, WHAT, WHERE, GO, HELP, YES, NO and others) can be typed and signed only if a clip exists; they have no recognition data and no clip, and fingerspelling clips do not exist. In total 262 of 313 dictionary glosses have a clip.
- **Real webcams are unmeasured.** The browser results use dataset videos re-encoded as pictures. No real webcam, real lighting, real user or left-handed signer is included, and the framing study covers only sizes up to the dataset range.
- **Residual 4:3 loss.** The loss that remains in 4:3 pictures after the exact rescale is not explained by vertical scale, signer size or resolution. A validation test (100 videos, Python landmarks) traces most of it to the black bars of the letterboxed benchmark pictures (0.59 with black bars, 0.73 with edge-filled bars, 0.77 native). The unpadded crop is confounded by signer size, the test was not repeated with browser landmarks, and a real 4:3 webcam has no bars, so the loss on real cameras is unmeasured.
- **Small samples.** One sample per class gives wide intervals (about plus or minus 9 points for 100 videos), many classes have only a few test samples, and the single-seed CNN study has no estimate of training variance.
- **Continuous signing.** Signs signed back to back without a pause cannot be separated, the pauses in the tests are synthetic, and the segmented accuracy is a few points below the isolated accuracy.
- **Licence.** The INCLUDE licence is stated inconsistently (CC BY 4.0 in the Zenodo record, CC BY-NC-SA 4.0 on a third-party page). The project follows the stricter reading: INCLUDE-derived material is non-commercial only, with attribution. Eleven early clips remain in the git history. The terms of the Mixamo avatar are unconfirmed, so the avatar file is not distributed and a public deployment should not include it until they are confirmed.
- **Not deployed.** The Vercel and Hugging Face deployments were prepared and the container was tested locally, but nothing was deployed, and the download of assets from a private repository was not tested against a real repository.

## Problems found in commits made outside the project sessions

Commits made after the measurements of this report (by the repository owner's git identity, outside the sessions that wrote the rest of the history) added Next.js route handlers under `frontend/src/app/api` as a fallback for a Vercel deployment. They were reviewed on 3 November 2026 (`docs/COMMIT_REVIEW_2026-11-03.md`).

- **A fake fallback was found and removed.** The route `/api/signs/recognize` did not run the recognition model. When its call to an external Hugging Face Space failed (and that call sent a label, not the landmarks), it returned the label of the request or a fixed "Hello" with a confidence of 0.94 and marked it as accepted, and for frames without hands it returned a confidence of 0.12 with made-up alternatives. This violated the rule of the project never to invent a prediction. The route now forwards the landmark frames to the real API and, on any failure, returns an error with no label, confidence or alternatives; the client shows that as an error. Eighteen tests cover each failure mode and check that no prediction field is present. The route was never used for any result in this report.
- **The related problems were fixed.** The routes `/api/health` and `/api/model/status` always answered healthy and loaded, and the client fell back to them when the real backend was unreachable, so the status panel could show a backend and a model that were not checked; they now proxy the real backend and answer with an error when it does not answer. The registry entry and the clip file for WATER claimed a signer review that did not happen (WATER is not an INCLUDE class and the origin of that clip is not documented); the claim was removed, a test now fails if the shipped registry claims any review, and the clip is listed as unreviewed with an undocumented origin. The registry and plan routes now count a clip only if its file exists, and an untested TypeScript copy of the text to gloss rules was removed so that there is a single implementation of the rules.
- **A clip was added to git and has been untracked.** `water.json` was committed although clip files stay out of git; it was removed from the index and is covered by `.gitignore`, but it remains in the history of that commit.

## Test-split disclosure

The test split was used as follows; every use known to the author is listed.

1. The three baseline models (seed 0) were each evaluated once on the full test split (816 samples) to produce the table of Section 9.1. The earlier pilot runs used the validation split of a partial manifest only and never read test features.
2. The segmentation study of Section 9.5 evaluated streams of test samples once per rest-gap setting (three settings) after tuning on validation.
3. The browser-path benchmark of the baseline CNN on 100 test videos (Section 9.3) is a further use. It followed three end-to-end fake-camera runs on three INCLUDE test videos ([[tab:fake]]), whose wrong results first exposed the picture aspect problem. The rescale was therefore designed after seeing test videos, although it was derived from the geometry and its size was not tuned on test data.
4. After the resampling routine was vectorized for speed, the baseline CNN was run over the test split once to confirm that its accuracy was unchanged.
5. Each of the three augmented models (seed 0) was evaluated once on the full test split at the end of its training run, and the six seed-0 models were evaluated once on the 312 test videos of the larger browser corpus. The twelve additional models of seeds 1 and 2 were evaluated in the same way once each on the full test split and once each on the 312 browser-corpus test videos (eighteen browser-corpus evaluations in all). The padding test, the per-sign analysis and the calibration check used validation videos only.

No augmentation range, threshold or model choice was tuned on the test split. They were chosen on validation data.

## Future work

- **Record signers with identifiers on real webcams.** The recorder and the training plan are ready (signer roles S01 to S03 for training, S04 for validation and S05 for test). This is the only way to measure signer independence and the webcam gap directly, and to retrain with webcam data.
- **Review the clips and the rules with Deaf signers and ISL linguists**, and replace the rules and clips that they reject.
- **Add facial and non-manual features** to the recognizer and animate the face of the avatar.
- **Repeat the padding test with browser landmarks and real 4:3 webcam recordings**, test the larger signer sizes with real recordings, and study cameras that are not 16:9 or 4:3.
- **Extend the vocabulary** with the 50 grammar words recorded by signers and with fingerspelling.
- **Improve continuous recognition** for signs that follow each other without a pause, with real streams instead of synthetic pauses.
- **Deploy** after the placeholder route has been removed, the avatar terms have been confirmed and the asset download has been tested.
