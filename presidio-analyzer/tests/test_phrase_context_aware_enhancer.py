import pytest

from presidio_analyzer import PhraseContextAwareEnhancer


def _licence_recognizer(context, regex=r"\b[A-Z]{3}\d{5}\b"):
    from presidio_analyzer import Pattern, PatternRecognizer

    return PatternRecognizer(
        supported_entity="TEST_LICENCE",
        name="test_licence_recognizer",
        context=context,
        patterns=[Pattern("test_pattern", regex, 0.3)],
    )


def _enhance_one(spacy_nlp_engine, text, recognizer, enhancer):
    nlp_artifacts = spacy_nlp_engine.process_text(text, "en")
    results = recognizer.analyze(text, recognizer.supported_entities, nlp_artifacts)
    assert len(results) == 1
    return enhancer.enhance_using_context(text, results, nlp_artifacts, [recognizer])[0]


@pytest.mark.parametrize("matching_mode", ["substring", "whole_word"])
@pytest.mark.parametrize(
    "text",
    [
        "My driving licence number is ABC12345",
        "My Driving  LICENCE is ABC12345",
        "driving\tlicence:\nABC12345",
    ],
)
def test_when_multi_word_context_word_in_window_then_score_enhanced(
    spacy_nlp_engine, text, matching_mode
):
    recognizer = _licence_recognizer(["driving licence"])
    enhancer = PhraseContextAwareEnhancer(context_matching_mode=matching_mode)

    result = _enhance_one(spacy_nlp_engine, text, recognizer, enhancer)

    assert result.score == pytest.approx(0.65)
    assert result.analysis_explanation.supportive_context_word == "driving licence"


@pytest.mark.parametrize(
    "text",
    [
        "licence driving ABC12345",
        "driving the licence ABC12345",
        "driving, licence ABC12345",
        "I was driving. Licence ABC12345",
        # after the entity, and the suffix window is 0 by default
        "ABC12345 is my driving licence",
        # before the five keywords of the prefix window
        "driving licence office closed early today because staff were ill ABC12345",
    ],
)
def test_when_multi_word_context_word_not_in_window_then_score_unchanged(
    spacy_nlp_engine, text
):
    recognizer = _licence_recognizer(["driving licence"])

    result = _enhance_one(
        spacy_nlp_engine, text, recognizer, PhraseContextAwareEnhancer()
    )

    assert result.score == pytest.approx(0.3)
    assert result.analysis_explanation.supportive_context_word == ""


def test_when_suffix_window_set_then_multi_word_context_after_entity_counts(
    spacy_nlp_engine,
):
    recognizer = _licence_recognizer(["driving licence"])
    enhancer = PhraseContextAwareEnhancer(context_suffix_count=3)

    result = _enhance_one(
        spacy_nlp_engine, "ABC12345 is my driving licence", recognizer, enhancer
    )

    assert result.score == pytest.approx(0.65)


def test_when_multi_word_context_word_embedded_then_only_substring_mode_matches(
    spacy_nlp_engine,
):
    text = "My driving licenceholder is ABC12345"
    recognizer = _licence_recognizer(["driving licence"])

    substring = _enhance_one(
        spacy_nlp_engine,
        text,
        recognizer,
        PhraseContextAwareEnhancer(context_matching_mode="substring"),
    )
    whole_word = _enhance_one(
        spacy_nlp_engine,
        text,
        recognizer,
        PhraseContextAwareEnhancer(context_matching_mode="whole_word"),
    )

    assert substring.score == pytest.approx(0.65)
    assert whole_word.score == pytest.approx(0.3)


@pytest.mark.parametrize(
    "text, expected_score",
    [
        # the phrase is part of the entity itself
        ("Filed: driving licence 12345", 0.3),
        # an occurrence inside the entity, then one before it
        ("driving licence: driving licence 12345", 0.65),
    ],
)
def test_when_multi_word_context_word_overlaps_entity_then_it_is_not_context(
    spacy_nlp_engine, text, expected_score
):
    recognizer = _licence_recognizer(["driving licence"], r"driving licence \d{5}")

    result = _enhance_one(
        spacy_nlp_engine, text, recognizer, PhraseContextAwareEnhancer()
    )

    assert result.score == pytest.approx(expected_score)


@pytest.mark.parametrize("matching_mode", ["substring", "whole_word"])
def test_when_rejected_phrase_match_overlaps_a_valid_one_then_valid_one_counts(
    spacy_nlp_engine, matching_mode
):
    recognizer = _licence_recognizer(["test test"], r"^test")
    enhancer = PhraseContextAwareEnhancer(
        context_prefix_count=0,
        context_suffix_count=2,
        context_matching_mode=matching_mode,
    )

    result = _enhance_one(spacy_nlp_engine, "test test test", recognizer, enhancer)

    assert (result.start, result.end) == (0, 4)
    assert result.score == pytest.approx(0.65)


