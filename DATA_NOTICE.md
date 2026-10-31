# Data notice: INCLUDE dataset and derived material

This notice covers the third party data behind SignBridge. The MIT licence in `LICENSE` covers the original code only. It does not cover
INCLUDE or anything derived from INCLUDE.

## Source and citation

SignBridge uses the INCLUDE dataset of Indian Sign Language videos and the authors' train, validation and test lists.

- Paper: Advaith Sridhar, Rohith Gandhi Ganesan, Pratyush Kumar and Mitesh Khapra. "INCLUDE: A Large Scale Dataset for Indian Sign Language
  Recognition." Proceedings of the 28th ACM International Conference on Multimedia (ACM MM 2020). DOI 10.1145/3394171.3413528.
- Data: Zenodo record 4010759, https://zenodo.org/records/4010759
- Split lists: the AI4Bharat INCLUDE repository (`train_test_paths`), used exactly as published.

If you use anything in this repository that is derived from INCLUDE, cite the paper and the Zenodo record.

## Licence of INCLUDE, and the open question

- The Zenodo record metadata gives **CC BY 4.0**.
- A third party page about the dataset gives **CC BY-NC-SA 4.0**.

The two do not agree and the question is **unresolved**. This project does not try to settle it. It follows the stricter licence,
**CC BY-NC-SA 4.0** (https://creativecommons.org/licenses/by-nc-sa/4.0/):

- **Attribution:** give credit as above and say that changes were made.
- **NonCommercial:** no commercial use.
- **ShareAlike:** material you build from it is shared under the same licence.

This is a statement of how the project behaves, not legal advice. Anyone who needs certainty (for example for commercial use) should ask the
dataset authors.

## What in this repository is INCLUDE-derived

All of it is licensed **CC BY-NC-SA 4.0, non-commercial only**, with the attribution above:

1. **Eleven retargeted animation clips in git history.** `frontend/public/animations/` (bank, doctor, hello, hospital, i, market,
   thank-you, tomorrow, yesterday, you, plus `index.json`) was committed in `5450bb8` and removed from tracking in a later commit; the
   files remain in the earlier history. Each is an automatic retarget of one INCLUDE training sample, not signer reviewed.
2. **Statistics and listings computed from INCLUDE**, in `docs/evaluation/`: class counts, split integrity (including the authors' video
   paths that are missing from the archives), the label review, the pilot and final model metrics, and `results.md`.

Not in the repository, by design: the videos, the extracted landmark features, the trained model weights, any clip created after the
untracking commit, recorded takes, and the avatar. They are rebuilt locally (see the README) and are git-ignored (`data/`,
`backend/models/`, `frontend/public/animations/*.json`, `frontend/public/avatar/`). If you build them yourself, the same terms apply to
them as above.

## Avatar model (Mixamo)

The avatar model `signer.glb` is **not included** and must be downloaded by you from Mixamo under Mixamo's own terms, then converted with
`tools/avatar/`. The project has not confirmed those terms, so check them yourself before sharing anything that contains the model.

## Self-recorded signs

Signs recorded with the Record sign tab are your own material (landmarks only, no video). Check the consent of the person recorded before you
share them. They are not INCLUDE-derived unless you mix them with it.
