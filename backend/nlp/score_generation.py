"""Score the rule based generation (English to gloss, gloss to English) against references a signer wrote. Run from backend/:

    python -m nlp.score_generation --make-template ..\\docs\\evaluation\\generation_references_template.csv
    python -m nlp.score_generation --references my_references.csv --out ..\\docs\\evaluation\\generation_scores

Reference file (CSV, UTF-8, one sentence per row), columns:
    id                   any unique text, for example S01
    english              the English sentence (filled in by the template; the source of English to gloss and the reference of gloss to English)
    reference_gloss      FILLED IN BY THE SIGNER: the gloss sequence a signer would use, tokens separated by spaces, upper case, a fingerspelled word as FS:WORD.
                         Several acceptable answers are separated by " | ". Leave it empty when you do not know: the row is then skipped and counted.
    english_alternatives optional: other acceptable English renderings of the sign sequence, separated by " | "
    signer_id            who wrote the row (P01, never a name)
    notes                free text

Task A (English to gloss): the system's gloss for `english` against `reference_gloss`: exact match, gloss word error rate, bag F1, BLEU.
Task B (gloss to English): the system's English for the first `reference_gloss` against `english` plus `english_alternatives`: BLEU and exact match.
The template contains no references: nothing is invented, an unfilled file cannot be scored. To score another system, give its output with
--hyp-gloss (CSV with columns id,hypothesis) and/or --hyp-english.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

from nlp.generation_metrics import bleu, gloss_scores, tokenize_english, tokenize_gloss

FIELDS = ["id", "english", "reference_gloss", "english_alternatives", "signer_id", "notes"]
TEMPLATE_SENTENCES = ["Where is the hospital?", "I went to the hospital yesterday", "I do not like the hospital"]


def split_alternatives(text: str) -> list[str]:
    return [t.strip() for t in text.split("|") if t.strip()]


def read_references(path: Path) -> tuple[list[dict], list[dict]]:
    """(rows with a reference gloss, rows without). Raises ValueError for a file that is not in the format."""
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = {"id", "english", "reference_gloss"} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"the reference file is missing the column(s) {sorted(missing)}")
        rows = list(reader)
    ids = [r["id"].strip() for r in rows]
    if len(set(ids)) != len(ids) or any(not i for i in ids):
        raise ValueError("every row needs a unique, non empty id")
    filled = [r for r in rows if split_alternatives(r.get("reference_gloss") or "")]
    return filled, [r for r in rows if r not in filled]


def read_hypotheses(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not {"id", "hypothesis"} <= set(reader.fieldnames or []):
            raise ValueError("a hypothesis file needs the columns id,hypothesis")
        return {r["id"].strip(): r["hypothesis"] for r in reader}


def score(filled: list[dict], hyp_gloss: dict[str, str] | None, hyp_english: dict[str, str] | None, nlp=None, lex=None) -> dict:
    """Both tasks over the filled rows. Without hypothesis files the project's own rule based pipeline produces the hypotheses (nlp and lex required)."""
    if not filled:
        raise ValueError("no row has a reference gloss: nothing to score (the template is for a signer to fill in)")
    if (hyp_gloss is None or hyp_english is None) and nlp is None:
        raise ValueError("a spaCy model is needed to run the project's own pipeline")
    rows_a, rows_b = [], []
    for r in filled:
        rid = r["id"].strip()
        golds = [tokenize_gloss(g) for g in split_alternatives(r["reference_gloss"])]
        if hyp_gloss is not None:
            hyp_a = hyp_gloss.get(rid)
            if hyp_a is None:
                raise ValueError(f"no gloss hypothesis for id {rid}")
        else:
            from nlp.text_to_gloss import text_to_gloss

            hyp_a = " ".join(text_to_gloss(r["english"], nlp, lex).gloss)
        rows_a.append({"id": rid, "english": r["english"], "hypothesis": tokenize_gloss(hyp_a), "references": golds})
        refs_en = [r["english"]] + split_alternatives(r.get("english_alternatives") or "")
        if hyp_english is not None:
            hyp_b = hyp_english.get(rid)
            if hyp_b is None:
                raise ValueError(f"no English hypothesis for id {rid}")
        else:
            from nlp.gloss_to_text import gloss_to_english

            hyp_b = gloss_to_english(golds[0], lex)
        rows_b.append({"id": rid, "hypothesis": tokenize_english(hyp_b), "references": [tokenize_english(x) for x in refs_en], "text": hyp_b})
    a = gloss_scores([x["hypothesis"] for x in rows_a], [x["references"] for x in rows_a])
    b_bleu = bleu([x["hypothesis"] for x in rows_b], [x["references"] for x in rows_b])
    b_exact = sum(x["hypothesis"] in x["references"] for x in rows_b) / len(rows_b)
    return {
        "english_to_gloss": {**a, "per_sentence": [{"id": x["id"], "english": x["english"], "hypothesis": " ".join(x["hypothesis"]),
                                                    "references": [" ".join(g) for g in x["references"]], "exact": x["hypothesis"] in x["references"]} for x in rows_a]},
        "gloss_to_english": {"sentences": len(rows_b), "exact_match": b_exact, "bleu": b_bleu,
                             "per_sentence": [{"id": x["id"], "hypothesis": x["text"], "exact": x["hypothesis"] in x["references"]} for x in rows_b]},
    }


