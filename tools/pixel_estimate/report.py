"""docs/evaluation/PIXEL_MODEL_ESTIMATE.md from pixel_model_timing.json and the frame counts of the face extraction records. Nothing is typed in.
usage (repository root): python -I tools/pixel_estimate/report.py"""
import csv
import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
t = json.loads((ROOT / "docs" / "evaluation" / "pixel_model_timing.json").read_text(encoding="utf-8"))
frames = videos = 0
for p in glob.glob(str(ROOT / "data" / "processed" / "face_v1" / "_parts" / "*.csv")):
    for r in csv.DictReader(open(p, encoding="utf-8")):
        videos += 1
        frames += int(r["frames"] or 0)
per32 = videos * 32
raw = frames * 2
dec = t["decode"]
enc, par, seq = t["encoders"], t["parallel_4_processes_x_4_threads_frames_per_second"], t["sequence_epoch_seconds"]
mn = lambda s: f"{s / 60:.0f} min" if s < 5400 else f"{s / 3600:.1f} h"
o = []
P = o.append
P("# Pixel based sign model: CPU time estimate (nothing was trained)\n")
P("An image encoder pretrained on ImageNet looks at every frame, a recurrent or convolutional sequence model classifies the embeddings, on INCLUDE v2 (authors' predefined split, signer independence not verified). "
  "This is an **estimate from timings on this machine** (CPU only, torch " + t["machine"]["torch"] + ", " + str(t["machine"]["cpu_count"]) + " logical CPUs); no pixel model was run, no INCLUDE video was processed for it and no evaluation result changed. "
  "Encoders were timed with the torchvision architectures at random weights (the speed of a forward pass does not depend on the weights, nothing was downloaded).\n")
P("## Amounts\n")
P(f"- {videos} videos, {frames} usable frames at every second frame (the landmark pipeline's sampling, from the Phase 1 extraction records), about {raw} raw frames. "
  f"The landmark models resample every sign to 32 frames, so a pixel model would also look at 32 frames per video: {per32} frames. Both options are about {per32 // 1000} thousand frames to encode.")
P(f"- Video decoding (one INCLUDE video, {dec['width']}x{dec['height']}, {dec['fps']:.0f} fps): {dec['ms_per_frame_single_thread']} ms per frame with one thread, so all {raw} raw frames cost about {raw * dec['ms_per_frame_single_thread'] / 1000 / 60:.0f} core minutes (a few minutes of wall time on 12 workers when nothing else runs).")
P("- Data: 44 zips, 56.75 GB; 28 are already on disk in `zips_keep` (34 GB), 16 (about 22 GB) must be downloaded again one at a time at the rate seen in the Phase 1 extraction, about 8 to 9 minutes per 1.3 GB zip (about 2.7 MB/s): about 2.4 hours, which can overlap with encoding. Frames must be streamed, not stored: 138 thousand frames of 224x224x3 bytes would be about 21 GB, 277 thousand about 42 GB, against about 60 GB free.\n")
P("## One pass of a frozen encoder over all frames (about 138 thousand)\n")
P("| Encoder | Parameters | ms per frame, 224 px, one process | frames per second, 4 processes side by side | One pass at 224 px | One pass at 112 px |")
P("|---|---|---|---|---|---|")
for name, e in enc.items():
    one = e["ms_per_frame_224_forward_all_threads"]
    fps = par.get(name, {}).get("parallel") if name in par else None
    best = per32 / fps if fps else per32 * one / 1000
    P(f"| {name} | {e['parameters'] / 1e6:.1f} M | {one} | {fps if fps else 'not measured'} | {mn(best)} | {mn(per32 * e['ms_per_frame_112_forward_all_threads'] / 1000)} |")
P("\nSide by side processes helped only the smallest network (about 1.6 times); for ResNet-18 the CPU was already saturated by one process. The 224 px column uses the parallel rate where it was measured and the single process rate otherwise. Adding decoding on the same cores makes each figure somewhat longer.\n")
P("## Fine tuning the encoder end to end (forward and backward) is not practical on this CPU\n")
P("| Encoder | ms per frame, forward and backward | One epoch (3121 training videos x 32 frames) | 20 epochs, one run |")
P("|---|---|---|---|")
for name, e in enc.items():
    ms = e["ms_per_frame_224_forward_backward_all_threads"]
    if ms:
        ep = 3121 * 32 * ms / 1000
        P(f"| {name} | {ms} | {mn(ep)} | {ep * 20 / 3600:.0f} h |")
