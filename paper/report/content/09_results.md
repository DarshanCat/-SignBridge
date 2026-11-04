# Results

All numbers in this chapter come from `docs/evaluation` and are on the authors' predefined split of INCLUDE, signer independence not verified. The three-seed numbers are read at each build from `docs/evaluation/three_seed_summary.json`, which `tools/browser_path/three_seed.py` writes from the per-video result files.

## Model comparison

The three models were trained with identical settings and each was evaluated once on the test split (816 samples, 262 classes). The 1D CNN is clearly the best and is the model used live.

Table: Test results of the baseline models (seed 0). {#tab:modelresults}
| Model | Epochs run | Validation macro-F1 | Test top-1 | Test top-5 | Test macro-F1 | Macro precision | Macro recall |
|---|---|---|---|---|---|---|---|
| 1D CNN | {{j:seed0_model_metrics.json:baseline_cnn.hyperparameters.epochs_run}} | {{j:seed0_model_metrics.json:baseline_cnn.val.macro_f1:.4f}} | {{j:seed0_model_metrics.json:baseline_cnn.test.top1_accuracy:.4f}} | {{j:seed0_model_metrics.json:baseline_cnn.test.top5_accuracy:.4f}} | {{j:seed0_model_metrics.json:baseline_cnn.test.macro_f1:.4f}} | {{j:seed0_model_metrics.json:baseline_cnn.test.macro_precision:.4f}} | {{j:seed0_model_metrics.json:baseline_cnn.test.macro_recall:.4f}} |
| BiGRU | {{j:seed0_model_metrics.json:baseline_bigru.hyperparameters.epochs_run}} | {{j:seed0_model_metrics.json:baseline_bigru.val.macro_f1:.4f}} | {{j:seed0_model_metrics.json:baseline_bigru.test.top1_accuracy:.4f}} | {{j:seed0_model_metrics.json:baseline_bigru.test.top5_accuracy:.4f}} | {{j:seed0_model_metrics.json:baseline_bigru.test.macro_f1:.4f}} | {{j:seed0_model_metrics.json:baseline_bigru.test.macro_precision:.4f}} | {{j:seed0_model_metrics.json:baseline_bigru.test.macro_recall:.4f}} |
| Transformer | {{j:seed0_model_metrics.json:baseline_transformer.hyperparameters.epochs_run}} | {{j:seed0_model_metrics.json:baseline_transformer.val.macro_f1:.4f}} | {{j:seed0_model_metrics.json:baseline_transformer.test.top1_accuracy:.4f}} | {{j:seed0_model_metrics.json:baseline_transformer.test.top5_accuracy:.4f}} | {{j:seed0_model_metrics.json:baseline_transformer.test.macro_f1:.4f}} | {{j:seed0_model_metrics.json:baseline_transformer.test.macro_precision:.4f}} | {{j:seed0_model_metrics.json:baseline_transformer.test.macro_recall:.4f}} |

![Test results of the three baseline models.](figures/chart_model_comparison.png){#fig:models w=5.6}

For the 1D CNN, 212 of the 262 classes are classified perfectly on the test split, but many classes have only one to four test samples, so per-class accuracies are very coarse: the lowest are Afternoon, Bill and Sunday (0 of 1, 0 of 3 and 0 of 1 samples) and Blue, Brother and Husband (one of four each). [[fig:confpairs]] and [[fig:confheat]] show the most frequent confusions. They are pairs that are close in meaning or in form, such as Brother and Sister, Husband and Wife, Boat and Fish, and I and you. These counts are small (two or three samples each), so they illustrate the kind of error and should not be ranked.

![The most frequent confusions of the 1D CNN on the test split.](figures/chart_confusions_top_pairs.png){#fig:confpairs w=5.6}

![Confusion matrix restricted to the 14 classes with the most errors (1D CNN, test split).](figures/chart_confusion_heatmap.png){#fig:confheat w=5.2}

## Threshold trade-off

A prediction whose top confidence is below the threshold is reported as UNRECOGNIZED, which trades coverage for accuracy. [[tab:threshold]] gives the test-split trade-off at three thresholds and [[fig:thr]] shows the curves for all of them. The live threshold of 0.7 was chosen on the validation split of the CNN (at least 95 percent accuracy on answered samples). On the test split it answers 0.8676 of the samples with an accuracy of 0.9548 on the answered ones.

Table: Coverage and accuracy on answered samples against the confidence threshold (test split, baseline models, seed 0). {#tab:threshold}
| Model | Threshold 0.5 (coverage, accuracy) | Threshold 0.7 (coverage, accuracy) | Threshold 0.9 (coverage, accuracy) |
|---|---|---|---|
| 1D CNN | {{j:seed0_model_metrics.json:baseline_cnn.test.accuracy_vs_coverage.2.coverage:.4f}}, {{j:seed0_model_metrics.json:baseline_cnn.test.accuracy_vs_coverage.2.accuracy_on_answered:.4f}} | {{j:seed0_model_metrics.json:baseline_cnn.test.accuracy_vs_coverage.3.coverage:.4f}}, {{j:seed0_model_metrics.json:baseline_cnn.test.accuracy_vs_coverage.3.accuracy_on_answered:.4f}} | {{j:seed0_model_metrics.json:baseline_cnn.test.accuracy_vs_coverage.5.coverage:.4f}}, {{j:seed0_model_metrics.json:baseline_cnn.test.accuracy_vs_coverage.5.accuracy_on_answered:.4f}} |
| BiGRU | {{j:seed0_model_metrics.json:baseline_bigru.test.accuracy_vs_coverage.2.coverage:.4f}}, {{j:seed0_model_metrics.json:baseline_bigru.test.accuracy_vs_coverage.2.accuracy_on_answered:.4f}} | {{j:seed0_model_metrics.json:baseline_bigru.test.accuracy_vs_coverage.3.coverage:.4f}}, {{j:seed0_model_metrics.json:baseline_bigru.test.accuracy_vs_coverage.3.accuracy_on_answered:.4f}} | {{j:seed0_model_metrics.json:baseline_bigru.test.accuracy_vs_coverage.5.coverage:.4f}}, {{j:seed0_model_metrics.json:baseline_bigru.test.accuracy_vs_coverage.5.accuracy_on_answered:.4f}} |
| Transformer | {{j:seed0_model_metrics.json:baseline_transformer.test.accuracy_vs_coverage.2.coverage:.4f}}, {{j:seed0_model_metrics.json:baseline_transformer.test.accuracy_vs_coverage.2.accuracy_on_answered:.4f}} | {{j:seed0_model_metrics.json:baseline_transformer.test.accuracy_vs_coverage.3.coverage:.4f}}, {{j:seed0_model_metrics.json:baseline_transformer.test.accuracy_vs_coverage.3.accuracy_on_answered:.4f}} | {{j:seed0_model_metrics.json:baseline_transformer.test.accuracy_vs_coverage.5.coverage:.4f}}, {{j:seed0_model_metrics.json:baseline_transformer.test.accuracy_vs_coverage.5.accuracy_on_answered:.4f}} |

![Accuracy against coverage (left) and coverage against the threshold (right) for the three baseline models on the test split. The mark 0.7 is the live threshold.](figures/chart_threshold_curves.png){#fig:thr w=6.2}

## Deployment-gap results

### Browser path against the offline path

To measure what a deployment changes, 100 test videos (one per class, drawn with a fixed seed from the test samples whose video is available) were passed through the real in-browser MediaPipe frame by frame, in 16:9 (1280 x 720) and in 4:3 (letterboxed into 640 x 480), and classified with the live code path by the 1D CNN. Accuracy is the share of videos answered above the threshold and correctly; wrong accepted is answered above the threshold and wrongly; the rest is UNRECOGNIZED. Intervals are 95 percent Wilson intervals; paired comparisons use the exact McNemar test.

Table: The 1D CNN on 100 test videos at threshold 0.7. {#tab:bvo}
| Source | Accuracy | 95 percent interval | Wrong accepted | Unrecognized | Top-1 |
|---|---|---|---|---|---|
| Offline features | 0.82 | 0.73 to 0.88 | 0.03 | 0.15 | 0.92 |
| Python MediaPipe, 16:9 | 0.81 | 0.72 to 0.87 | 0.03 | 0.16 | 0.90 |
| Browser, 16:9 | 0.78 | 0.69 to 0.85 | 0.02 | 0.20 | 0.87 |
| Python MediaPipe, 4:3 | 0.70 | 0.60 to 0.78 | 0.05 | 0.25 | 0.81 |
| Browser, 4:3 with the vertical rescale | 0.65 | 0.55 to 0.74 | 0.07 | 0.28 | 0.78 |
| Python MediaPipe, 4:3 without the rescale | 0.08 | not computed | 0.29 | 0.63 | 0.12 |
| Browser, 4:3 without the rescale | 0.07 | not computed | 0.29 | 0.64 | 0.10 |

![The 1D CNN on 100 test videos at threshold 0.7: correct-and-accepted share with 95 percent Wilson intervals and wrong-and-accepted share, offline and in the browser path.](figures/chart_browser_vs_offline.png){#fig:bvo w=5.4}

The results lead to four findings. In native 16:9 the browser path is within noise of the offline path (0.78 against 0.82; 6 videos lost and 2 gained, exact McNemar p = 0.29). In 4:3 the loss is large (0.65; 22 videos lost and 5 gained, p = 0.002) and wrong answers increase from 0.03 to 0.07. On identical frames the browser is 3 to 5 points below Python MediaPipe, which is not significant at this sample size, so the extractor is a minor contributor and the picture is the major one. Without the vertical rescale, 4:3 input gives 0.07 accuracy with 29 percent confident wrong answers: the model fails by answering wrongly, not by hesitating. A 16:9 picture resized to 640 x 360 gives 0.80 and a centre crop of the 16:9 frame to 4:3 (a webcam-like fill) with the rescale gives 0.76.

The loss that remains in 4:3 after the exact rescale (0.65 against 0.78 in 16:9 on the test videos, 0.58 against 0.75 on the validation videos) is **not explained** by vertical scale, signer size or resolution. It is not a vertical scale error, because the rescale is exact. It is not signer size, because letterboxing keeps the picture width. It is not resolution, because the smaller 16:9 picture scores 0.80. A padding test on the 100 validation videos (Python MediaPipe, baseline CNN, threshold 0.7) points to the black bars of the letterbox: black bars give 0.59, the same picture with the bars filled by replicated edge pixels gives 0.73 (exact McNemar test against the black bars, p = 0.007), a native 16:9 picture gives 0.77 and a 16:9 picture of the same 640 by 360 resolution gives 0.72. An unpadded 4:3 centre crop scores 0.68 but enlarges the signer and cuts the sides, so it cannot separate those factors from padding. The test used Python landmarks only, and a real 4:3 webcam has no bars, so the loss on real cameras is unmeasured (`docs/evaluation/padding_test_val.md`).

### Vertical scale, noise and hand dropout

Controlled perturbations were applied to the browser landmarks of 100 validation videos ([[fig:yscale]] and [[tab:sweep]]). Without a perturbation the CNN scores 0.75 in 16:9 and 0.58 in 4:3. A vertical scale error of 10 percent lowers the 16:9 accuracy to 0.43 (factor 0.9) or 0.65 (factor 1.1); an error of 25 percent leaves 0.26 with 36 percent wrong answers, and a factor of 0.75, which is exactly what an unrescaled 4:3 camera produces, leaves 0.05. The model is therefore very sensitive to a cue that normalization by shoulder width cannot remove. Noise and hand dropout cost accuracy gradually, whereas vertical scale is a cliff.

![The 1D CNN against a vertical scale error applied to browser landmarks of 100 validation videos. The shaded band is the range of the augmentation.](figures/chart_yscale.png){#fig:yscale w=5.4}

Table: The 1D CNN on browser 16:9 landmarks of 100 validation videos with added noise or removed hands, threshold 0.7. {#tab:sweep}
| Noise (picture fraction) | Accuracy | Wrong accepted | Hand dropout (share of frames) | Accuracy | Wrong accepted |
|---|---|---|---|---|---|
| 0.002 | 0.74 | 0.02 | 0.1 | 0.77 | 0.02 |
| 0.005 | 0.72 | 0.03 | 0.2 | 0.69 | 0.04 |
| 0.01 | 0.70 | 0.06 | 0.4 | 0.55 | 0.09 |
| 0.02 | 0.44 | 0.11 | 0.6 | 0.30 | 0.16 |

### Signer size in the picture

Thirty validation videos were shrunk toward the centre of the picture and classified with Python MediaPipe, binned by the median shoulder width as a fraction of the picture width ([[tab:framing]] and [[fig:framing]]). INCLUDE signers measure 0.116 to 0.149 (median 0.133). Accuracy is 0.89 for widths of 0.13 to 0.17 and 0.83 for 0.10 to 0.13, falls to 0.71 for 0.08 to 0.10 and to 0.59 and 0.50 below 0.08, where 12 to 14 percent of the answers are confidently wrong. At 30 percent of the size no body pose was found. The application therefore warns when the smoothed shoulder width falls below 0.10.

Table: The 1D CNN by shoulder width, validation videos shrunk toward the centre (Python MediaPipe, threshold 0.7). {#tab:framing}
| Shoulder width (fraction of picture width) | Accuracy | Wrong accepted | Video and size pairs |
|---|---|---|---|
| 0.04 to 0.06 | 0.50 | 0.14 | 14 |
| 0.06 to 0.08 | 0.59 | 0.12 | 32 |
| 0.08 to 0.10 | 0.71 | 0.00 | 14 |
| 0.10 to 0.13 | 0.83 | 0.00 | 12 |
| 0.13 to 0.17 | 0.89 | 0.00 | 18 |

![The 1D CNN against the median shoulder width, validation videos shrunk toward the centre. The dotted line is the warning threshold of the application.](figures/chart_framing.png){#fig:framing w=5.4}

Larger signers could not be tested by cropping. The same 30 videos were cropped toward the signer to 75, 60 and 50 percent of the picture (median shoulder widths 0.175, 0.216 and 0.259). Accuracy fell to 0.30, 0.37 and 0.43, but a hand was found in only 63, 36 and 33 percent of the frames against about 87 percent uncropped, because the crop cuts the signing space off. Size and lost hands cannot be separated this way, so sizes above 0.15 remain untested, and the framing guide of the application was therefore placed inside the tested range, with the shoulders at about 14 percent of the picture width.

## Augmentation

The measurements above fixed the augmentation of Section 7.2: a vertical scale from 0.85 to 1.20, landmark noise up to 0.01 of the picture size and hand dropout up to 0.2. The three architectures were retrained with identical settings and the augmentation added, for one seed (seed 0), and each was evaluated once on the test split.

Table: Test results of the baseline and augmented models, single seed (seed 0). Differences between single runs are not separated from training variance. {#tab:augseed0}
| Model | Top-1 baseline | Top-1 augmented | Macro-F1 baseline | Macro-F1 augmented |
|---|---|---|---|---|
| 1D CNN | {{j:seed0_model_metrics.json:baseline_cnn.test.top1_accuracy:.4f}} | {{j:seed0_model_metrics.json:augmented_cnn.test.top1_accuracy:.4f}} | {{j:seed0_model_metrics.json:baseline_cnn.test.macro_f1:.4f}} | {{j:seed0_model_metrics.json:augmented_cnn.test.macro_f1:.4f}} |
| BiGRU | {{j:seed0_model_metrics.json:baseline_bigru.test.top1_accuracy:.4f}} | {{j:seed0_model_metrics.json:augmented_bigru.test.top1_accuracy:.4f}} | {{j:seed0_model_metrics.json:baseline_bigru.test.macro_f1:.4f}} | {{j:seed0_model_metrics.json:augmented_bigru.test.macro_f1:.4f}} |
| Transformer | {{j:seed0_model_metrics.json:baseline_transformer.test.top1_accuracy:.4f}} | {{j:seed0_model_metrics.json:augmented_transformer.test.top1_accuracy:.4f}} | {{j:seed0_model_metrics.json:baseline_transformer.test.macro_f1:.4f}} | {{j:seed0_model_metrics.json:augmented_transformer.test.macro_f1:.4f}} |

The robustness of the augmented models to the deployment conditions is measured by the same browser-path benchmark and perturbation sweeps, on larger corpora (211 validation and 312 test videos in two framings) and with two more seeds per model. The report presents mean and spread over three seeds in [[tab:threeseed]]. The raw per-video results of the first seed are in `docs/evaluation/eval_val.json` and `eval_test.json`.

Table: Three-seed summary, mean and spread over seeds 0, 1 and 2, accuracy at the validation-chosen threshold unless stated (authors' predefined split, signer independence not verified). Test videos are evaluated once per trained model. {#tab:threeseed}
| Condition | CNN baseline | CNN augmented | BiGRU baseline | BiGRU augmented | Transformer baseline | Transformer augmented |
|---|---|---|---|---|---|---|
| Offline features | {{3s:cnn_base.offline}} | {{3s:cnn_aug.offline}} | {{3s:bigru_base.offline}} | {{3s:bigru_aug.offline}} | {{3s:transformer_base.offline}} | {{3s:transformer_aug.offline}} |
| Browser, 16:9 | {{3s:cnn_base.br16x9}} | {{3s:cnn_aug.br16x9}} | {{3s:bigru_base.br16x9}} | {{3s:bigru_aug.br16x9}} | {{3s:transformer_base.br16x9}} | {{3s:transformer_aug.br16x9}} |
| Browser, 4:3 with rescale | {{3s:cnn_base.br4x3}} | {{3s:cnn_aug.br4x3}} | {{3s:bigru_base.br4x3}} | {{3s:bigru_aug.br4x3}} | {{3s:transformer_base.br4x3}} | {{3s:transformer_aug.br4x3}} |
| Browser, 4:3 raw | {{3s:cnn_base.br4x3_raw}} | {{3s:cnn_aug.br4x3_raw}} | {{3s:bigru_base.br4x3_raw}} | {{3s:bigru_aug.br4x3_raw}} | {{3s:transformer_base.br4x3_raw}} | {{3s:transformer_aug.br4x3_raw}} |
| Wrong-accepted rate, browser 16:9 | {{3s:cnn_base.wrong_accepted}} | {{3s:cnn_aug.wrong_accepted}} | {{3s:bigru_base.wrong_accepted}} | {{3s:bigru_aug.wrong_accepted}} | {{3s:transformer_base.wrong_accepted}} | {{3s:transformer_aug.wrong_accepted}} |
| Validation-chosen threshold | {{3s:cnn_base.threshold}} | {{3s:cnn_aug.threshold}} | {{3s:bigru_base.threshold}} | {{3s:bigru_aug.threshold}} | {{3s:transformer_base.threshold}} | {{3s:transformer_aug.threshold}} |

The effect of the augmentation is the difference between each augmented model and the baseline of the same seed, with a 95 percent t-interval over the three differences ([[tab:threeseeddelta]]). Three seeds give wide intervals, so an interval that contains zero is read as no clear change.

Table: Augmented minus baseline accuracy at each model's validation-chosen threshold, 312 test videos, mean and 95 percent t-interval over three seeds (authors' predefined split, signer independence not verified). {#tab:threeseeddelta}
| Condition | CNN | BiGRU | Transformer |
|---|---|---|---|
| Offline features | {{3s:delta.cnn.offline.acc}} | {{3s:delta.bigru.offline.acc}} | {{3s:delta.transformer.offline.acc}} |
| Browser, 16:9 | {{3s:delta.cnn.br16x9.acc}} | {{3s:delta.bigru.br16x9.acc}} | {{3s:delta.transformer.br16x9.acc}} |
| Browser, 4:3 with rescale | {{3s:delta.cnn.br4x3.acc}} | {{3s:delta.bigru.br4x3.acc}} | {{3s:delta.transformer.br4x3.acc}} |
| Browser, 4:3 raw | {{3s:delta.cnn.br4x3_raw.acc}} | {{3s:delta.bigru.br4x3_raw.acc}} | {{3s:delta.transformer.br4x3_raw.acc}} |
| Wrong-accepted rate, browser 16:9 | {{3s:delta.cnn.br16x9.wa}} | {{3s:delta.bigru.br16x9.wa}} | {{3s:delta.transformer.br16x9.wa}} |
| Change of the 16:9 minus 4:3 gap | {{3s:delta.cnn.gapchange}} | {{3s:delta.bigru.gapchange}} | {{3s:delta.transformer.gapchange}} |

The augmentation clearly helps in one case, the one it was designed for: for the CNN it lifts the accuracy on the unrescaled 4:3 picture from {{3s:cnn_base.br4x3_raw}} to {{3s:cnn_aug.br4x3_raw}} (change {{3s:delta.cnn.br4x3_raw.acc}}). In every other accuracy cell the interval contains zero: there is no clear change offline, in 16:9 or in rescaled 4:3 for any of the three architectures, and no clear regression either, although the spread between seeds is large. Without a threshold, the BiGRU's top-1 accuracy on the unrescaled picture rises by {{3s:delta.bigru.br4x3_raw.top1}}. The gap between 16:9 and rescaled 4:3 does not change clearly, as expected, because the augmentation does not address black padding. The augmented CNN on the unrescaled picture ({{3s:cnn_aug.br4x3_raw}}) still scores below the baseline CNN on the rescaled picture ({{3s:cnn_base.br4x3}}), so the augmentation does not replace the rescale. The CNN is the best architecture in every condition. The validation-chosen threshold differs between models (the threshold row of the first table), and it is 0.95 for all six Transformer models, which lowers their thresholded accuracy. The perturbation sweeps were run for seed 0 only and are not interpreted here.

## Segmentation

The continuous mode was evaluated on streams that join 3 to 5 real INCLUDE samples of different classes (80 streams per row, fixed seed). Between two samples a number of rest frames is inserted (a copy of the last frame of the earlier sample, still, hands down, with small noise); the samples already carry a short rest margin. The rest frames are synthetic and real people may pause differently. Ground truth is the span of each sample. The parameters were tuned on the validation streams (the rest line and the padding mattered) and the test streams were run once with the final settings.

Table: Segmentation results on streams of real INCLUDE samples (real signs split correctly, recognized correctly, accepted but wrong, UNRECOGNIZED). {#tab:seg}
| Split | Rest frames between signs | Real signs | Split correctly | Recognized correctly | Accepted but wrong | UNRECOGNIZED | Whole sentence right |
|---|---|---|---|---|---|---|---|
| Validation | 0 (natural margins only) | 313 | 203 (64.9 percent) | 161 (51.4 percent) | 10 (3.2 percent) | 32 (10.2 percent) | 34 of 80 |
| Validation | 10 | 313 | 308 (98.4 percent) | 250 (79.9 percent) | 13 (4.2 percent) | 45 (14.4 percent) | 36 of 80 |
| Validation | 20 | 313 | 310 (99.0 percent) | 252 (80.5 percent) | 13 (4.2 percent) | 45 (14.4 percent) | 36 of 80 |
| Test | 0 (natural margins only) | 322 | 242 (75.2 percent) | 188 (58.4 percent) | 20 (6.2 percent) | 34 (10.6 percent) | 28 of 80 |
| Test | 10 | 322 | 316 (98.1 percent) | 247 (76.7 percent) | 22 (6.8 percent) | 47 (14.6 percent) | 28 of 80 |
| Test | 20 | 322 | 320 (99.4 percent) | 248 (77.0 percent) | 23 (7.1 percent) | 49 (15.2 percent) | 28 of 80 |

![Segmentation results on validation and test streams for three amounts of rest between signs.](figures/chart_segmentation.png){#fig:seg w=6.0}

With 10 or more rest frames the segmenter finds nearly every sign (98 to 99 percent split correctly). With only the natural margins, 24 to 33 percent of the signs are merged with a neighbour or fragmented: signs signed back to back cannot be separated by this method. For comparison, the isolated mode on whole test samples accepts 86.8 percent at the live threshold with 95.5 percent of those correct, which is about 82.8 percent right, 3.9 percent wrong and 13.2 percent unrecognized. Segmentation costs about 6 points of correct recognition (77.0 against 82.8 percent) and nearly doubles the wrong accepted signs (7.1 against 3.9 percent), because the cut segment is not exactly the span that the model was trained on.

## Comparison with published INCLUDE results

The accuracies of [[tab:modelresults]] cannot be compared directly with published work. Pose-based models on INCLUDE have been reported in the OpenHands study [@selvaraj2022openhands] and the INCLUDE paper itself [@sridhar2020include], but those numbers have not been checked against the published versions for this report and are not repeated. The comparison would also be loose: this project uses 262 of the 263 classes, MediaPipe landmarks, its own training settings and one seed in the baseline, and the split is the authors' in every case, so none of the works can claim signer independence. The result is reported here as it is.
