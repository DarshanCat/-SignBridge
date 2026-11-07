"""docs/evaluation/ISL_CSLRT_RESULTS.md from isl_cslrt_continuous.json (the one pass of the live model) and isl_cslrt_generation_scores/scores.json. Nothing is typed in.
usage (repository root): python -I tools/extra_datasets/isl_cslrt_report.py"""
import json
from pathlib import Path

EV = Path(__file__).resolve().parents[2] / "docs" / "evaluation"
r = json.loads((EV / "isl_cslrt_continuous.json").read_text(encoding="utf-8"))
g = json.loads((EV / "isl_cslrt_generation_scores" / "scores.json").read_text(encoding="utf-8"))
pv = r["per_video"]
seg, rec, ans, prec = r["segmentation"], r["covered_sign_recall"], r["answer_rate"], r["answer_precision"]
one = sum(p["signs"] == 1 for p in pv)
o = []
P = o.append
P("# ISL-CSLTR continuous sentence test: results\n")
P("Protocol: `ISL_CSLRT_PROTOCOL.md`, written and committed before the first video was fetched. One pass of the live model (1D CNN, 262 classes, trained on the authors' predefined split of INCLUDE v2, "
  f"validation-chosen threshold {r['model']['threshold']}) and of the live segmenter over {r['videos_evaluated']} of {r['videos_selected']} selected videos of the ISL-CSLTR corpus "
  "(79 sentences that contain at least one corpus gloss that is a class of the model, first three videos of each folder). Authors' predefined split, signer independence not verified: this is a different dataset, no signer IDs exist for either. "
  "This is one test use of the live model on external data and is on the disclosure list. The reference glosses are the corpus authors', not checked by a signer of this project. Nothing was tuned on this data and nothing was changed after seeing the results.\n")
P("The selection rule gave 235 videos, not the 232 written in the protocol: the folder `which collegeschool are you from` (3 videos) matches its sentence once spaces are ignored, which the protocol's count had missed. Extraction transferred 3.71 GB (the range reader fetches 4 MB blocks, so more than the 2.75 GB of the selected files); every video was deleted after its landmarks were extracted.\n")
P("## Results\n")
P(f"- **Segmentation.** The live segmenter found exactly one segment in {one} of {len(pv)} videos (median {seg['median_segments']} segment against a median of {seg['median_gloss_tokens']} corpus gloss tokens per sentence). "
  f"Segment count is within one of the gloss count in {seg['within_one'] * 100:.1f} percent of the videos; Spearman correlation between the two counts {seg['spearman_segments_vs_gloss_tokens']:.2f}. The likely reason (not checked frame by frame) is that the signs of a sentence run into each other without the rest between them that the segmenter looks for, so the sentence ends up as one segment.")
P(f"- **Recall of covered signs.** {rec['found']} of {rec['covered_tokens']} covered gloss tokens appear among the answers ({(rec['recall'] or 0) * 100:.1f} percent).")
P(f"- **Answer rate.** {ans['answered']} of {ans['signs']} segments were answered at the threshold ({(ans['rate'] or 0) * 100:.1f} percent); the rest are UNRECOGNIZED.")
P(f"- **Answer precision against the corpus glosses.** {prec['in_sentence_glosses']} of {prec['answered']} answers are one of the glosses of their sentence; all {prec['wrong']} are wrong. "
  + "; ".join(f"{k} files: {v['wrong']} wrong of {v['answered']} answered, {v['signs']} segments" for k, v in prec["by_video_kind"].items()) + ". The most frequent wrong answers: "
  + ", ".join(f"{a} ({n})" for a, n in __import__("collections").Counter(a for p in pv for a in p["answered"]).most_common(6)) + ".")
full = r["fully_covered_sentences"]
P(f"- **The two fully covered sentences** (you are bad, you are good): {sum(f['exact'] for f in full)} of {len(full)} videos exactly right. Too few to be a score.\n")
P("Reading: the model was trained on isolated signs and answers a whole sentence video (median 48 usable frames at every second frame) with one class, with a confidence that passes the threshold in about 4 of 10 cases, and it never named a sign that is in the sentence. "
  "This measures what the live pipeline does with continuous, differently recorded signing; it is not a finding about unseen signers of INCLUDE. It also shows the open vocabulary error: signs outside the 262 classes are answered with some class instead of UNRECOGNIZED.\n")
a, b = g["english_to_gloss"], g["gloss_to_english"]
P("## English to gloss against the corpus glosses (no video, `nlp.score_generation`)\n")
P(f"{g['scored']} sentences. Exact match {a['exact_match']:.3f}, gloss word error rate {a['word_error_rate']:.3f}, bag of gloss tokens F1 {a['bag_f1']:.3f}, BLEU-4 {a['bleu']['bleu']:.1f}. "
  f"Gloss to English from the corpus glosses back to the sentence: exact match {b['exact_match']:.3f}, BLEU-4 {b['bleu']['bleu']:.1f}. "
  "The rule based gloss puts time signs first and drops function words in its own way, while the corpus glosses keep English word order and write different spellings (DONOT, FS:WORD); the numbers measure agreement with that convention, not whether either is right ISL.\n")
(EV / "ISL_CSLRT_RESULTS.md").write_text("\n".join(o) + "\n", encoding="utf-8", newline="\n")
print("\n".join(o))
