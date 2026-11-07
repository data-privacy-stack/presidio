import logging
from abc import abstractmethod
from typing import List, Optional

from presidio_analyzer import EntityRecognizer, RecognizerResult
from presidio_analyzer.nlp_engine import NlpArtifacts

logger = logging.getLogger("presidio-analyzer")

#: The context matching modes a recognizer or an enhancer may use.
CONTEXT_MATCHING_MODES = ("substring", "whole_word")


def resolve_context_matching_mode(
    recognizer: Optional[EntityRecognizer], default: str
) -> str:
    """
    Return the context matching mode to use for a recognizer's results.

    A recognizer may opt into a mode of its own through its
    ``CONTEXT_MATCHING_MODE`` class attribute; otherwise the enhancer's
    configured mode applies. This lets one recognizer match its context
    words as whole tokens only (e.g. ``"sin"`` must not match inside
    ``"business"``) without changing the default for every recognizer.

    :param recognizer: the recognizer the result belongs to, or None
    :param default: the enhancer's configured ``context_matching_mode``
    :return: ``"substring"`` or ``"whole_word"``
    :raises ValueError: if the recognizer declares an unknown mode
    """
    mode = getattr(recognizer, "CONTEXT_MATCHING_MODE", None) or default
    if mode not in CONTEXT_MATCHING_MODES:
        raise ValueError(
            f"context_matching_mode must be one of: 'substring', 'whole_word'. "
            f"Got: {mode!r} from {type(recognizer).__name__}."
        )
    return mode


class ContextAwareEnhancer:
    """
    A class representing an abstract context aware enhancer.

    Context words might enhance confidence score of a recognized entity,
    ContextAwareEnhancer is an abstract class to be inherited by a context aware
    enhancer logic.

    :param context_similarity_factor: How much to enhance confidence of match entity
    :param min_score_with_context_similarity: Minimum confidence score
    :param context_prefix_count: how many words before the entity to match context
    :param context_suffix_count: how many words after the entity to match context
    """

    MIN_SCORE = 0
    MAX_SCORE = 1.0

    def __init__(
        self,
        context_similarity_factor: float,
        min_score_with_context_similarity: float,
        context_prefix_count: int,
        context_suffix_count: int,
    ):
        self.context_similarity_factor = context_similarity_factor
        self.min_score_with_context_similarity = min_score_with_context_similarity
        self.context_prefix_count = context_prefix_count
        self.context_suffix_count = context_suffix_count

    @abstractmethod
    def enhance_using_context(
        self,
        text: str,
        raw_results: List[RecognizerResult],
        nlp_artifacts: NlpArtifacts,
        recognizers: List[EntityRecognizer],
        context: Optional[List[str]] = None,
    ) -> List[RecognizerResult]:
        """
        Update results in case surrounding words are relevant to the context words.

        Using the surrounding words of the actual word matches, look
        for specific strings that if found contribute to the score
        of the result, improving the confidence that the match is
        indeed of that PII entity type

        :param text: The actual text that was analyzed
        :param raw_results: Recognizer results which didn't take
                            context into consideration
        :param nlp_artifacts: The nlp artifacts contains elements
                              such as lemmatized tokens for better
                              accuracy of the context enhancement process
        :param recognizers: the list of recognizers
        :param context: list of context words
        """
        return raw_results
