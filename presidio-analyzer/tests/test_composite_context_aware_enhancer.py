import copy

import pytest

from presidio_analyzer import (
    AnalyzerEngine,
    CompositeContextAwareEnhancer,
    ContextAwareEnhancer,
    LemmaContextAwareEnhancer,
    Pattern,
    PatternRecognizer,
    PhraseContextAwareEnhancer,
    RecognizerRegistry,
    RecognizerResult,
)
from presidio_analyzer.context_aware_enhancers import (
    composite_context_aware_enhancer,
)

TEXT = "My driving licence is ABC12345"


def _recognizer(context):
    return PatternRecognizer(
        supported_entity="TEST_LICENCE",
        name="test_licence_recognizer",
        context=context,
        patterns=[Pattern("test_pattern", r"\b[A-Z]{3}\d{5}\b", 0.3)],
    )


def _results(spacy_nlp_engine, recognizer, text=TEXT, count=1):
    nlp_artifacts = spacy_nlp_engine.process_text(text, "en")
    results = recognizer.analyze(text, recognizer.supported_entities, nlp_artifacts)
    assert len(results) == count
    return sorted(results, key=lambda r: r.start), nlp_artifacts


def _enhance(spacy_nlp_engine, enhancer, recognizer, text=TEXT):
    results, nlp_artifacts = _results(spacy_nlp_engine, recognizer, text)
    return enhancer.enhance_using_context(text, results, nlp_artifacts, [recognizer])[0]


def _default():
    return CompositeContextAwareEnhancer(
        [LemmaContextAwareEnhancer(), PhraseContextAwareEnhancer()]
    )


@pytest.mark.parametrize(
    "lemma_factor, phrase_factor, order, expected_score, expected_word",
    [
        (0.35, 0.1, "lemma_first", 0.65, "licence"),
        (0.35, 0.1, "phrase_first", 0.4, "driving licence"),
    ],
)
def test_when_two_enhancers_match_then_only_the_first_enhances(
    spacy_nlp_engine, lemma_factor, phrase_factor, order, expected_score, expected_word
):
    lemma = LemmaContextAwareEnhancer(context_similarity_factor=lemma_factor)
    phrase = PhraseContextAwareEnhancer(context_similarity_factor=phrase_factor)
    enhancers = [lemma, phrase] if order == "lemma_first" else [phrase, lemma]

    result = _enhance(
        spacy_nlp_engine,
        CompositeContextAwareEnhancer(enhancers),
        _recognizer(["driving licence", "licence"]),
    )

    assert result.score == pytest.approx(expected_score)
    assert result.analysis_explanation.supportive_context_word == expected_word
    assert result.analysis_explanation.score_context_improvement == pytest.approx(
        expected_score - 0.3
    )


def test_when_a_match_leaves_the_score_unchanged_then_later_enhancers_skip_it(
    spacy_nlp_engine,
):
    lemma = LemmaContextAwareEnhancer(
        context_similarity_factor=0, min_score_with_context_similarity=0
    )

    result = _enhance(
        spacy_nlp_engine,
        CompositeContextAwareEnhancer([lemma, PhraseContextAwareEnhancer()]),
        _recognizer(["driving licence", "licence"]),
    )

    assert result.score == pytest.approx(0.3)
    assert result.analysis_explanation.supportive_context_word == "licence"


def test_when_the_first_enhancer_misses_then_the_next_one_enhances(spacy_nlp_engine):
    result = _enhance(spacy_nlp_engine, _default(), _recognizer(["driving licence"]))

    assert result.score == pytest.approx(0.65)
    assert result.analysis_explanation.supportive_context_word == "driving licence"


def test_when_result_already_enhanced_by_recognizer_then_no_enhancer_changes_it(
    spacy_nlp_engine,
):
    recognizer = _recognizer(["driving licence", "licence"])
    results, nlp_artifacts = _results(spacy_nlp_engine, recognizer)
    results[0].recognition_metadata[
        RecognizerResult.IS_SCORE_ENHANCED_BY_CONTEXT_KEY
    ] = True

    enhanced = _default().enhance_using_context(
        TEXT, results, nlp_artifacts, [recognizer]
    )

    assert enhanced[0].score == pytest.approx(0.3)


