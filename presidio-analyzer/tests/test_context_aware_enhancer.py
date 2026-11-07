import pytest
from presidio_analyzer.context_aware_enhancers.context_aware_enhancer import (
    resolve_context_matching_mode,
)
from presidio_analyzer.predefined_recognizers import (
    CaSinRecognizer,
    UsSsnRecognizer,
)


def test_resolve_uses_recognizer_override():
    """A recognizer opting into whole-word matching wins over the default."""
    assert resolve_context_matching_mode(CaSinRecognizer(), "substring") == "whole_word"


def test_resolve_falls_back_to_enhancer_default():
    """Recognizers without an override use the enhancer's configured mode."""
    recognizer = UsSsnRecognizer()
    assert resolve_context_matching_mode(recognizer, "substring") == "substring"
    assert resolve_context_matching_mode(recognizer, "whole_word") == "whole_word"


def test_resolve_without_attribute_falls_back():
    """Objects predating CONTEXT_MATCHING_MODE use the enhancer default."""
    assert resolve_context_matching_mode(object(), "substring") == "substring"
    assert resolve_context_matching_mode(None, "whole_word") == "whole_word"


def test_resolve_rejects_unknown_mode():
    """A typo in a recognizer's CONTEXT_MATCHING_MODE must fail loudly."""

    class BadRecognizer:
        CONTEXT_MATCHING_MODE = "fuzzy"

    with pytest.raises(ValueError, match="context_matching_mode must be one of"):
        resolve_context_matching_mode(BadRecognizer(), "substring")
