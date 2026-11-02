import copy
import logging
import re
from functools import lru_cache
from typing import List, Optional, Set, Tuple

from presidio_analyzer import EntityRecognizer, RecognizerResult
from presidio_analyzer.context_aware_enhancers.context_aware_enhancer import (
    ContextAwareEnhancer,
)
from presidio_analyzer.nlp_engine import NlpArtifacts

logger = logging.getLogger("presidio-analyzer")


# Phrase words are split at whitespace, hyphens and slashes, and between two
# words of the text any whitespace, or one hyphen or slash, joins them:
# "driving licence" also matches "driving-licence", and "zip code" "zip/code".
_PHRASE_WORD_SEPARATOR = re.compile(r"[\s\-/]+")
_PHRASE_GAP = r"(?:\s+|\s*[-/]\s*)"
_PHRASE_GAP_RE = re.compile(_PHRASE_GAP)
_WORD_CHAR = re.compile(r"\w")
# A typographic apostrophe matches a straight one, in both directions.
_APOSTROPHE = str.maketrans("’", "'")
# spaCy splits a possessive "'s" off its word: "driver's" is "driver", "'s"
_POSSESSIVE = re.compile(r"(.+?)('s)")


@lru_cache(maxsize=1024)
def _phrase_words(phrase: str) -> Tuple[str, ...]:
    """Split a context phrase into its lowercase words."""
    phrase = phrase.lower().translate(_APOSTROPHE)
    return tuple(word for word in _PHRASE_WORD_SEPARATOR.split(phrase) if word)


@lru_cache(maxsize=1024)
def _phrase_tokens(phrase: str) -> Tuple[Tuple[Tuple[str, bool], ...], ...]:
    """Return the token sequences a context phrase can be tokenized into.

    Each token comes with whether it joins the previous one with no gap. A
    possessive word is one token or two: spaCy splits "driver's licence" but
    not "driver's-licence".
    """
    words = _phrase_words(phrase)
    unsplit = tuple((word, False) for word in words)
    split = []
    for word in words:
        possessive = _POSSESSIVE.fullmatch(word)
        if possessive:
            split.extend(((possessive[1], False), (possessive[2], True)))
        else:
            split.append((word, False))
    return (unsplit,) if len(split) == len(unsplit) else (unsplit, tuple(split))


@lru_cache(maxsize=1024)
def _compile_phrase(phrase: str, whole_word: bool) -> re.Pattern:
    """Compile a context phrase: its words in order, joined by a phrase gap.

    The phrase starts at a word boundary, so "st-nr" does not match "first nr";
    only "whole_word" also requires a word boundary after it.
    """
    pattern = _PHRASE_GAP.join(re.escape(word) for word in _phrase_words(phrase))
    pattern = rf"(?<!\w){pattern}".replace("'", "['’]")
    if whole_word:
        pattern = rf"{pattern}(?!\w)"
    return re.compile(pattern, re.IGNORECASE)


