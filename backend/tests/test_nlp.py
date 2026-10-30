"""Tests for the rule based English <-> ISL gloss layer (spaCy en_core_web_sm). Expected glosses follow the documented simplified rules;
they are NOT validated ISL and must not be read as linguistic ground truth."""

import pytest
import spacy

from nlp.fingerspell import fingerspell
from nlp.gloss_forms import to_gloss
from nlp.gloss_to_text import gloss_to_english
from nlp.lexicon import load_lexicon
from nlp.text_to_gloss import text_to_gloss


@pytest.fixture(scope="module")
def nlp():
    return spacy.load("en_core_web_sm")


# (English, expected gloss, expected non manual markers)
TEXT_TO_GLOSS = [
    ("Where is the hospital?", "HOSPITAL WHERE", ["wh-question"]),
    ("I went to the market yesterday.", "YESTERDAY I MARKET GO", []),
    ("What is your name?", "YOU NAME WHAT", ["wh-question"]),
    ("My name is Ravi.", "I NAME FS:RAVI", []),
    ("Do you want water?", "YOU WATER WANT", ["yes-no-question"]),
    ("I will go to school tomorrow.", "TOMORROW I SCHOOL GO", []),
    ("I am not happy.", "I HAPPY NOT", ["negation"]),
    ("Good morning.", "GOOD-MORNING", []),
    ("How are you?", "HOW-ARE-YOU", []),
    ("Thank you very much.", "THANK-YOU", []),
    ("He eats food.", "HE FOOD EAT", []),
    ("The doctor helps the patient.", "DOCTOR PATIENT HELP", []),
    ("Who is the teacher?", "TEACHER WHO", ["wh-question"]),
    ("Where is the bank?", "BANK WHERE", ["wh-question"]),
    ("I am a student.", "I STUDENT", []),
    ("Today is Monday.", "TODAY MONDAY", []),
    ("She does not like tea.", "SHE FS:TEA LIKE NOT", ["negation"]),
    ("We go home.", "WE HOME GO", []),
    ("Can you help me?", "YOU I HELP CAN", ["yes-no-question"]),
    ("I want to eat food.", "I FOOD WANT EAT", []),
    ("Where is your school?", "YOU SCHOOL WHERE", ["wh-question"]),
    ("Hello, my name is Anita.", "HELLO I NAME FS:ANITA", []),
    ("I saw my brother yesterday.", "YESTERDAY I BROTHER SEE", []),
    ("Tomorrow I will meet the doctor.", "TOMORROW I DOCTOR MEET", []),
    ("The hospital is big.", "HOSPITAL BIG-LARGE", []),
    ("I cannot go to the market.", "I MARKET GO NOT CAN", ["negation"]),
    ("You all are happy.", "YOU-PLURAL HAPPY", []),
    ("Please help me.", "PLEASE I HELP", []),
    ("He did not come to the office last week.", "LAST WEEK HE OFFICE COME NOT", ["negation"]),
    ("I have a car.", "I CAR HAVE", []),
    ("Why are you sad?", "YOU SAD WHY", ["wh-question"]),
    ("They went to the temple on Sunday.", "SUNDAY THEY TEMPLE GO", []),
    ("I live in India.", "I INDIA LIVE", []),
    ("I drink water every morning.", "MORNING I WATER DRINK", []),
    ("Is the library open?", "LIBRARY FS:OPEN", ["yes-no-question"]),
    ("What time is it?", "TIME IT WHAT", ["wh-question"]),
]

# (gloss, expected English)
GLOSS_TO_TEXT = [
    ("YESTERDAY I MARKET GO", "I went to the market yesterday."),
    ("HOSPITAL WHERE", "Where is the hospital?"),
    ("YOU NAME WHAT", "What is your name?"),
    ("I NAME FS:RAVI", "My name is Ravi."),
    ("TOMORROW I SCHOOL GO", "I will go to the school tomorrow."),
    ("I HAPPY NOT", "I am not happy."),
    ("GOOD-MORNING", "Good morning."),
    ("HOW-ARE-YOU", "How are you?"),
    ("THANK-YOU", "Thank you."),
    ("DOCTOR PATIENT HELP", "The doctor helps the patient."),
    ("SHE TEACHER", "She is a teacher."),
    ("YOU I HELP CAN", "You can help me."),
    ("YESTERDAY HE SCHOOL GO NOT", "He did not go to the school yesterday."),
    ("HOSPITAL BIG", "The hospital is big."),
    ("I TEACHER", "I am a teacher."),
    ("TODAY I WORK", "I work today."),
    ("WE HOME GO", "We go home."),
    ("I TEA LIKE BUT SHE COFFEE LIKE", "I like the tea, but she likes the coffee."),
    ("BANK WHERE", "Where is the bank?"),
    ("YOU WATER WANT", "You want the water."),
]