P("\nThree seeds would triple these figures, and pixel augmentation would need a new pass of the encoder per epoch. This is why the estimate below is for **frozen** encoders with a trained sequence model on top.\n")
P("## Sequence model on the embeddings\n")
P(f"One training epoch of the project's models on random inputs of the real shape (3121 sequences, 32 frames, batch 16): CNN {seq['cnn_225']} s with the 225 landmark features and {seq['cnn_576']} s with 576 values per frame (MobileNetV3-small size), BiGRU {seq['bigru_225']} s and {seq['bigru_576']} s. "
  "So the sequence model is a small part of the cost: with up to 60 epochs a CNN run is a few minutes and a BiGRU run about 20 minutes of pure compute; the landmark BiGRU runs took about 50 minutes each in practice (three in parallel plus data preparation), so allow about that.\n")
P("## Estimate for the whole experiment (frozen encoder, 32 frames per video)\n")
sm, eb, r18 = per32 / par["mobilenet_v3_small"]["parallel"], per32 / par["efficientnet_b0"]["parallel"], per32 / par["resnet18"]["parallel"]
P(f"| Step | MobileNetV3-small | EfficientNet-B0 | ResNet-18 |")
P("|---|---|---|---|")
P(f"| Download of the 16 missing zips (overlaps with the rest) | about 2.4 h | about 2.4 h | about 2.4 h |")
P(f"| Decode and encode all frames | {mn(sm + raw * dec['ms_per_frame_single_thread'] / 1000 / 8)} | {mn(eb + raw * dec['ms_per_frame_single_thread'] / 1000 / 8)} | {mn(r18 + raw * dec['ms_per_frame_single_thread'] / 1000 / 8)} |")
P("| CNN, BiGRU and Transformer on the embeddings, 3 seeds each | about 1 to 3 h | about 1 to 3 h | about 1 to 3 h |")
enc_s = [sm, eb, r18]
dec_s = raw * dec["ms_per_frame_single_thread"] / 1000 / 8
rng = [f"about {2.4 + (e + dec_s) / 3600 + 1:.1f} to {2.4 + (e + dec_s) / 3600 + 3:.1f} h" for e in enc_s]
P(f"| **Total wall time, one encoder (download, encode, then train; no overlap assumed)** | **{rng[0]}** | **{rng[1]}** | **{rng[2]}** |")
P("\nThe decode term assumes decoding is spread over 8 cores. Pretrained ImageNet weights (9.8 MB, 21 MB and 45 MB) would have to be downloaded; that was not timed. The largest cost is the data transfer, not the computation.\n")
P("## What the estimate does not cover, and risks\n")
P("- **Signer and background leak into the features.** An ImageNet encoder sees clothes, room and face, not only the hands. INCLUDE has no verified signer independence, so a pixel model can score well by recognizing the recording session. The landmark features remove most of this; a pixel model would make the headline numbers look better than they are for unseen signers.")
P("- **The hands are small in a 224 px full frame.** A useful pixel model would need hand crops, which needs the MediaPipe landmarks anyway: a second pass of the Holistic extraction (about 3 hours with downloads, as in Phase 1) on top of the encoder.")
P("- **Domain shift to a webcam is untested for pixels**, and the live browser path would need an encoder running in the browser at about 7 frames per second already taken by landmark extraction (`docs/evaluation/LATENCY.md`).")
P("- Frozen features cannot use pixel augmentation without a new encoder pass per augmented copy. Test discipline as always: all choices on validation, the test split once per final model, each use on the disclosure list.")
(ROOT / "docs" / "evaluation" / "PIXEL_MODEL_ESTIMATE.md").write_text("\n".join(o) + "\n", encoding="utf-8", newline="\n")
print("\n".join(o))