class PhraseContextAwareEnhancer(ContextAwareEnhancer):
    """
    A context aware enhancer for context words of several words.

    A context word that contains whitespace, a hyphen or a slash (e.g.
    'driving licence') cannot equal the lemma of one token, so
    `LemmaContextAwareEnhancer` never matches it. This enhancer looks such
    phrases up in the context window, outside the entity itself, and leaves
    context words of one word to the lemma enhancer.

    A phrase matches its words in order, case-insensitively, separated by
    whitespace or by one hyphen or slash, starting at a word boundary.
    It also matches consecutive tokens whose text or lemma equals each word
    ('woman driver' matches 'women drivers'). A typographic apostrophe matches
    a straight one, and a possessive "'s" may be its own token.

    :param context_similarity_factor: How much to enhance confidence of match entity
    :param min_score_with_context_similarity: Minimum confidence score
    :param context_prefix_count: how many words before the entity to match context
    :param context_suffix_count: how many words after the entity to match context
    :param context_matching_mode: "substring" (default) or "whole_word".
        In the text, "whole_word" also requires a word boundary after the
        phrase. The token match compares whole tokens in both modes.
    """

    def __init__(
        self,
        context_similarity_factor: float = 0.35,
        min_score_with_context_similarity: float = 0.4,
        context_prefix_count: int = 5,
        context_suffix_count: int = 0,
        context_matching_mode: str = "substring",
    ):
        super().__init__(
            context_similarity_factor=context_similarity_factor,
            min_score_with_context_similarity=min_score_with_context_similarity,
            context_prefix_count=context_prefix_count,
            context_suffix_count=context_suffix_count,
        )
        if context_matching_mode not in ["whole_word", "substring"]:
            raise ValueError(
                f"context_matching_mode must be one of: 'whole_word', 'substring'. "
                f"Got: {context_matching_mode}"
            )
        self.context_matching_mode = context_matching_mode

    def enhance_using_context(
        self,
        text: str,
        raw_results: List[RecognizerResult],
        nlp_artifacts: NlpArtifacts,
        recognizers: List[EntityRecognizer],
        context: Optional[List[str]] = None,
    ) -> List[RecognizerResult]:
        """
        Update results whose recognizer context phrases occur near the entity.

        :param text: The actual text that was analyzed
        :param raw_results: Recognizer results which didn't take
                            context into consideration
        :param nlp_artifacts: The nlp artifacts of the analyzed text
        :param recognizers: the list of recognizers
        :param context: list of context words. Not used: the context window
                        of the text is searched only.
        """  # noqa: D205,D400
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
        matched = set()
        if nlp_artifacts is None or not nlp_artifacts.tokens:
            return matched

        # each recognizer's context words of several words
        phrases_dict = {
            recognizer.id: [
                word
                for word in recognizer.context or []
                if len(_phrase_words(word)) > 1
            ]
            for recognizer in recognizers
        }
        for i, result in enumerate(results):
            metadata = result.recognition_metadata or {}
            phrases = phrases_dict.get(
                metadata.get(RecognizerResult.RECOGNIZER_IDENTIFIER_KEY)
            )
            # skip results already boosted at recognizer level
            if not phrases or metadata.get(
                RecognizerResult.IS_SCORE_ENHANCED_BY_CONTEXT_KEY
            ):
                continue
            window = self._get_context_window(nlp_artifacts, result.start)
            if not window:
                continue
            phrase = self._find_supportive_phrase_in_window(
                text, nlp_artifacts, window, result, phrases
            )
            if phrase:
                result.score += self.context_similarity_factor
                result.score = max(result.score, self.min_score_with_context_similarity)
                result.score = min(result.score, ContextAwareEnhancer.MAX_SCORE)
                result.analysis_explanation.set_supportive_context_word(phrase)
                result.analysis_explanation.set_improved_score(result.score)
                matched.add(i)
        return matched

    def _find_supportive_phrase_in_window(
        self,
        text: str,
        nlp_artifacts: NlpArtifacts,
        window: Tuple[int, int],
        result: RecognizerResult,
        phrases: List[str],
    ) -> str:
        """
        Find a context word of several words in the context window.

        Such a phrase never equals a single lemma, so it is matched against the
        original text of the window, and also against the text or lemma of its
        consecutive tokens. A match that overlaps the entity itself does not
        count.

        :param text: the analyzed text
        :param nlp_artifacts: the NLP artifacts of the analyzed text
        :param window: indices of the first and last token of the window
        :param result: the recognized entity
        :param phrases: the recognizer's context words of several words
        :return: the first matching phrase, or an empty string
        """
        tokens = nlp_artifacts.tokens
        tokens_indices = nlp_artifacts.tokens_indices
        window_start = tokens_indices[window[0]]
        window_end = tokens_indices[window[1]] + len(tokens[window[1]])
        whole_word = self.context_matching_mode == "whole_word"
        window_words = None
        for phrase in phrases:
            if self._phrase_in_window_text(
                text, window_start, window_end, result, phrase, whole_word
            ):
                return phrase
            if window_words is None:
                # (index, lowercase text, lowercase lemma) of each token,
                # without the whitespace, hyphen and slash tokens a phrase
                # gap holds
                window_words = [
                    (
                        i,
                        str(tokens[i]).lower().translate(_APOSTROPHE),
                        nlp_artifacts.lemmas[i].lower().translate(_APOSTROPHE),
                    )
                    for i in range(window[0], window[1] + 1)
                    if str(tokens[i]) not in ("-", "/") and not str(tokens[i]).isspace()
                ]
            if self._phrase_in_window_tokens(
                text, nlp_artifacts, window_words, result, phrase
            ):
                return phrase
        return ""

    @staticmethod
    def _phrase_in_window_text(
        text: str,
        window_start: int,
        window_end: int,
        result: RecognizerResult,
        phrase: str,
        whole_word: bool,
    ) -> bool:
        """Check if a phrase occurs in the original text of the context window.

        :param text: the analyzed text
        :param window_start: start offset of the context window in the text
        :param window_end: end offset of the context window in the text
        :param result: the recognized entity
        :param phrase: a context word of several words
        :param whole_word: whether the phrase needs word boundaries around it
        """
        pattern = _compile_phrase(phrase, whole_word)
        # One character past the window lets a word boundary see the next
        # character; a match ending there is outside the window. Search again
        # one character on, as a rejected match can overlap a valid one.
        end_pos = window_end + 1
        match = pattern.search(text, window_start, end_pos)
        while match:
            if match.end() <= window_end and (
                match.end() <= result.start or match.start() >= result.end
            ):
                logger.debug("Found context phrase '%s'", phrase)
                return True
            match = pattern.search(text, match.start() + 1, end_pos)
        return False

    @staticmethod
    def _phrase_in_window_tokens(
        text: str,
        nlp_artifacts: NlpArtifacts,
        window_words: List[Tuple[int, str, str]],
        result: RecognizerResult,
        phrase: str,
    ) -> bool:
        """Check if consecutive window tokens spell the phrase by text or lemma.

        Each phrase word must equal the text or the lemma of its token (as a
        single context word equals a lemma), and only a phrase gap may lie
        between two tokens; a possessive "'s" may be its own token, right after
        its word. The tokens must not continue a word of the text on either side,
        and must not overlap the entity.

        :param text: the analyzed text
        :param nlp_artifacts: the NLP artifacts of the analyzed text
        :param window_words: index, lowercase text and lowercase lemma of each
            window token that is not whitespace, a hyphen or a slash
        :param result: the recognized entity
        :param phrase: a context word of several words
        """
        tokens = nlp_artifacts.tokens
        tokens_indices = nlp_artifacts.tokens_indices
        for words in _phrase_tokens(phrase):
            for j in range(len(window_words) - len(words) + 1):
                run = window_words[j : j + len(words)]
                if not all(
                    word in (t, lemma) for (word, _), (_, t, lemma) in zip(words, run)
                ):
                    continue
                first, last = run[0][0], run[-1][0]
                run_start = tokens_indices[first]
                run_end = tokens_indices[last] + len(tokens[last])
                if run_start < result.end and run_end > result.start:
                    continue
                if _WORD_CHAR.match(text, max(run_start - 1, 0), run_start) or (
                    _WORD_CHAR.match(text, run_end)
                ):
                    continue
                gaps = (
                    (tokens_indices[a] + len(tokens[a]), tokens_indices[b], joined)
                    for (a, _, _), (b, _, _), (_, joined) in zip(
                        run, run[1:], words[1:]
                    )
                )
                if all(
                    gap_start == gap_end
                    if joined
                    else _PHRASE_GAP_RE.fullmatch(text, gap_start, gap_end)
                    for gap_start, gap_end, joined in gaps
                ):
                    logger.debug("Found context phrase '%s' in tokens", phrase)
                    return True
        return False