def test_when_window_ends_inside_a_word_then_whole_word_phrase_does_not_match(
    spacy_nlp_engine,
):
    # spaCy splits "10km" into "10" and "km", so the window ends after "10"
    recognizer = _licence_recognizer(["foo 10"])
    enhancer = PhraseContextAwareEnhancer(
        context_prefix_count=0,
        context_suffix_count=2,
        context_matching_mode="whole_word",
    )

    result = _enhance_one(spacy_nlp_engine, "ABC12345 foo 10km", recognizer, enhancer)

    assert result.score == pytest.approx(0.3)


@pytest.mark.parametrize("prefix_count, suffix_count", [(-1, 0), (5, -1), (-1, -1)])
def test_when_window_count_is_negative_then_no_error(
    spacy_nlp_engine, prefix_count, suffix_count
):
    recognizer = _licence_recognizer(["driving licence"])
    enhancer = PhraseContextAwareEnhancer(
        context_prefix_count=prefix_count, context_suffix_count=suffix_count
    )

    result = _enhance_one(
        spacy_nlp_engine, "driving licence ABC12345", recognizer, enhancer
    )

    expected = 0.65 if prefix_count >= 0 else 0.3
    assert result.score == pytest.approx(expected)


@pytest.mark.parametrize(
    "phrase, expected_score",
    [("driver's lic. (uk)", 0.65), ("driver.s lic", 0.3)],
)
def test_when_phrase_has_regex_characters_then_matched_literally(
    spacy_nlp_engine, phrase, expected_score
):
    result = _enhance_one(
        spacy_nlp_engine,
        "my driver's lic. (uk) ABC12345",
        _licence_recognizer([phrase]),
        PhraseContextAwareEnhancer(),
    )

    assert result.score == pytest.approx(expected_score)


@pytest.mark.parametrize("matching_mode", ["substring", "whole_word"])
@pytest.mark.parametrize(
    "text, phrase",
    [
        ("My driving licences: ABC12345", "driving licence"),
        ("My driving  licences: ABC12345", "driving licence"),
        ("My driving\tlicences: ABC12345", "driving licence"),
        ("My driving\nlicences: ABC12345", "driving licence"),
        ("Two women drivers: ABC12345", "woman driver"),
        ("My driver's licences: ABC12345", "driver's licence"),
        ("My driver\u2019s licence: ABC12345", "driver's licence"),
        ("My driver\u2019s licences: ABC12345", "driver's licence"),
        ("My driver's licences: ABC12345", "driver\u2019s licence"),
        ("My driver's-licences: ABC12345", "driver's licence"),
        ("My driver\u2019s-licences: ABC12345", "driver's licence"),
        ("My driving-licence is ABC12345", "driving licence"),
        ("My driving - licence is ABC12345", "driving licence"),
        ("zip/code ABC12345", "zip code"),
    ],
)
def test_when_phrase_is_inflected_or_hyphenated_then_score_enhanced(
    spacy_nlp_engine, text, phrase, matching_mode
):
    result = _enhance_one(
        spacy_nlp_engine,
        text,
        _licence_recognizer([phrase]),
        PhraseContextAwareEnhancer(context_matching_mode=matching_mode),
    )

    assert result.score == pytest.approx(0.65)
    assert result.analysis_explanation.supportive_context_word == phrase


@pytest.mark.parametrize("text", ["my pag-ibig no ABC12345", "my pag ibig no ABC12345"])
def test_when_context_word_has_a_hyphen_then_it_matches_as_a_phrase(
    spacy_nlp_engine, text
):
    # spaCy splits "pag-ibig" into "pag", "-" and "ibig", so no lemma equals it
    result = _enhance_one(
        spacy_nlp_engine,
        text,
        _licence_recognizer(["pag-ibig"]),
        PhraseContextAwareEnhancer(),
    )

    assert result.score == pytest.approx(0.65)


@pytest.mark.parametrize("matching_mode", ["substring", "whole_word"])
@pytest.mark.parametrize(
    "context_word, text",
    [("st-nr", "first nr ABC12345"), ("ust-id", "just id ABC12345")],
)
def test_when_phrase_starts_inside_a_word_then_score_not_enhanced(
    spacy_nlp_engine, context_word, text, matching_mode
):
    result = _enhance_one(
        spacy_nlp_engine,
        text,
        _licence_recognizer([context_word]),
        PhraseContextAwareEnhancer(context_matching_mode=matching_mode),
    )

    assert result.score == pytest.approx(0.3)


