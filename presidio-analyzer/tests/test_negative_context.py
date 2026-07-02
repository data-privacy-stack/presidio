"""Tests for negative_context functionality in Presidio analyzer."""

import pytest
from presidio_analyzer import Pattern, PatternRecognizer
from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer

# Recognizer Tests: negative_context parameter and serialization


def test_negative_context_parameter_accepted():
    """Test that PatternRecognizer accepts negative_context parameter."""
    recognizer = PatternRecognizer(
        supported_entity="TEST_ENTITY",
        name="test_recognizer",
        patterns=[Pattern("test_pattern", r"\d{3}-\d{2}-\d{4}", 0.8)],
        context=["ssn"],
        negative_context=["test", "example"],
    )
    assert recognizer.negative_context == ["test", "example"]


def test_negative_context_defaults_to_empty_list():
    """Test that negative_context defaults to empty list when not provided."""
    recognizer = PatternRecognizer(
        supported_entity="TEST_ENTITY",
        name="test_recognizer",
        patterns=[Pattern("test_pattern", r"\d{3}-\d{2}-\d{4}", 0.8)],
    )
    assert recognizer.negative_context == []


def test_negative_context_serialization_to_dict():
    """Test that negative_context is included in to_dict() serialization."""
    recognizer = PatternRecognizer(
        supported_entity="TEST_ENTITY",
        name="test_recognizer",
        patterns=[Pattern("test_pattern", r"\d{3}-\d{2}-\d{4}", 0.8)],
        negative_context=["test", "example"],
    )
    serialized = recognizer.to_dict()
    assert "negative_context" in serialized
    assert serialized["negative_context"] == ["test", "example"]


def test_negative_context_deserialization_from_dict():
    """Test that negative_context is properly loaded via from_dict()."""
    config = {
        "supported_entity": "TEST_ENTITY",
        "name": "test_recognizer",
        "patterns": [
            {"name": "test_pattern", "regex": r"\d{3}-\d{2}-\d{4}", "score": 0.8}
        ],
        "negative_context": ["test", "example"],
    }
    recognizer = PatternRecognizer.from_dict(config)
    assert recognizer.negative_context == ["test", "example"]


def test_negative_context_deserialization_defaults_to_empty():
    """Test that negative_context defaults to empty list in from_dict()."""
    config = {
        "supported_entity": "TEST_ENTITY",
        "name": "test_recognizer",
        "patterns": [
            {"name": "test_pattern", "regex": r"\d{3}-\d{2}-\d{4}", "score": 0.8}
        ],
    }
    recognizer = PatternRecognizer.from_dict(config)
    assert recognizer.negative_context == []


# Enhancer Tests: negative_context_penalty parameter


def test_negative_context_penalty_parameter_accepted():
    """Test that LemmaContextAwareEnhancer accepts negative_context_penalty."""
    enhancer = LemmaContextAwareEnhancer(negative_context_penalty=0.5)
    assert enhancer.negative_context_penalty == 0.5


def test_negative_context_penalty_defaults_to_0_3():
    """Test that negative_context_penalty defaults to 0.3."""
    enhancer = LemmaContextAwareEnhancer()
    assert enhancer.negative_context_penalty == 0.3


# Enhancer Tests: matching logic


def test_find_supportive_word_substring_mode():
    """Test finding negative context words in substring mode."""
    context_list = ["test", "example", "sample"]
    negative_context_list = ["test", "example"]

    result = LemmaContextAwareEnhancer._find_supportive_word_in_context(
        context_list, negative_context_list, matching_mode="substring"
    )

    assert result == "test"


def test_find_supportive_word_whole_word_mode():
    """Test finding negative context words in whole_word mode."""
    context_list = ["test", "example", "sample"]
    negative_context_list = ["test", "example"]

    result = LemmaContextAwareEnhancer._find_supportive_word_in_context(
        context_list, negative_context_list, matching_mode="whole_word"
    )

    assert result == "test"


def test_find_supportive_word_no_match():
    """Test when negative context word is not found."""
    context_list = ["real", "document", "official"]
    negative_context_list = ["test", "example"]

    result = LemmaContextAwareEnhancer._find_supportive_word_in_context(
        context_list, negative_context_list, matching_mode="substring"
    )

    assert result == ""


# Integration Tests: score reduction with negative context