def test_when_several_results_then_each_is_enhanced_by_its_first_match(
    spacy_nlp_engine,
):
    text = "My driving licence is ABC12345, my licence is XYZ67890"
    recognizer = _recognizer(["driving licence", "licence"])
    lemma = LemmaContextAwareEnhancer(context_prefix_count=1)
    phrase = PhraseContextAwareEnhancer(context_prefix_count=3)
    results, nlp_artifacts = _results(spacy_nlp_engine, recognizer, text, count=2)

    enhanced = CompositeContextAwareEnhancer([phrase, lemma]).enhance_using_context(
        text, results, nlp_artifacts, [recognizer]
    )

    words = [r.analysis_explanation.supportive_context_word for r in enhanced]
    assert [r.start for r in enhanced] == [r.start for r in results]
    assert words == ["driving licence", "licence"]


def test_when_enhancing_then_results_are_copied_once(spacy_nlp_engine, monkeypatch):
    recognizer = _recognizer(["driving licence"])
    results, nlp_artifacts = _results(spacy_nlp_engine, recognizer)
    original = copy.deepcopy(results)
    copies = []
    deepcopy = copy.deepcopy

    def counting_deepcopy(value):
        copies.append(value)
        return deepcopy(value)

    # the copy module is shared, so this counts the copies of every enhancer
    monkeypatch.setattr(
        composite_context_aware_enhancer.copy, "deepcopy", counting_deepcopy
    )
    enhanced = _default().enhance_using_context(
        TEXT, results, nlp_artifacts, [recognizer]
    )
    monkeypatch.undo()

    assert len(copies) == 1
    assert enhanced[0].score == pytest.approx(0.65)
    assert enhanced[0] is not results[0]
    assert results[0].score == original[0].score
    assert results[0].analysis_explanation.supportive_context_word == ""


class _LicenceContextLemmaEnhancer(LemmaContextAwareEnhancer):
    """Overrides only the public method, as a subclass written before composites."""

    def enhance_using_context(
        self, text, raw_results, nlp_artifacts, recognizers, context=None
    ):
        return super().enhance_using_context(
            text, raw_results, nlp_artifacts, recognizers, ["LICENCE"]
        )


def test_when_subclass_overrides_enhance_using_context_then_composite_calls_it(
    spacy_nlp_engine,
):
    # "permit" is nowhere in the text: only the override's context finds it
    recognizer = _recognizer(["licence"])
    enhancer = CompositeContextAwareEnhancer(
        [_LicenceContextLemmaEnhancer(context_matching_mode="substring")]
    )

    result = _enhance(spacy_nlp_engine, enhancer, recognizer, "My permit ABC12345")

    assert result.score == pytest.approx(0.65)
    assert result.analysis_explanation.supportive_context_word == "licence"


class _ConstantEnhancer(ContextAwareEnhancer):
    """A custom enhancer that sets every result's supportive word."""

    def __init__(self, word):
        super().__init__(0.2, 0, 5, 0)
        self.word = word

    def enhance_using_context(
        self, text, raw_results, nlp_artifacts, recognizers, context=None
    ):
        results = copy.deepcopy(raw_results)
        for result in results:
            result.score += self.context_similarity_factor
            result.analysis_explanation.set_supportive_context_word(self.word)
        return results


class _MixinEnhanceUsingContext:
    def enhance_using_context(
        self, text, raw_results, nlp_artifacts, recognizers, context=None
    ):
        return super().enhance_using_context(
            text, raw_results, nlp_artifacts, recognizers, ["LICENCE"]
        )


class _MixinLemmaEnhancer(_MixinEnhanceUsingContext, LemmaContextAwareEnhancer):
    pass


class _ScoreOnlyEnhancer(ContextAwareEnhancer):
    """A custom enhancer that raises scores without a supportive word."""

    def __init__(self):
        super().__init__(0.2, 0, 5, 0)

    def enhance_using_context(
        self, text, raw_results, nlp_artifacts, recognizers, context=None
    ):
        results = copy.deepcopy(raw_results)
        for result in results:
            result.score += self.context_similarity_factor
        return results


def test_when_mixin_overrides_enhance_using_context_then_composite_calls_it(
    spacy_nlp_engine,
):
    enhancer = CompositeContextAwareEnhancer([_MixinLemmaEnhancer()])

    result = _enhance(
        spacy_nlp_engine, enhancer, _recognizer(["licence"]), "My permit ABC12345"
    )

    assert result.score == pytest.approx(0.65)


def test_when_custom_enhancer_changes_only_the_score_then_later_ones_skip_it(
    spacy_nlp_engine,
):
    enhancer = CompositeContextAwareEnhancer(
        [_ScoreOnlyEnhancer(), LemmaContextAwareEnhancer()]
    )

    result = _enhance(spacy_nlp_engine, enhancer, _recognizer(["licence"]))

    assert result.score == pytest.approx(0.5)


