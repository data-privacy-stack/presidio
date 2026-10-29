import copy
import inspect
import logging
from typing import List, Optional, Set, Type, Union

from presidio_analyzer import EntityRecognizer, RecognizerResult
from presidio_analyzer.context_aware_enhancers.context_aware_enhancer import (
    ContextAwareEnhancer,
)
from presidio_analyzer.nlp_engine import NlpArtifacts

logger = logging.getLogger("presidio-analyzer")


def _defining_class(cls: type, name: str) -> type:
    return next(klass for klass in cls.__mro__ if name in vars(klass))


class CompositeContextAwareEnhancer(ContextAwareEnhancer):
    """
    Run several context aware enhancers in order; the first match wins.

    Once an enhancer finds a supportive context word for a result, the later
    enhancers skip that result, so its score is enhanced at most once.
    The results are copied once for all the enhancers.

    An enhancer given as a class is built with the composite's settings; an
    instance is used as is, so its own settings win.

    :param enhancers: the enhancers to run, in order, as instances or classes
    :param context_similarity_factor: How much to enhance confidence of match entity
    :param min_score_with_context_similarity: Minimum confidence score
    :param context_prefix_count: how many words before the entity to match context
    :param context_suffix_count: how many words after the entity to match context
    :param context_matching_mode: "substring" or "whole_word", given to the
    enhancer classes whose constructor takes it
    """

    def __init__(
        self,
        enhancers: List[Union[ContextAwareEnhancer, Type[ContextAwareEnhancer]]],
        context_similarity_factor: float = 0.35,
        min_score_with_context_similarity: float = 0.4,
        context_prefix_count: int = 5,
        context_suffix_count: int = 0,
        context_matching_mode: str = "substring",
    ):
        settings = dict(
            context_similarity_factor=context_similarity_factor,
            min_score_with_context_similarity=min_score_with_context_similarity,
            context_prefix_count=context_prefix_count,
            context_suffix_count=context_suffix_count,
        )
        super().__init__(**settings)
        if context_matching_mode not in ["whole_word", "substring"]:
            raise ValueError(
                f"context_matching_mode must be one of: 'whole_word', 'substring'. "
                f"Got: {context_matching_mode}"
            )
        self.context_matching_mode = context_matching_mode
        self.enhancers = [
            self._build(enhancer, settings) if isinstance(enhancer, type) else enhancer
            for enhancer in enhancers
        ]

    def _build(
        self, enhancer_class: Type[ContextAwareEnhancer], settings: dict
    ) -> ContextAwareEnhancer:
        """Build an enhancer class with the composite's settings."""
        if "context_matching_mode" in inspect.signature(enhancer_class).parameters:
            settings = {**settings, "context_matching_mode": self.context_matching_mode}
        return enhancer_class(**settings)

    def enhance_using_context(
        self,
        text: str,
        raw_results: List[RecognizerResult],
        nlp_artifacts: NlpArtifacts,
        recognizers: List[EntityRecognizer],
        context: Optional[List[str]] = None,
    ) -> List[RecognizerResult]:
        """
        Update results with the first of the enhancers that finds context.

        :param text: The actual text that was analyzed
        :param raw_results: Recognizer results which didn't take
                            context into consideration
        :param nlp_artifacts: The nlp artifacts of the analyzed text
        :param recognizers: the list of recognizers
        :param context: list of context words
        """
        results = copy.deepcopy(raw_results)
        self._enhance_in_place(text, results, nlp_artifacts, recognizers, context)
        return results

    def _enhance_in_place(
        self,
        text: str,
        results: List[RecognizerResult],
        nlp_artifacts: NlpArtifacts,
        recognizers: List[EntityRecognizer],
        context: Optional[List[str]] = None,
    ) -> Set[int]:
        """Enhance results in place; return the positions whose context matched."""
        pending = list(range(len(results)))
        for enhancer in self.enhancers:
            if not pending:
                break
            subset = [results[i] for i in pending]
            args = (text, subset, nlp_artifacts, recognizers, context)
            if self._overrides_enhance_using_context(enhancer):
                # the base step runs its enhance_using_context, so the override
                # is not bypassed
                matched = ContextAwareEnhancer._enhance_in_place(enhancer, *args)
            else:
                matched = enhancer._enhance_in_place(*args)
            for i, result in zip(pending, subset):
                results[i] = result
            pending = [i for k, i in enumerate(pending) if k not in matched]
        return set(range(len(results))) - set(pending)

    @staticmethod
    def _overrides_enhance_using_context(enhancer: ContextAwareEnhancer) -> bool:
        """Check if enhance_using_context and _enhance_in_place differ in class.

        This is the case for a custom enhancer, and for a subclass of a built-in
        enhancer that overrides only enhance_using_context.
        """
        public = _defining_class(type(enhancer), "enhance_using_context")
        in_place = _defining_class(type(enhancer), "_enhance_in_place")
        return public is not in_place