def test_negative_context_reduces_score(spacy_nlp_engine):
    """Test that negative context words reduce the confidence score."""
    recognizer = PatternRecognizer(
        supported_entity="TEST_SSN",
        name="test_ssn_recognizer",
        patterns=[Pattern("ssn_pattern", r"\d{3}-\d{2}-\d{4}", 0.9)],
        negative_context=["test", "example"],
    )

    text = "This is a test SSN: 123-45-6789"
    nlp_artifacts = spacy_nlp_engine.process_text(text, "en")

    results = recognizer.analyze(text=text, entities=[], nlp_artifacts=nlp_artifacts)
    assert len(results) > 0
    original_score = results[0].score

    enhancer = LemmaContextAwareEnhancer(negative_context_penalty=0.3)
    enhanced_results = enhancer.enhance_using_context(
        text, results, nlp_artifacts, [recognizer]
    )

    assert enhanced_results[0].score < original_score
    expected_score = max(original_score - 0.3, 0)
    assert enhanced_results[0].score == pytest.approx(expected_score)


def test_negative_context_prevents_false_positives(spacy_nlp_engine):
    """Test that negative context can prevent weak matches."""
    recognizer = PatternRecognizer(
        supported_entity="TEST_SSN",
        name="test_ssn_recognizer",
        patterns=[Pattern("ssn_pattern", r"\d{3}-\d{2}-\d{4}", 0.7)],
        negative_context=["example", "sample"],
    )

    text = "Example SSN for testing: 123-45-6789"
    nlp_artifacts = spacy_nlp_engine.process_text(text, "en")

    results = recognizer.analyze(text=text, entities=[], nlp_artifacts=nlp_artifacts)
    original_score = results[0].score

    enhancer = LemmaContextAwareEnhancer(negative_context_penalty=0.5)
    enhanced_results = enhancer.enhance_using_context(
        text, results, nlp_artifacts, [recognizer]
    )

    assert enhanced_results[0].score < original_score
    assert enhanced_results[0].score == pytest.approx(0.2)


def test_negative_context_penalty_clamped_to_min_score(spacy_nlp_engine):
    """Test that score never goes below MIN_SCORE (0)."""
    recognizer = PatternRecognizer(
        supported_entity="TEST_SSN",
        name="test_ssn_recognizer",
        patterns=[Pattern("ssn_pattern", r"\d{3}-\d{2}-\d{4}", 0.1)],
        negative_context=["test"],
    )

    text = "This is a test SSN: 123-45-6789"
    nlp_artifacts = spacy_nlp_engine.process_text(text, "en")

    results = recognizer.analyze(text=text, entities=[], nlp_artifacts=nlp_artifacts)

    enhancer = LemmaContextAwareEnhancer(negative_context_penalty=0.5)
    enhanced_results = enhancer.enhance_using_context(
        text, results, nlp_artifacts, [recognizer]
    )

    assert enhanced_results[0].score >= 0
    assert enhanced_results[0].score == pytest.approx(0)


# Integration Tests: interaction with positive context


def test_positive_context_unaffected_by_negative_context(spacy_nlp_engine):
    """Test that positive context is independent of negative context."""
    recognizer = PatternRecognizer(
        supported_entity="TEST_SSN",
        name="test_ssn_recognizer",
        patterns=[Pattern("ssn_pattern", r"\d{3}-\d{2}-\d{4}", 0.3)],
        context=["ssn", "social", "security"],
        negative_context=["test"],
    )

    text = "My social security number is 123-45-6789"
    nlp_artifacts = spacy_nlp_engine.process_text(text, "en")

    results = recognizer.analyze(text=text, entities=[], nlp_artifacts=nlp_artifacts)
    original_score = results[0].score

    enhancer = LemmaContextAwareEnhancer(
        context_similarity_factor=0.35, negative_context_penalty=0.3
    )
    enhanced_results = enhancer.enhance_using_context(
        text, results, nlp_artifacts, [recognizer]
    )

    assert enhanced_results[0].score > original_score


