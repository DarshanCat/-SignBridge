"""BLEU and gloss scores against hand worked values, and the reference file format."""

import csv
import math
from pathlib import Path

import pytest

from nlp.generation_metrics import (
    bag_f1, bleu, edit_distance, gloss_scores, gloss_word_error_rate, tokenize_english, tokenize_gloss,
)
from nlp.score_generation import make_template, read_references, score, split_alternatives, to_markdown

t = str.split


def test_bleu_identical_sentences_score_100() -> None:
    s = [t("the cat sat on the mat"), t("a b c d e")]
    r = bleu(s, [[x] for x in s])
    assert r["bleu"] == pytest.approx(100.0) and r["brevity_penalty"] == 1.0


def test_bleu_worked_example_with_and_without_smoothing() -> None:
    hyp, ref = [t("the cat is on the mat")], [[t("the cat sat on the mat")]]
    # unigrams 5/6, bigrams (the cat, on the, the mat) 3/5, trigrams (on the mat) 1/4, 4-grams 0/3
    r = bleu(hyp, ref)
    assert [round(p, 6) for p in r["precisions"][:3]] == [round(100 * 5 / 6, 6), round(100 * 3 / 5, 6), round(100 * 1 / 4, 6)]
    expected = 100 * math.exp((math.log(5 / 6) + math.log(3 / 5) + math.log(1 / 4) + math.log(1 / (2 * 3))) / 4)  # exp smoothing: 1 / (2 * total)
    assert r["bleu"] == pytest.approx(expected)
    assert bleu(hyp, ref, smooth=False)["bleu"] == 0.0


def test_bleu_clips_repeated_words_and_applies_the_brevity_penalty() -> None:
    r = bleu([t("the the the the the the the")], [[t("the cat is on the mat"), t("there is a cat on the mat")]])
    assert r["precisions"][0] == pytest.approx(100 * 2 / 7)  # Papineni's example: "the" counts at most twice
    short = bleu([t("the cat")], [[t("the cat sat on the mat")]])
    assert short["brevity_penalty"] == pytest.approx(math.exp(1 - 6 / 2))


def test_bleu_uses_the_closest_reference_length_and_rejects_bad_input() -> None:
    r = bleu([t("a b c d")], [[t("a b c"), t("a b c d e f g")]])
    assert r["ref_len"] == 3
    with pytest.raises(ValueError):
        bleu([t("a")], [[]])
    with pytest.raises(ValueError):
        bleu([], [])


def test_edit_distance_wer_exact_match_and_bag_f1() -> None:
    assert edit_distance(t("a b c"), t("a c")) == 1 and edit_distance([], t("a b")) == 2 and edit_distance(t("a b"), t("a b")) == 0
    assert gloss_word_error_rate([t("a b c")], [[t("a c"), t("x y z w")]]) == pytest.approx(1 / 2)  # closest reference is "a c"
    assert bag_f1(t("A B B"), [t("A B C")]) == pytest.approx(2 / 3)
    assert bag_f1(t("X"), [t("A B")]) == 0.0
    g = gloss_scores([t("I LIKE EAT"), t("YOU GO")], [[t("I LIKE EAT")], [t("YOU GO WHERE")]])
    assert g["exact_match"] == 0.5 and g["word_error_rate"] == pytest.approx(1 / 6) and g["token_accuracy"] == pytest.approx(5 / 6)


def test_tokenizers() -> None:
    assert tokenize_english("What's your name?") == ["what's", "your", "name", "?"]
    assert tokenize_gloss("YOU FS:RAVI  GO") == ["YOU", "FS:RAVI", "GO"]
    assert split_alternatives(" A B | C D |") == ["A B", "C D"] and split_alternatives("") == []


def write_refs(path: Path, rows: list[dict]) -> Path:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "english", "reference_gloss", "english_alternatives", "signer_id", "notes"])
        w.writeheader()
        for r in rows:
            w.writerow({"english_alternatives": "", "signer_id": "", "notes": "", **r})
    return path


def test_the_template_has_no_references_and_is_never_overwritten(tmp_path: Path) -> None:
    p = tmp_path / "template.csv"
    make_template(p)
    filled, skipped = read_references(p)
    assert filled == [] and len(skipped) == 13  # 3 example sentences and the 10 conversation test sentences
    assert "Where is the hospital?" in p.read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="ever overwritten"):
        make_template(p)
    with pytest.raises(ValueError, match="no row has a reference gloss"):
        score(filled, {}, {})  # an unfilled file cannot be scored


def test_reference_file_validation(tmp_path: Path) -> None:
    (tmp_path / "bad.csv").write_text("id,english\nS1,hi\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing the column"):
        read_references(tmp_path / "bad.csv")
    with pytest.raises(ValueError, match="unique"):
        read_references(write_refs(tmp_path / "dup.csv", [{"id": "S1", "english": "a", "reference_gloss": "A"}, {"id": "S1", "english": "b", "reference_gloss": "B"}]))


def test_scoring_with_hypothesis_files_and_report(tmp_path: Path) -> None:
    refs = write_refs(tmp_path / "r.csv", [
        {"id": "S1", "english": "Where is the hospital?", "reference_gloss": "HOSPITAL WHERE | WHERE HOSPITAL", "signer_id": "P01"},
        {"id": "S2", "english": "I like water", "reference_gloss": "I LIKE WATER", "english_alternatives": "I love water", "signer_id": "P01"},
        {"id": "S3", "english": "unknown", "reference_gloss": ""},
    ])
    filled, skipped = read_references(refs)
    assert [r["id"] for r in filled] == ["S1", "S2"] and [r["id"] for r in skipped] == ["S3"]
    res = score(filled, {"S1": "HOSPITAL WHERE", "S2": "I LIKE"}, {"S1": "Where is the hospital?", "S2": "I like water."})
    a, b = res["english_to_gloss"], res["gloss_to_english"]
    assert a["exact_match"] == 0.5 and a["word_error_rate"] == pytest.approx(1 / 5)  # S1 exact, S2 one word missing of 3 (2 + 3 reference words, 1 error)
    assert b["exact_match"] == 0.5  # the full stop of "I like water." is a token the references do not have, so only S1 matches exactly
    assert a["per_sentence"][0]["exact"] and not a["per_sentence"][1]["exact"]
    md = to_markdown(res, 2, 1, ["P01"])
    assert "2 sentence(s)" in md and "1 without one were skipped" in md and "P01" in md
    with pytest.raises(ValueError, match="no gloss hypothesis for id S2"):
        score(filled, {"S1": "X"}, {"S1": "x", "S2": "y"})


def test_the_projects_own_pipeline_runs_through_the_scorer(tmp_path: Path) -> None:
    spacy = pytest.importorskip("spacy")
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        pytest.skip("the spaCy model is not installed")
    from nlp.lexicon import load_lexicon

    refs = write_refs(tmp_path / "r.csv", [{"id": "S1", "english": "Where are you going?", "reference_gloss": "YOU GO WHERE", "signer_id": "P01"}])
    filled, _ = read_references(refs)
    res = score(filled, None, None, nlp, load_lexicon())
    assert res["english_to_gloss"]["exact_match"] == 1.0  # the system's gloss for this sentence is YOU GO WHERE
    assert 0.0 <= res["gloss_to_english"]["bleu"]["bleu"] <= 100.0
