# Face block: with and without eyebrows, eyes and mouth

Authors' predefined split, signer independence not verified. INCLUDE v2 features (3121 train, 347 validation, 816 test samples). The face block is 50 MediaPipe Holistic face points (10 eyebrow, 12 eye, 28 mouth), normalized like the body (shoulder midpoint, shoulder width), appended to the 225 body features as a separate 150 value block (375 per frame). Same settings for both arms (epochs_max 60, patience 10, max_gap 3, batch 16, lr 0.001, seq_len 32, hidden 128, no augmentation), seeds 0, 1, 2. Mean ± sample SD over three independently trained models; difference taken seed by seed, 95 percent t-interval over the three differences. The without-face models are the three-seed baselines already reported in three_seed_results.md. No clip or sign is signer reviewed.

## Validation (used for every decision)

| Model | Metric | Without face | With face | Difference with face (95% interval) |
|---|---|---|---|---|
| cnn | macro-F1 | 0.9127 ± 0.0089 | 0.9194 ± 0.0153 | +0.0067 (-0.0264 to +0.0398), no clear change |
| cnn | top-1 | 0.9289 ± 0.0088 | 0.9337 ± 0.0144 | +0.0048 (-0.0305 to +0.0401), no clear change |
| bigru | macro-F1 | 0.8181 ± 0.0304 | 0.8328 ± 0.0058 | +0.0147 (-0.0492 to +0.0787), no clear change |
| bigru | top-1 | 0.8492 ± 0.0294 | 0.8569 ± 0.0120 | +0.0077 (-0.0451 to +0.0605), no clear change |
| transformer | macro-F1 | 0.6844 ± 0.0369 | 0.4586 ± 0.1698 | -0.2259 (-0.6772 to +0.2254), no clear change |
| transformer | top-1 | 0.7320 ± 0.0375 | 0.5130 ± 0.1706 | -0.2190 (-0.6916 to +0.2536), no clear change |

Per seed (validation macro-F1, without face then with face):

- cnn: seed 0 0.9039 to 0.9201, seed 1 0.9123 to 0.9038, seed 2 0.9217 to 0.9343
- bigru: seed 0 0.7832 to 0.8277, seed 1 0.8383 to 0.8390, seed 2 0.8328 to 0.8318
- transformer: seed 0 0.7128 to 0.5720, seed 1 0.6426 to 0.5402, seed 2 0.6979 to 0.2634

Parameters (seed 0): cnn 343558 to 439558, bigru 636422 to 751622, transformer 360710 to 379910. Epochs run (seeds 0, 1, 2): cnn [46, 51, 60] to [56, 48, 60]; bigru [38, 60, 47] to [48, 60, 60]; transformer [43, 39, 60] to [51, 55, 60].