def test_negative_context_works_without_positive_context(spacy_nlp_engine):
    """Test that negative context works independently without positive context."""
    recognizer = PatternRecognizer(
        supported_entity="TEST_SSN",
        name="test_ssn_recognizer",
        patterns=[Pattern("ssn_pattern", r"\d{3}-\d{2}-\d{4}", 0.8)],
        negative_context=["test"],
    )

    text = "This is a test SSN: 123-45-6789"
    nlp_artifacts = spacy_nlp_engine.process_text(text, "en")

    results = recognizer.analyze(text=text, entities=[], nlp_artifacts=nlp_artifacts)
    original_score = results[0].score

    enhancer = LemmaContextAwareEnhancer(negative_context_penalty=0.3)
    enhanced_results = enhancer.enhance_using_context(
        text, results, nlp_artifacts, [recognizer]
    )

    assert enhanced_results[0].score < original_score


# Integration Tests: matching modes


def test_substring_matching_mode_matches_partial_words(spacy_nlp_engine):
    """Test negative context with substring matching mode."""
    recognizer = PatternRecognizer(
        supported_entity="TEST_ENTITY",
        name="test_recognizer",
        patterns=[Pattern("test_pattern", r"\d{3}-\d{2}-\d{4}", 0.8)],
        negative_context=["exam"],
    )

    text = "This is an example: 123-45-6789"
    nlp_artifacts = spacy_nlp_engine.process_text(text, "en")

    results = recognizer.analyze(text=text, entities=[], nlp_artifacts=nlp_artifacts)
    original_score = results[0].score

    enhancer = LemmaContextAwareEnhancer(
        context_matching_mode="substring", negative_context_penalty=0.3
    )
    enhanced_results = enhancer.enhance_using_context(
        text, results, nlp_artifacts, [recognizer]
    )

    assert enhanced_results[0].score < original_score


def test_whole_word_matching_mode_no_partial_match(spacy_nlp_engine):
    """Test negative context with whole_word matching mode."""
    recognizer = PatternRecognizer(
        supported_entity="TEST_ENTITY",
        name="test_recognizer",
        patterns=[Pattern("test_pattern", r"\d{3}-\d{2}-\d{4}", 0.8)],
        negative_context=["exam"],
    )

    text = "This is an example: 123-45-6789"
    nlp_artifacts = spacy_nlp_engine.process_text(text, "en")

    results = recognizer.analyze(text=text, entities=[], nlp_artifacts=nlp_artifacts)
    original_score = results[0].score

    enhancer = LemmaContextAwareEnhancer(
        context_matching_mode="whole_word", negative_context_penalty=0.3
    )
    enhanced_results = enhancer.enhance_using_context(
        text, results, nlp_artifacts, [recognizer]
    )

    assert enhanced_results[0].score == pytest.approx(original_score)


# Backward Compatibility Tests


def test_recognizer_without_negative_context_unchanged(spacy_nlp_engine):
    """Test that recognizers without negative_context work as before."""
    recognizer = PatternRecognizer(
        supported_entity="TEST_SSN",
        name="test_ssn_recognizer",
        patterns=[Pattern("ssn_pattern", r"\d{3}-\d{2}-\d{4}", 0.8)],
        context=["ssn"],
    )

    text = "My SSN is 123-45-6789"
    nlp_artifacts = spacy_nlp_engine.process_text(text, "en")

    results = recognizer.analyze(text=text, entities=[], nlp_artifacts=nlp_artifacts)
    original_score = results[0].score

    enhancer = LemmaContextAwareEnhancer()
    enhanced_results = enhancer.enhance_using_context(
        text, results, nlp_artifacts, [recognizer]
    )

    assert enhanced_results[0].score >= original_score


def test_empty_negative_context_no_penalty(spacy_nlp_engine):
    """Test that empty negative_context list doesn't cause issues."""
    recognizer = PatternRecognizer(
        supported_entity="TEST_SSN",
        name="test_ssn_recognizer",
        patterns=[Pattern("ssn_pattern", r"\d{3}-\d{2}-\d{4}", 0.8)],
        negative_context=[],
    )

    text = "My SSN is 123-45-6789"
    nlp_artifacts = spacy_nlp_engine.process_text(text, "en")

    results = recognizer.analyze(text=text, entities=[], nlp_artifacts=nlp_artifacts)
    original_score = results[0].score

    enhancer = LemmaContextAwareEnhancer()
    enhanced_results = enhancer.enhance_using_context(
        text, results, nlp_artifacts, [recognizer]
    )

    assert enhanced_results[0].score == pytest.approx(original_score)