def test_when_custom_enhancer_matches_then_later_enhancers_skip_the_result(
    spacy_nlp_engine,
):
    enhancer = CompositeContextAwareEnhancer(
        [_ConstantEnhancer("custom"), LemmaContextAwareEnhancer()]
    )

    result = _enhance(spacy_nlp_engine, enhancer, _recognizer(["licence"]))

    assert result.score == pytest.approx(0.5)
    assert result.analysis_explanation.supportive_context_word == "custom"


class _DroppingEnhancer(ContextAwareEnhancer):
    def __init__(self):
        super().__init__(0.35, 0.4, 5, 0)

    def enhance_using_context(
        self, text, raw_results, nlp_artifacts, recognizers, context=None
    ):
        return []


class _ClearingEnhancer(_DroppingEnhancer):
    def enhance_using_context(
        self, text, raw_results, nlp_artifacts, recognizers, context=None
    ):
        raw_results.clear()
        return raw_results


@pytest.mark.parametrize("enhancer_class", [_DroppingEnhancer, _ClearingEnhancer])
def test_when_custom_enhancer_drops_results_then_composite_raises(
    spacy_nlp_engine, enhancer_class
):
    enhancer = CompositeContextAwareEnhancer([enhancer_class()])

    with pytest.raises(ValueError, match="one result per input"):
        _enhance(spacy_nlp_engine, enhancer, _recognizer(["licence"]))


def test_when_no_enhancers_then_results_are_unchanged(spacy_nlp_engine):
    result = _enhance(
        spacy_nlp_engine, CompositeContextAwareEnhancer([]), _recognizer(["licence"])
    )

    assert result.score == pytest.approx(0.3)


@pytest.mark.parametrize("context", [["insurance"], ["national insurance"]])
def test_when_entity_has_several_tokens_then_suffix_window_still_counts_from_first(
    spacy_nlp_engine, context
):
    # the suffix window counts the entity's own tokens, as on main; a fallback
    # that counts from the entity's last token belongs in a separate change
    recognizer = PatternRecognizer(
        supported_entity="TEST_NINO",
        context=context,
        patterns=[Pattern("nino", r"\bAB \d{2} \d{2} \d{2} C\b", 0.3)],
    )
    text = "AB 12 34 56 C is my national insurance"
    lemma = LemmaContextAwareEnhancer(context_suffix_count=3)
    phrase = PhraseContextAwareEnhancer(context_suffix_count=3)

    for enhancer in (lemma, CompositeContextAwareEnhancer([lemma, phrase])):
        result = _enhance(spacy_nlp_engine, enhancer, recognizer, text)
        assert result.score == pytest.approx(0.3)


def test_when_single_word_context_also_matches_then_it_stays_supportive_word(
    spacy_nlp_engine,
):
    result = _enhance(
        spacy_nlp_engine, _default(), _recognizer(["driving licence", "licence"])
    )

    assert result.score == pytest.approx(0.65)
    assert result.analysis_explanation.supportive_context_word == "licence"


@pytest.mark.parametrize(
    "recognizer_name, text, start, end",
    [
        (
            "UkDrivingLicenceRecognizer",
            "My driving licence number is MORGA753116SM9IJ.",
            29,
            45,
        ),
        ("UkNinoRecognizer", "His national insurance is AB 12 34 56 C.", 26, 39),
    ],
)
def test_when_predefined_multi_word_context_precedes_entity_then_score_enhanced(
    spacy_nlp_engine, recognizer_name, text, start, end
):
    from presidio_analyzer import predefined_recognizers

    recognizer = getattr(predefined_recognizers, recognizer_name)()
    control_text = "Reference " + text[start:end] + " was filed."

    result = _enhance(spacy_nlp_engine, _default(), recognizer, text)
    lemma_only = _enhance(
        spacy_nlp_engine, LemmaContextAwareEnhancer(), recognizer, text
    )
    control = _enhance(spacy_nlp_engine, _default(), recognizer, control_text)

    assert (result.start, result.end) == (start, end)
    assert result.score == pytest.approx(0.85)
    assert result.analysis_explanation.score_context_improvement == pytest.approx(0.35)
    assert lemma_only.score == pytest.approx(0.5)
    assert control.score == pytest.approx(0.5)
    assert control.analysis_explanation.supportive_context_word == ""


