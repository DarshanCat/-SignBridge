# Three-seed results

Authors' predefined split, signer independence not verified. Seed 0 is the earlier training run; seeds 1 and 2 are the twelve additional models. Mean ± sample SD over three independently trained models. Each model has its own validation-chosen threshold (lowest threshold with at least 95 percent accuracy on answered validation samples, offline). Browser conditions use the browser-path TEST corpus (312 videos, one evaluation per trained model); the offline column is the stored features of the same 312 videos, not the full 816-sample test split. Three seeds are few: the SD is a rough indication, not an interval.

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

## Gap and augmentation effect (test corpus)

16:9 minus rescaled 4:3 accuracy, per seed:

| Model | 16:9 minus 4:3 (mean) | per-seed |
|---|---|---|
| cnn_base | +0.13 | +0.13, +0.12, +0.15 |
| cnn_aug | +0.11 | +0.12, +0.13, +0.08 |
| bigru_base | +0.10 | +0.07, +0.11, +0.13 |
| bigru_aug | +0.10 | +0.11, +0.08, +0.13 |
| transformer_base | +0.05 | +0.08, +0.04, +0.05 |
| transformer_aug | +0.03 | +0.07, +0.00, +0.03 |

Change of the 16:9 minus 4:3 gap (augmented minus baseline), cnn: -0.02 (-0.12 to +0.09) no clear change  
Change of the 16:9 minus 4:3 gap (augmented minus baseline), bigru: +0.00 (-0.09 to +0.09) no clear change  
Change of the 16:9 minus 4:3 gap (augmented minus baseline), transformer: -0.02 (-0.06 to +0.02) no clear change  

Augmented minus baseline, taken seed by seed; interval = 95 percent t-interval over the three differences (an interval that contains zero is written "no clear change").

| Architecture | Condition | accuracy at threshold | top-1 (no threshold) | per-seed accuracy differences |
|---|---|---|---|---|
| cnn | offline | -0.05 (-0.26 to +0.16) no clear change | -0.02 (-0.07 to +0.04) no clear change | -0.14, +0.03, -0.05 |
| cnn | br16x9 | -0.06 (-0.25 to +0.13) no clear change | -0.00 (-0.08 to +0.07) no clear change | -0.14, +0.01, -0.05 |
| cnn | br4x3 | -0.04 (-0.23 to +0.15) no clear change | -0.03 (-0.15 to +0.09) no clear change | -0.13, -0.01, +0.01 |
| cnn | br4x3_raw | +0.57 (+0.26 to +0.88) | +0.67 (+0.62 to +0.72) | +0.43, +0.68, +0.59 |
| cnn | wrong accepted, br16x9 | +0.00 (-0.06 to +0.07) no clear change | | -0.02, +0.04, -0.01 |
| bigru | offline | +0.09 (-0.36 to +0.54) no clear change | +0.02 (-0.12 to +0.16) no clear change | +0.29, -0.07, +0.04 |
| bigru | br16x9 | +0.07 (-0.44 to +0.58) no clear change | +0.02 (-0.06 to +0.10) no clear change | +0.30, -0.09, -0.00 |
| bigru | br4x3 | +0.07 (-0.35 to +0.49) no clear change | +0.04 (-0.04 to +0.11) no clear change | +0.26, -0.06, +0.00 |
| bigru | br4x3_raw | +0.13 (-0.19 to +0.44) no clear change | +0.12 (+0.01 to +0.23) | +0.27, +0.02, +0.08 |
| bigru | wrong accepted, br16x9 | +0.02 (-0.04 to +0.08) no clear change | | +0.04, +0.00, +0.02 |
| transformer | offline | -0.08 (-0.51 to +0.36) no clear change | -0.09 (-0.55 to +0.36) no clear change | +0.11, -0.24, -0.09 |
| transformer | br16x9 | -0.07 (-0.49 to +0.35) no clear change | -0.06 (-0.50 to +0.38) no clear change | +0.08, -0.25, -0.04 |
| transformer | br4x3 | -0.05 (-0.43 to +0.33) no clear change | -0.06 (-0.47 to +0.35) no clear change | +0.09, -0.21, -0.03 |
| transformer | br4x3_raw | +0.03 (-0.30 to +0.36) no clear change | +0.02 (-0.43 to +0.48) no clear change | +0.15, -0.12, +0.05 |
| transformer | wrong accepted, br16x9 | -0.02 (-0.04 to +0.00) no clear change | | -0.02, -0.02, -0.03 |

## Seed 0 only: validation sweeps, accuracy baseline to augmented (not run for seeds 1 and 2)

| Architecture | y scale 0.9 | y scale 1.25 | noise 0.01 | dropout 0.2 |
|---|---|---|---|---|
| cnn | 0.45 to 0.60 | 0.34 to 0.57 | 0.68 to 0.59 | 0.71 to 0.53 |
| bigru | 0.41 to 0.73 | 0.32 to 0.71 | 0.41 to 0.76 | 0.32 to 0.70 |
| transformer | 0.36 to 0.44 | 0.32 to 0.45 | 0.35 to 0.42 | 0.33 to 0.38 |

## Seed 0 only: threshold trade-off (coverage / accuracy on answered)

| Threshold | baseline CNN, browser 16:9, 312 test videos | augmented CNN, offline, 816 test samples |
|---|---|---|
| 0 | 1.0000 / 0.8686 | 1.0000 / 0.9056 |
| 0.3 | 0.9936 / 0.8742 | 0.9988 / 0.9067 |
| 0.5 | 0.9359 / 0.9075 | 0.9559 / 0.9256 |
| 0.7 | 0.8205 / 0.9531 | 0.8775 / 0.9483 |
| 0.8 | 0.7788 / 0.9588 | 0.8248 / 0.9614 |
| 0.9 | 0.7051 / 0.9682 | 0.7304 / 0.9681 |
| 0.95 | 0.6090 / 0.9684 | 0.6299 / 0.9786 |
