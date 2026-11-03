# Padding test (validation, 100 videos)

Python MediaPipe on the sampled frames, baseline CNN (seed 0), threshold 0.7, vertical rescale to 16:9 for every picture that is not 16:9. Authors' predefined split, signer independence not verified. Validation videos only; no test video is used. Intervals are 95 percent Wilson; the paired test is the exact McNemar test (exact binomial test on the discordant videos).

| Condition | Accuracy | 95% interval | Wrong accepted | Unrecognized | Top-1 | Frames with a hand |
|---|---|---|---|---|---|---|
| native16x9 | 0.77 | 0.68 to 0.84 | 0.02 | 0.21 | 0.86 | 0.85 |
| small16x9 | 0.72 | 0.63 to 0.80 | 0.04 | 0.24 | 0.86 | 0.85 |
| lb4x3_black | 0.59 | 0.49 to 0.68 | 0.06 | 0.35 | 0.71 | 0.84 |
| lb4x3_edge | 0.73 | 0.64 to 0.81 | 0.05 | 0.22 | 0.82 | 0.84 |
| lb1x1_black | 0.61 | 0.51 to 0.70 | 0.07 | 0.32 | 0.73 | 0.84 |
| crop4x3 | 0.68 | 0.58 to 0.76 | 0.06 | 0.26 | 0.83 | 0.84 |

| Pair (first minus second) | first only right | second only right | exact McNemar p |
|---|---|---|---|
| native16x9 minus small16x9 | 7 | 2 | 0.180 |
| native16x9 minus lb4x3_black | 19 | 1 | 0.000 |
| small16x9 minus lb4x3_black | 18 | 5 | 0.011 |
| lb4x3_edge minus lb4x3_black | 19 | 5 | 0.007 |
| native16x9 minus lb4x3_edge | 5 | 1 | 0.219 |
| small16x9 minus lb4x3_edge | 3 | 4 | 1.000 |
| lb1x1_black minus lb4x3_black | 4 | 2 | 0.688 |
| native16x9 minus crop4x3 | 10 | 1 | 0.012 |
| lb4x3_edge minus crop4x3 | 9 | 4 | 0.267 |
