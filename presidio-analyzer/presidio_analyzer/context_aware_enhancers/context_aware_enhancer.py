import logging
from abc import abstractmethod
from bisect import bisect_right
from typing import Iterator, List, Optional, Set, Tuple

from presidio_analyzer import EntityRecognizer, RecognizerResult
from presidio_analyzer.nlp_engine import NlpArtifacts

logger = logging.getLogger("presidio-analyzer")


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

    def _enhance_in_place(
        self,
        text: str,
        results: List[RecognizerResult],
        nlp_artifacts: NlpArtifacts,
        recognizers: List[EntityRecognizer],
        context: Optional[List[str]] = None,
    ) -> Set[int]:
        """
        Enhance results in place; return the positions whose context matched.

        `CompositeContextAwareEnhancer` calls this so that it copies the results
        once for all its enhancers. This default runs `enhance_using_context` and
        copies its results back; a result whose score, supportive context word
        or `IS_SCORE_ENHANCED_BY_CONTEXT_KEY` changed counts as matched.

        :param text: The actual text that was analyzed
        :param results: Recognizer results, updated in place
        :param nlp_artifacts: The nlp artifacts of the analyzed text
        :param recognizers: the list of recognizers
        :param context: list of context words
        """

        def state(result: RecognizerResult) -> Tuple:
            explanation = result.analysis_explanation
            metadata = result.recognition_metadata or {}
            return (
                result.score,
                explanation.supportive_context_word if explanation else "",
                metadata.get(RecognizerResult.IS_SCORE_ENHANCED_BY_CONTEXT_KEY),
            )

        before = [state(result) for result in results]
        enhanced = self.enhance_using_context(
            text, results, nlp_artifacts, recognizers, context
        )
        # compared with the count before the call, as the child may change the
        # list it was given
        if len(enhanced) != len(before):
            raise ValueError(
                f"{type(self).__name__}.enhance_using_context returned "
                f"{len(enhanced)} results for {len(before)}; an enhancer inside "
                "CompositeContextAwareEnhancer must return one result per input."
            )
        results[:] = enhanced
        return {i for i, result in enumerate(results) if state(result) != before[i]}

    def _get_context_window(
        self, nlp_artifacts: NlpArtifacts, start: int
    ) -> Optional[Tuple[int, int]]:
        """Return the indices of the first and last token of the context window.

        The window holds the tokens that `LemmaContextAwareEnhancer` takes its
        context lemmas from: from `_find_entity_first_token`, back over
        `context_prefix_count` keywords and forward over `context_suffix_count`
        keywords, where the entity's own token counts as one keyword more in
        each direction.

        :param nlp_artifacts: the NLP artifacts of the analyzed text
        :param start: the start index of the entity in the original text
        :return: None when the text has no tokens or the window is empty
        """
        if not nlp_artifacts.tokens:
            return None
        first = self._find_entity_first_token(nlp_artifacts, start)
        lemmas = nlp_artifacts.lemmas
        keywords = nlp_artifacts.keywords
        visited = [
            *self._walk_context_tokens(
                first, self.context_prefix_count, lemmas, keywords, -1
            ),
            *self._walk_context_tokens(
                first, self.context_suffix_count, lemmas, keywords, 1
            ),
        ]
        if not visited:
            return None
        return min(visited), max(visited)

    @staticmethod
    def _find_entity_first_token(nlp_artifacts: NlpArtifacts, start: int) -> int:
        """Return the index of the first token that ends after `start`.

        This is the token `LemmaContextAwareEnhancer` counts its context window
        from. Tokens are sorted and do not overlap, so a binary search over
        their start offsets finds it.

        :param nlp_artifacts: the NLP artifacts of the analyzed text
        :param start: the start index of the entity in the original text
        """
        tokens = nlp_artifacts.tokens
        tokens_indices = nlp_artifacts.tokens_indices
        first = bisect_right(tokens_indices, start) - 1
        if first < 0 or tokens_indices[first] + len(tokens[first]) <= start:
            first += 1
        if first >= len(tokens):
            raise ValueError(
                f"Did not find a token at index {start} although it is "
                "expected to be found"
            )
        return first

    @staticmethod
    def _walk_context_tokens(
        index: int, n_words: int, lemmas: List[str], keywords: List[str], step: int
    ) -> Iterator[int]:
        """Yield the token indices from index until n_words + 1 keywords are seen.

        :param index: index of the token to start at
        :param n_words: number of keywords to take besides the starting token's
        :param lemmas: lemma of each token
        :param keywords: the lemmas that count as keywords
        :param step: -1 to walk to the preceding tokens, 1 to the following ones
        """
        i = index
        remaining = n_words + 1
        while 0 <= i < len(lemmas) and remaining > 0:
            yield i
            if lemmas[i].lower() in keywords:
                remaining -= 1
            i += step