def test_when_multi_word_context_precedes_entity_then_result_passes_threshold(
    spacy_nlp_engine,
):
    from presidio_analyzer.predefined_recognizers import UkDrivingLicenceRecognizer

    registry = RecognizerRegistry(recognizers=[UkDrivingLicenceRecognizer()])
    engine = AnalyzerEngine(registry=registry, nlp_engine=spacy_nlp_engine)
    lemma_engine = AnalyzerEngine(
        registry=registry,
        nlp_engine=spacy_nlp_engine,
        context_aware_enhancer=LemmaContextAwareEnhancer(),
    )
    text = "My driving licence number is MORGA753116SM9IJ."

    with_phrase = engine.analyze(text, language="en", score_threshold=0.6)
    lemma_only = lemma_engine.analyze(text, language="en", score_threshold=0.6)
    without_phrase = engine.analyze(
        "Reference MORGA753116SM9IJ was filed.", language="en", score_threshold=0.6
    )

    assert isinstance(engine.context_aware_enhancer, CompositeContextAwareEnhancer)
    assert [(r.entity_type, r.start, r.end) for r in with_phrase] == [
        ("UK_DRIVING_LICENCE", 29, 45)
    ]
    assert with_phrase[0].score == pytest.approx(0.85)
    assert lemma_only == []
    assert without_phrase == []


class _BaseSettingsEnhancer(_ScoreOnlyEnhancer):
    """A custom enhancer class whose constructor takes only the base settings."""

    def __init__(
        self,
        context_similarity_factor,
        min_score_with_context_similarity,
        context_prefix_count,
        context_suffix_count,
    ):
        ContextAwareEnhancer.__init__(
            self,
            context_similarity_factor,
            min_score_with_context_similarity,
            context_prefix_count,
            context_suffix_count,
        )


def test_when_default_engine_then_enhancer_settings_are_readable():
    enhancer = AnalyzerEngine().context_aware_enhancer

    assert isinstance(enhancer, CompositeContextAwareEnhancer)
    assert enhancer.context_similarity_factor == 0.35
    assert enhancer.min_score_with_context_similarity == 0.4
    assert enhancer.context_prefix_count == 5
    assert enhancer.context_suffix_count == 0
    assert enhancer.context_matching_mode == "substring"


def test_when_enhancers_given_as_classes_then_built_with_composite_settings():
    composite = CompositeContextAwareEnhancer(
        [LemmaContextAwareEnhancer, PhraseContextAwareEnhancer, _BaseSettingsEnhancer],
        context_similarity_factor=0.2,
        min_score_with_context_similarity=0.5,
        context_prefix_count=3,
        context_suffix_count=2,
        context_matching_mode="whole_word",
    )

    lemma, phrase, custom = composite.enhancers
    assert type(lemma) is LemmaContextAwareEnhancer
    assert type(phrase) is PhraseContextAwareEnhancer
    assert type(custom) is _BaseSettingsEnhancer
    for enhancer in (composite, lemma, phrase, custom):
        assert enhancer.context_similarity_factor == 0.2
        assert enhancer.min_score_with_context_similarity == 0.5
        assert enhancer.context_prefix_count == 3
        assert enhancer.context_suffix_count == 2
    for enhancer in (composite, lemma, phrase):
        assert enhancer.context_matching_mode == "whole_word"
    assert not hasattr(custom, "context_matching_mode")


def test_when_enhancer_given_as_instance_then_its_own_settings_win():
    phrase = PhraseContextAwareEnhancer(
        context_prefix_count=7, context_matching_mode="whole_word"
    )
    composite = CompositeContextAwareEnhancer(
        [LemmaContextAwareEnhancer, phrase], context_prefix_count=2
    )

    lemma, same_phrase = composite.enhancers
    assert same_phrase is phrase
    assert phrase.context_prefix_count == 7
    assert phrase.context_matching_mode == "whole_word"
    assert lemma.context_prefix_count == 2
    assert lemma.context_matching_mode == "substring"


def test_when_composite_settings_given_then_class_children_use_them(
    spacy_nlp_engine,
):
    # "driving licence" is three words before the entity: out of a window of 2
    recognizer = _recognizer(["driving licence"])
    text = "My driving licence number is ABC12345"
    narrow = CompositeContextAwareEnhancer(
        [LemmaContextAwareEnhancer, PhraseContextAwareEnhancer],
        context_prefix_count=2,
    )

    assert _enhance(spacy_nlp_engine, narrow, recognizer, text).score == pytest.approx(
        0.3
    )
    assert _enhance(
        spacy_nlp_engine, _default(), recognizer, text
    ).score == pytest.approx(0.65)


def test_when_composite_matching_mode_invalid_then_raises():
    with pytest.raises(ValueError, match="context_matching_mode must be one of"):
        CompositeContextAwareEnhancer([], context_matching_mode="prefix")
