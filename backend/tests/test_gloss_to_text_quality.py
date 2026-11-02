"""30 gloss sequences and the English they must give. Sequences use the gloss order rules (time first, subject object verb, NOT after the verb,
question word last). The first 21 use only glosses of the 262 INCLUDE classes (what live recognition can output) or the greeting phrases; the
last nine also use grammar words (WHAT, WHERE, WHO, NAME, NOT, GO, LIKE, WANT, SLEEP) that come from text to gloss and have no recognizer class yet."""

import json

import pytest

from nlp.gloss_to_text import gloss_to_english
from nlp.lexicon import load_lexicon

CASES = [
    # greetings and phrases
    ("HELLO", "Hello."),
    ("THANK-YOU", "Thank you."),
    ("GOOD-MORNING", "Good morning."),
    ("HOW-ARE-YOU", "How are you?"),
    ("HELLO DOCTOR", "Hello, doctor."),
    # pronouns with adjectives and nouns
    ("I HAPPY", "I am happy."),
    ("YOU SICK", "You are sick."),
    ("SHE BEAUTIFUL", "She is beautiful."),
    ("THEY POOR", "They are poor."),
    ("HE DOCTOR", "He is a doctor."),
    ("YOU-PLURAL HAPPY", "You all are happy."),
    ("I BROTHER DOCTOR", "My brother is a doctor."),
    ("YOU BOOK NEW", "Your book is new."),
    ("BOOK NEW", "The book is new."),
    ("DOG BIG-LARGE", "The dog is big."),
    # time words
    ("TODAY I HAPPY", "I am happy today."),
    ("YESTERDAY I SICK", "I was sick yesterday."),
    ("YESTERDAY WE SICK", "We were sick yesterday."),
    ("TOMORROW SHE HAPPY", "She will be happy tomorrow."),
    ("MONDAY THEY HAPPY", "They are happy on Monday."),
    ("MORNING I COLD", "I am cold in the morning."),
    # questions
    ("YOU NAME WHAT", "What is your name?"),
    ("HOSPITAL WHERE", "Where is the hospital?"),
    ("YOU WHO", "Who are you?"),
    # verbs, tense and negation (grammar words from text to gloss)
    ("YESTERDAY I HOSPITAL GO", "I went to the hospital yesterday."),
    ("TOMORROW I MARKET GO", "I will go to the market tomorrow."),
    ("I HOSPITAL LIKE NOT", "I do not like the hospital."),
    ("YESTERDAY HE SICK NOT", "He was not sick yesterday."),
    ("YOU WANT WHAT", "What do you want?"),
    ("NIGHT I SLEEP", "I sleep at night."),
]
EXTRA = [
    ("THANK-YOU DOCTOR", "Thank you, doctor."),
    ("TODAY I DOCTOR GO", "I go to the doctor today."),
    ("YESTERDAY YOU GO WHERE", "Where did you go yesterday?"),
    ("YOU HAPPY WHY", "Why are you happy?"),
    ("MONDAY", "Monday."),
    ("MORNING", "Morning."),
    ("SHE HOME GO", "She goes home."),
    ("HE WATER DRINK NOT", "He does not drink the water."),
    ("YOU DOCTOR NOT", "You are not a doctor."),
    ("I NAME FS:RAVI", "My name is Ravi."),
]


def test_there_are_30_cases() -> None:
    assert len(CASES) == 30


@pytest.mark.parametrize("gloss,expected", CASES + EXTRA, ids=[c[0] for c in CASES + EXTRA])
def test_gloss_sequence_gives_the_expected_english(gloss: str, expected: str) -> None:
    assert gloss_to_english(gloss.split()) == expected


def test_every_gloss_in_the_cases_is_in_the_dictionary_and_the_first_21_are_signable_by_the_recognizer() -> None:
    lex = load_lexicon()
    recognizable = {g for g, s in lex.signs.items() if s.source == "include"}
    for gloss, _ in CASES + EXTRA:
        for g in gloss.split():
            assert g in lex.signs or g.startswith("FS:"), g
    for gloss, _ in CASES[:21]:
        assert set(gloss.split()) <= recognizable, gloss  # only glosses the live recognizer can produce


def test_live_stream_sequences_give_the_same_english(tmp_path) -> None:
    """The WebSocket builds its sentence with the same function: a sequence kept in a session reads exactly like the direct call."""
    from app.services.live_service import LiveSession, sentence_fields

    lex = load_lexicon()
    session = LiveSession()
    session.sequence = "YESTERDAY I SICK".split()
    assert sentence_fields(session, lex)["english"] == "I was sick yesterday."
    json.dumps(sentence_fields(session, lex))  # serializable for the socket