@pytest.mark.parametrize("english, gloss, nmm", TEXT_TO_GLOSS)
def test_english_to_gloss(nlp, english, gloss, nmm) -> None:
    r = text_to_gloss(english, nlp)
    assert r.gloss_string == gloss
    assert r.nmm == nmm


def test_at_least_thirty_text_to_gloss_pairs() -> None:
    assert len(TEXT_TO_GLOSS) >= 30


@pytest.mark.parametrize("gloss, english", GLOSS_TO_TEXT)
def test_gloss_to_english(gloss, english) -> None:
    assert gloss_to_english(gloss.split()) == english


@pytest.mark.parametrize(
    "english",
    ["I went to the market yesterday.", "Where is the hospital?", "What is your name?", "My name is Ravi.", "Good morning.",
     "How are you?", "The doctor helps the patient.", "I am not happy."],
)
def test_round_trip_for_supported_sentences(nlp, english) -> None:
    assert gloss_to_english(text_to_gloss(english, nlp).gloss) == english


def test_required_examples(nlp) -> None:
    assert text_to_gloss("Where is the hospital?", nlp).gloss_string == "HOSPITAL WHERE"
    assert text_to_gloss("I went to the market yesterday", nlp).gloss_string == "YESTERDAY I MARKET GO"
    assert gloss_to_english(["YESTERDAY", "I", "MARKET", "GO"]) == "I went to the market yesterday."


def test_tense_comes_from_time_signs_and_markers_are_reported(nlp) -> None:
    assert text_to_gloss("I went to the market yesterday.", nlp).tense == "past"
    assert text_to_gloss("I will go tomorrow.", nlp).tense == "future"
    assert text_to_gloss("I go to the market.", nlp).tense == "present"
    r = text_to_gloss("I did not go to the market.", nlp)
    assert r.nmm == ["negation"] and "NOT" in r.gloss


def test_dropped_words_are_reported_with_reasons(nlp) -> None:
    r = text_to_gloss("Where is the hospital?", nlp)
    assert {d["word"]: d["reason"] for d in r.dropped} == {"is": "copula or auxiliary", "the": "article or determiner"}


def test_multiple_clauses_keep_each_clause_order(nlp) -> None:
    assert text_to_gloss("I like tea but she likes coffee.", nlp).gloss_string == "I FS:TEA LIKE BUT SHE FS:COFFEE LIKE"


def test_unknown_words_and_names_are_fingerspelled(nlp) -> None:
    r = text_to_gloss("I met Ravi.", nlp)
    assert "FS:RAVI" in r.gloss and "RAVI" in r.fingerspelled
    tok = next(t for t in r.tokens if t.gloss == "FS:RAVI")
    assert tok.kind == "fingerspell" and tok.letters == ["R", "A", "V", "I"]
    assert fingerspell("o'neil 2") == ("FS:ONEIL2", list("ONEIL2"))
    with pytest.raises(ValueError):
        fingerspell("...")


def test_fingerspelled_tokens_become_names_in_english() -> None:
    assert gloss_to_english(["I", "NAME", "FS:ANITA"]) == "My name is Anita."


@pytest.mark.parametrize(
    "label, gloss",
    [("you (plural)", "YOU-PLURAL"), ("Race (ethnicity)", "RACE-ETHNICITY"), ("Second (Number)", "SECOND-NUMBER"),
     ("Second", "SECOND"), ("Store or Shop", "STORE-OR-SHOP"), ("Thank you", "THANK-YOU"), ("T-Shirt", "T-SHIRT")],
)
def test_gloss_forms(label, gloss) -> None:
    assert to_gloss(label) == gloss


def test_dictionary_has_the_263_include_signs_and_marks_placeholders() -> None:
    lex = load_lexicon()
    include = [s for s in lex.signs.values() if s.source == "include"]
    assert len(include) == 263
    assert {"YOU-PLURAL", "RACE-ETHNICITY", "SECOND-NUMBER", "SECOND"} <= set(lex.signs)
    assert all(s.source == "grammar_placeholder" for s in lex.signs.values() if s.category == "grammar")
    assert lex.lookup("hospital") == "HOSPITAL" and lex.lookup("shop") == "STORE-OR-SHOP" and lex.lookup("zzzz") is None


def test_input_errors(nlp) -> None:
    with pytest.raises(ValueError):
        text_to_gloss("?!...", nlp)
    with pytest.raises(ValueError):
        gloss_to_english([])