def to_markdown(res: dict, n_filled: int, n_skipped: int, signers: list[str]) -> str:
    a, b = res["english_to_gloss"], res["gloss_to_english"]
    o = ["# Generation scores\n",
         f"{n_filled} sentence(s) with a reference gloss were scored, {n_skipped} without one were skipped. Reference signers: {', '.join(signers) or 'not stated'}. "
         "References are only as good as the people who wrote them; the BLEU of very short sentences is unstable, so read it together with exact match and word error rate.\n",
         "## English to gloss\n", f"- Exact match: {a['exact_match']:.3f}", f"- Gloss word error rate: {a['word_error_rate']:.3f} (token accuracy {a['token_accuracy']:.3f})",
         f"- Bag of gloss tokens F1: {a['bag_f1']:.3f}", f"- BLEU-4: {a['bleu']['bleu']:.1f} (n-gram precisions {', '.join(f'{p:.1f}' for p in a['bleu']['precisions'])}, brevity penalty {a['bleu']['brevity_penalty']:.2f})\n",
         "| id | English | system gloss | reference gloss | exact |", "|---|---|---|---|---|"]
    o += [f"| {x['id']} | {x['english']} | {x['hypothesis']} | {' / '.join(x['references'])} | {'yes' if x['exact'] else 'no'} |" for x in a["per_sentence"]]
    o += ["\n## Gloss to English\n", f"- Exact match: {b['exact_match']:.3f}", f"- BLEU-4: {b['bleu']['bleu']:.1f} (n-gram precisions {', '.join(f'{p:.1f}' for p in b['bleu']['precisions'])}, brevity penalty {b['bleu']['brevity_penalty']:.2f})\n",
          "| id | system English | exact |", "|---|---|---|"]
    o += [f"| {x['id']} | {x['hypothesis']} | {'yes' if x['exact'] else 'no'} |" for x in b["per_sentence"]]
    return "\n".join(o) + "\n"


def make_template(path: Path) -> None:
    from app.conversation_vocab import load_vocabulary

    if path.exists():
        raise ValueError(f"{path} exists: nothing is ever overwritten")
    sentences = TEMPLATE_SENTENCES + list(load_vocabulary().test_sentences)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for i, s in enumerate(sentences, 1):
            w.writerow({"id": f"S{i:02d}", "english": s, "reference_gloss": "", "english_alternatives": "", "signer_id": "", "notes": ""})
    print(f"template with {len(sentences)} sentences written to {path} (reference_gloss is empty: a signer fills it in)")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--make-template", type=Path)
    p.add_argument("--references", type=Path)
    p.add_argument("--hyp-gloss", type=Path, help="CSV id,hypothesis: gloss from another system (default: this project's text to gloss)")
    p.add_argument("--hyp-english", type=Path, help="CSV id,hypothesis: English from another system (default: this project's gloss to English)")
    p.add_argument("--out", type=Path, help="output folder for scores.json and scores.md")
    p.add_argument("--spacy-model", default="en_core_web_sm")
    a = p.parse_args()
    try:
        if a.make_template:
            make_template(a.make_template)
            return 0
        if not a.references:
            p.error("give --make-template or --references")
        filled, skipped = read_references(a.references)
        nlp = lex = None
        if a.hyp_gloss is None or a.hyp_english is None:
            import spacy

            from nlp.lexicon import load_lexicon

            nlp, lex = spacy.load(a.spacy_model), load_lexicon()
        res = score(filled, read_hypotheses(a.hyp_gloss) if a.hyp_gloss else None, read_hypotheses(a.hyp_english) if a.hyp_english else None, nlp, lex)
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    signers = sorted({r.get("signer_id", "").strip() for r in filled if r.get("signer_id", "").strip()})
    md = to_markdown(res, len(filled), len(skipped), signers)
    if a.out:
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / "scores.json").write_text(json.dumps({"scored": len(filled), "skipped": len(skipped), "signers": signers, **res}, indent=1), encoding="utf-8")
        (a.out / "scores.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
