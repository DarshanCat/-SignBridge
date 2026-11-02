# Pilot training: pilot, v1 partial split, not reportable

Short runs on the partial v1 INCLUDE manifest to debug the pipeline and choose settings. Validation split only (299 samples, 266 classes); the test split was never read. The split is the authors' predefined one and signer independence is unverified, so these numbers are probably optimistic. Not reportable. Result files: one JSON per run in this folder; weights are in `data/pilot_models/` (git-ignored).

| Run | Model | Epochs run | Top-1 | Top-5 | Macro F1 | Settings |
|---|---|---|---|---|---|---|
| s1_cnn | 1D CNN | 15 of 15 | 0.806 | 0.963 | 0.769 | defaults |
| s1_bigru | BiGRU | 15 of 15 | 0.682 | 0.916 | 0.628 | defaults |
| s1_transformer | Transformer | 15 of 15 | 0.572 | 0.873 | 0.511 | defaults |
| s2_cnn_e40 | 1D CNN | 40 of 40 | 0.883 | 0.977 | 0.871 | patience 8 |
| s2_cnn_e40_augment | 1D CNN | 40 of 40 | 0.886 | 0.963 | 0.867 | augmentation on |
| s2_cnn_e40_gap3 | 1D CNN | 34 of 40 | 0.896 | 0.970 | 0.870 | hand gap interpolation 3 frames |
| s2_bigru_e40 | BiGRU | 40 of 40 | 0.816 | 0.960 | 0.797 | patience 8 |
| s2_transformer_e40 | Transformer | 32 of 40 | 0.712 | 0.930 | 0.677 | patience 8 |

Common settings: seed 0, lr 0.001, hidden 128, 2 layers, dropout 0.3, batch 16, sequence length 32, 2 CPU threads.

Reading: the 1D CNN is clearly ahead of BiGRU and Transformer at these budgets. The three CNN variants differ by at most 0.013 top-1, which is about 4 of 299 samples, so augmentation and gap interpolation are not separable from noise here. BiGRU and the 15 epoch runs were still improving at their cap.