def test_when_suffix_count_is_zero_then_phrase_after_long_entity_does_not_count(
    spacy_nlp_engine,
):
    recognizer = _licence_recognizer(
        ["national insurance"], r"\bAB \d{2} \d{2} \d{2} C\b"
    )

    result = _enhance_one(
        spacy_nlp_engine,
        "AB 12 34 56 C national insurance",
        recognizer,
        PhraseContextAwareEnhancer(),
    )

    assert result.score == pytest.approx(0.3)


def test_when_context_word_is_one_word_then_it_is_left_to_the_lemma_enhancer(
    spacy_nlp_engine,
):
    # "women" is no lemma of "woman", but the phrase enhancer skips single words
    result = _enhance_one(
        spacy_nlp_engine,
        "Two women: ABC12345",
        _licence_recognizer(["women"]),
        PhraseContextAwareEnhancer(),
    )

    assert result.score == pytest.approx(0.3)
    assert result.analysis_explanation.supportive_context_word == ""


def test_when_result_already_enhanced_by_recognizer_then_skipped(spacy_nlp_engine):
    from presidio_analyzer import RecognizerResult

    text = "My driving licence is ABC12345"
    recognizer = _licence_recognizer(["driving licence"])
    nlp_artifacts = spacy_nlp_engine.process_text(text, "en")
    results = recognizer.analyze(text, recognizer.supported_entities, nlp_artifacts)
    results[0].recognition_metadata[
        RecognizerResult.IS_SCORE_ENHANCED_BY_CONTEXT_KEY
    ] = True

    enhanced = PhraseContextAwareEnhancer().enhance_using_context(
        text, results, nlp_artifacts, [recognizer]
    )

    assert enhanced[0].score == pytest.approx(0.3)


def test_when_enhancing_then_input_results_are_not_changed(spacy_nlp_engine):
    text = "My driving licence is ABC12345"
    recognizer = _licence_recognizer(["driving licence"])
    nlp_artifacts = spacy_nlp_engine.process_text(text, "en")
    results = recognizer.analyze(text, recognizer.supported_entities, nlp_artifacts)

    enhanced = PhraseContextAwareEnhancer().enhance_using_context(
        text, results, nlp_artifacts, [recognizer]
    )

    assert enhanced[0].score == pytest.approx(0.65)
    assert results[0].score == pytest.approx(0.3)
    assert results[0].analysis_explanation.supportive_context_word == ""


def test_when_nlp_artifacts_have_no_tokens_then_score_unchanged():
    from presidio_analyzer.nlp_engine import NlpArtifacts

    text = "My driving licence is ABC12345"
    recognizer = _licence_recognizer(["driving licence"])
    nlp_artifacts = NlpArtifacts([], [], [], [], None, "en")
    results = recognizer.analyze(text, recognizer.supported_entities, nlp_artifacts)

    enhanced = PhraseContextAwareEnhancer().enhance_using_context(
        text, results, nlp_artifacts, [recognizer]
    )

    assert enhanced[0].score == pytest.approx(0.3)


@pytest.mark.parametrize(
    "text, prefix_count, suffix_count",
    [
        ("Filed today: my driving licence number is ABC12345 and more text", 5, 0),
        ("Filed today: my driving licence number is ABC12345 and more text", 1, 2),
        ("Filed: the my driving licence number, is ABC12345 , and the text", 2, 2),
        ("ABC12345", 5, 5),
    ],
)
def test_context_window_covers_the_tokens_of_the_lemma_context(
    spacy_nlp_engine, text, prefix_count, suffix_count
):
    from presidio_analyzer import LemmaContextAwareEnhancer

    nlp_artifacts = spacy_nlp_engine.process_text(text, "en")
    settings = dict(
        context_prefix_count=prefix_count, context_suffix_count=suffix_count
    )
    start = text.index("ABC12345")

    first, last = PhraseContextAwareEnhancer(**settings)._get_context_window(
        nlp_artifacts, start
    )
    words = LemmaContextAwareEnhancer(**settings)._extract_surrounding_words(
        nlp_artifacts, "ABC12345", start
    )

    in_window = {nlp_artifacts.lemmas[i].lower() for i in range(first, last + 1)} & set(
        nlp_artifacts.keywords
    )
    assert set(words) == in_window
    # the window ends at a keyword, or at the edge of the text
    for edge, count in ((first, prefix_count), (last, suffix_count)):
        assert (
            nlp_artifacts.lemmas[edge].lower() in nlp_artifacts.keywords
            or edge in (0, len(nlp_artifacts.tokens) - 1)
            or count == 0
        )
