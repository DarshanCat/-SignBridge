# Pixel based sign model: CPU time estimate (nothing was trained)

An image encoder pretrained on ImageNet looks at every frame, a recurrent or convolutional sequence model classifies the embeddings, on INCLUDE v2 (authors' predefined split, signer independence not verified). This is an **estimate from timings on this machine** (CPU only, torch 2.15.0+cpu, 16 logical CPUs); no pixel model was run, no INCLUDE video was processed for it and no evaluation result changed. Encoders were timed with the torchvision architectures at random weights (the speed of a forward pass does not depend on the weights, nothing was downloaded).

## Amounts

- 4284 videos, 138738 usable frames at every second frame (the landmark pipeline's sampling, from the Phase 1 extraction records), about 277476 raw frames. The landmark models resample every sign to 32 frames, so a pixel model would also look at 32 frames per video: 137088 frames. Both options are about 137 thousand frames to encode.
- Video decoding (one INCLUDE video, 1920x1080, 25 fps): 8.67 ms per frame with one thread, so all 277476 raw frames cost about 40 core minutes (a few minutes of wall time on 12 workers when nothing else runs).
- Data: 44 zips, 56.75 GB; 28 are already on disk in `zips_keep` (34 GB), 16 (about 22 GB) must be downloaded again one at a time at the rate seen in the Phase 1 extraction, about 8 to 9 minutes per 1.3 GB zip (about 2.7 MB/s): about 2.4 hours, which can overlap with encoding. Frames must be streamed, not stored: 138 thousand frames of 224x224x3 bytes would be about 21 GB, 277 thousand about 42 GB, against about 60 GB free.

## One pass of a frozen encoder over all frames (about 138 thousand)

| Encoder | Parameters | ms per frame, 224 px, one process | frames per second, 4 processes side by side | One pass at 224 px | One pass at 112 px |
|---|---|---|---|---|---|
| mobilenet_v3_small | 2.5 M | 6.54 | 251.0 | 9 min | 7 min |
| mobilenet_v3_large | 5.5 M | 13.43 | not measured | 31 min | 9 min |
| resnet18 | 11.7 M | 34.47 | 28.9 | 79 min | 23 min |
| efficientnet_b0 | 5.3 M | 24.12 | 46.7 | 49 min | 16 min |
| resnet50 | 25.6 M | 81.0 | not measured | 3.1 h | 54 min |

Side by side processes helped only the smallest network (about 1.6 times); for ResNet-18 the CPU was already saturated by one process. The 224 px column uses the parallel rate where it was measured and the single process rate otherwise. Adding decoding on the same cores makes each figure somewhat longer.

## Fine tuning the encoder end to end (forward and backward) is not practical on this CPU

| Encoder | ms per frame, forward and backward | One epoch (3121 training videos x 32 frames) | 20 epochs, one run |
|---|---|---|---|
| mobilenet_v3_small | 47.9 | 80 min | 27 h |
| resnet18 | 96.49 | 2.7 h | 54 h |

Three seeds would triple these figures, and pixel augmentation would need a new pass of the encoder per epoch. This is why the estimate below is for **frozen** encoders with a trained sequence model on top.

## Sequence model on the embeddings

One training epoch of the project's models on random inputs of the real shape (3121 sequences, 32 frames, batch 16): CNN 3.2 s with the 225 landmark features and 4.1 s with 576 values per frame (MobileNetV3-small size), BiGRU 18.5 s and 20.1 s. So the sequence model is a small part of the cost: with up to 60 epochs a CNN run is a few minutes and a BiGRU run about 20 minutes of pure compute; the landmark BiGRU runs took about 50 minutes each in practice (three in parallel plus data preparation), so allow about that.

## Estimate for the whole experiment (frozen encoder, 32 frames per video)

| Step | MobileNetV3-small | EfficientNet-B0 | ResNet-18 |
|---|---|---|---|
| Download of the 16 missing zips (overlaps with the rest) | about 2.4 h | about 2.4 h | about 2.4 h |
| Decode and encode all frames | 14 min | 54 min | 84 min |
| CNN, BiGRU and Transformer on the embeddings, 3 seeds each | about 1 to 3 h | about 1 to 3 h | about 1 to 3 h |
| **Total wall time, one encoder (download, encode, then train; no overlap assumed)** | **about 3.6 to 5.6 h** | **about 4.3 to 6.3 h** | **about 4.8 to 6.8 h** |

The decode term assumes decoding is spread over 8 cores. Pretrained ImageNet weights (9.8 MB, 21 MB and 45 MB) would have to be downloaded; that was not timed. The largest cost is the data transfer, not the computation.

## What the estimate does not cover, and risks

- **Signer and background leak into the features.** An ImageNet encoder sees clothes, room and face, not only the hands. INCLUDE has no verified signer independence, so a pixel model can score well by recognizing the recording session. The landmark features remove most of this; a pixel model would make the headline numbers look better than they are for unseen signers.
- **The hands are small in a 224 px full frame.** A useful pixel model would need hand crops, which needs the MediaPipe landmarks anyway: a second pass of the Holistic extraction (about 3 hours with downloads, as in Phase 1) on top of the encoder.
- **Domain shift to a webcam is untested for pixels**, and the live browser path would need an encoder running in the browser at about 7 frames per second already taken by landmark extraction (`docs/evaluation/LATENCY.md`).
- Frozen features cannot use pixel augmentation without a new encoder pass per augmented copy. Test discipline as always: all choices on validation, the test split once per final model, each use on the disclosure list.
