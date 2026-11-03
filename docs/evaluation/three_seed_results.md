# Three-seed results

Authors' predefined split, signer independence not verified. Seed 0 is the earlier training run; seeds 1 and 2 are the twelve additional models. Mean ± sample SD (n = 3) over independently trained models. Each model has its own validation-chosen threshold (lowest threshold with at least 95 percent accuracy on answered validation samples, offline). Browser conditions use the browser-path TEST corpus (312 videos, one evaluation per trained model); the offline column is the stored features of the same 312 videos, not the full 816-sample test split. Seeds are few: the SD is a rough indication, not an interval.

## Test corpus (312 videos), accuracy at the validation-chosen threshold

| Condition | base cnn | aug cnn | base bigru | aug bigru | base transformer | aug transformer |
|---|---|---|---|---|---|---|
| offline | 0.85 ± 0.03 | 0.80 ± 0.11 | 0.62 ± 0.10 | 0.70 ± 0.08 | 0.38 ± 0.08 | 0.30 ± 0.23 |
| br16x9 | 0.84 ± 0.05 | 0.78 ± 0.12 | 0.57 ± 0.11 | 0.64 ± 0.09 | 0.36 ± 0.07 | 0.29 ± 0.22 |
| br4x3 | 0.71 ± 0.05 | 0.67 ± 0.12 | 0.47 ± 0.08 | 0.54 ± 0.09 | 0.31 ± 0.06 | 0.25 ± 0.19 |
| br4x3_raw | 0.06 ± 0.02 | 0.62 ± 0.13 | 0.38 ± 0.07 | 0.51 ± 0.07 | 0.20 ± 0.05 | 0.22 ± 0.17 |
| wrong accepted, br16x9 | 0.04 ± 0.00 | 0.04 ± 0.03 | 0.02 ± 0.01 | 0.04 ± 0.01 | 0.04 ± 0.02 | 0.02 ± 0.01 |
| wrong accepted, br4x3 | 0.07 ± 0.01 | 0.09 ± 0.07 | 0.04 ± 0.02 | 0.04 ± 0.02 | 0.04 ± 0.02 | 0.02 ± 0.01 |
| wrong accepted, br4x3_raw | 0.41 ± 0.08 | 0.08 ± 0.06 | 0.03 ± 0.02 | 0.05 ± 0.03 | 0.05 ± 0.01 | 0.03 ± 0.02 |

## Validation corpus (211 videos), accuracy at the validation-chosen threshold

| Condition | base cnn | aug cnn | base bigru | aug bigru | base transformer | aug transformer |
|---|---|---|---|---|---|---|
| offline | 0.84 ± 0.04 | 0.78 ± 0.10 | 0.56 ± 0.11 | 0.68 ± 0.06 | 0.39 ± 0.09 | 0.29 ± 0.23 |
| br16x9 | 0.80 ± 0.04 | 0.73 ± 0.12 | 0.55 ± 0.11 | 0.63 ± 0.10 | 0.36 ± 0.10 | 0.27 ± 0.22 |
| br4x3 | 0.68 ± 0.06 | 0.62 ± 0.14 | 0.43 ± 0.06 | 0.53 ± 0.10 | 0.32 ± 0.10 | 0.25 ± 0.20 |
| br4x3_raw | 0.05 ± 0.00 | 0.58 ± 0.15 | 0.34 ± 0.09 | 0.51 ± 0.09 | 0.21 ± 0.06 | 0.22 ± 0.18 |
| wrong accepted, br16x9 | 0.04 ± 0.02 | 0.06 ± 0.04 | 0.03 ± 0.02 | 0.03 ± 0.01 | 0.03 ± 0.01 | 0.03 ± 0.02 |
| wrong accepted, br4x3 | 0.07 ± 0.01 | 0.08 ± 0.04 | 0.04 ± 0.00 | 0.06 ± 0.03 | 0.05 ± 0.02 | 0.03 ± 0.03 |
| wrong accepted, br4x3_raw | 0.44 ± 0.09 | 0.06 ± 0.05 | 0.05 ± 0.04 | 0.06 ± 0.03 | 0.06 ± 0.04 | 0.04 ± 0.05 |

## Per-model validation-chosen thresholds (seed 0, 1, 2)

- cnn_base: 0.7, 0.7, 0.7
- bigru_base: 0.9, 0.9, 0.9
- transformer_base: 0.95, 0.95, 0.95
- cnn_aug: 0.9, 0.5, 0.7
- bigru_aug: 0.7, 0.9, 0.9
- transformer_aug: 0.95, 0.95, 0.95

No threshold reached 95 percent accuracy on answered validation samples for: [('transformer_aug', 0), ('transformer_aug', 1), ('transformer_aug', 2)]; 0.95 was used for them.

## Gap and augmentation effect (test corpus, mean over seeds; per-seed values in three_seed_per_seed.json)

| Model | 16:9 minus 4:3 (rescaled) | per-seed |
|---|---|---|
| cnn_base | +0.13 | +0.13, +0.12, +0.15 |
| bigru_base | +0.10 | +0.07, +0.11, +0.13 |
| transformer_base | +0.05 | +0.08, +0.04, +0.05 |
| cnn_aug | +0.11 | +0.12, +0.13, +0.08 |
| bigru_aug | +0.10 | +0.11, +0.08, +0.13 |
| transformer_aug | +0.03 | +0.07, +0.00, +0.03 |

| Architecture | Condition | augmented minus baseline, mean | per-seed |
|---|---|---|---|
| cnn | offline | -0.05 | -0.14, +0.03, -0.05 |
| cnn | br16x9 | -0.06 | -0.14, +0.01, -0.05 |
| cnn | br4x3 | -0.04 | -0.13, -0.01, +0.01 |
| cnn | br4x3_raw | +0.57 | +0.43, +0.68, +0.59 |
| cnn | wrong accepted, br16x9 | +0.00 | -0.02, +0.04, -0.01 |
| bigru | offline | +0.09 | +0.29, -0.07, +0.04 |
| bigru | br16x9 | +0.07 | +0.30, -0.09, -0.00 |
| bigru | br4x3 | +0.07 | +0.26, -0.06, +0.00 |
| bigru | br4x3_raw | +0.13 | +0.27, +0.02, +0.08 |
| bigru | wrong accepted, br16x9 | +0.02 | +0.04, +0.00, +0.02 |
| transformer | offline | -0.08 | +0.11, -0.24, -0.09 |
| transformer | br16x9 | -0.07 | +0.08, -0.25, -0.04 |
| transformer | br4x3 | -0.05 | +0.09, -0.21, -0.03 |
| transformer | br4x3_raw | +0.03 | +0.15, -0.12, +0.05 |
| transformer | wrong accepted, br16x9 | -0.02 | -0.02, -0.02, -0.03 |
