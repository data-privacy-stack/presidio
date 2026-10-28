"""Abstract base class for text chunking strategies."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from presidio_analyzer.recognizer_result import RecognizerResult


@dataclass
class TextChunk:
    """Represents a chunk of text with its position in the original text.

    :param text: The chunk content
    :param start: Start position in the original text (inclusive)
    :param end: End position in the original text (exclusive)
    """

    text: str
    start: int
    end: int


class BaseTextChunker(ABC):
    """Abstract base class for text chunking strategies.

    Subclasses must implement the chunk() method to split text into
    TextChunk objects that include both content and position information.

    Provides methods for processing predictions across chunks and
    deduplicating overlapping entities.
    """

    @abstractmethod
    def chunk(self, text: str) -> List[TextChunk]:
        """Split text into chunks with position information.

        :param text: The input text to split
        :return: List of TextChunk objects with text and position data
        """
        pass

    def predict_with_chunking(
        self,
        text: str,
        predict_func: Callable[[str], List["RecognizerResult"]],
    ) -> List["RecognizerResult"]:
        """Process text with automatic chunking for long texts.

        For short text, calls predict_func directly.
        For long text, chunks it and merges predictions with deduplication.

        :param text: Input text to process
        :param predict_func: Function that takes text and returns
            RecognizerResult objects
        :return: List of RecognizerResult with correct offsets
        """
        chunks = self.chunk(text)
        if not chunks:
            return []
        if len(chunks) == 1:
            return predict_func(text)

        predictions, at_chunk_edge = self._process_chunks_marking_edges(
            chunks, predict_func
        )
        return self.deduplicate_overlapping_entities(
            predictions, at_chunk_edge=at_chunk_edge
        )

    def predict_batch_with_chunking(
        self,
        texts: List[str],
        predict_batch_func: Callable[[List[str]], List[List["RecognizerResult"]]],
    ) -> List[List["RecognizerResult"]]:
        """Process multiple texts with automatic chunking for batch inference.

        Chunks all texts, batches them into a single call to predict_batch_func,
        then unflattens and adjusts offsets.

        Note on memory: all chunk strings are collected into one Python list
        before being passed to predict_batch_func. The list itself is small
        (just string references). The GPU/CPU memory bound for the actual
        model forward pass is the responsibility of predict_batch_func — for
        the in-tree recognizers, that is enforced via `inference_batch_size`
        which caps the per-forward-pass batch.

        :param texts: List of input texts to process
        :param predict_batch_func: Function that takes a list of texts and returns
            a list of lists of RecognizerResult objects. Must return exactly
            one result list per input chunk.
        :return: List of RecognizerResult lists, one per input text
        :raises ValueError: If predict_batch_func returns a list of a length
            different from its input list.
        """
        from presidio_analyzer import RecognizerResult

        if not texts:
            return []

        # Build flat list of all chunk texts with tracking metadata
        # Each entry: (text_index, chunk, is_single_chunk)
        all_chunks = []
        flat_chunk_texts = []
        multi_chunk_texts = set()

        for text_idx, text in enumerate(texts):
            chunks = self.chunk(text)
            if not chunks:
                # No chunks produced; record a sentinel
                all_chunks.append((text_idx, None, True))
            elif len(chunks) == 1:
                # Single chunk - use original text for consistency
                all_chunks.append((text_idx, chunks[0], True))
                flat_chunk_texts.append(text)
            else:
                multi_chunk_texts.add(text_idx)
                for chunk in chunks:
                    all_chunks.append((text_idx, chunk, False))
                    flat_chunk_texts.append(chunk.text)

        # Call predict_batch_func once with all chunk texts, sorted by
        # length. Batched pipelines pad each batch to its longest member,
        # so grouping similar-length chunks minimizes wasted compute on
        # padding tokens. Results are restored to original order after.
        if flat_chunk_texts:
            order = sorted(
                range(len(flat_chunk_texts)),
                key=lambda i: len(flat_chunk_texts[i]),
            )
            sorted_results = predict_batch_func(
                [flat_chunk_texts[i] for i in order]
            )
            if len(sorted_results) != len(flat_chunk_texts):
                raise ValueError(
                    f"predict_batch_func returned {len(sorted_results)} results "
                    f"for {len(flat_chunk_texts)} input chunks. The function "
                    "must return one result list per input chunk."
                )
            flat_results = [None] * len(flat_chunk_texts)
            for sorted_pos, orig_idx in enumerate(order):
                flat_results[orig_idx] = sorted_results[sorted_pos]
        else:
            flat_results = []

        # Unflatten results back to per-text structure
        num_texts = len(texts)
        per_text_results: List[List["RecognizerResult"]] = [
            [] for _ in range(num_texts)
        ]

        flat_idx = 0
        for text_idx, chunk, is_single in all_chunks:
            if chunk is None:
                # No chunks for this text, skip
                continue

            chunk_results = flat_results[flat_idx]
            flat_idx += 1

            if is_single:
                # Single chunk covering entire text - no offset adjustment
                per_text_results[text_idx].extend(chunk_results)
            else:
                # Adjust offsets using chunk.start
                for pred in chunk_results:
                    adjusted_pred = RecognizerResult(
                        entity_type=pred.entity_type,
                        start=pred.start + chunk.start,
                        end=pred.end + chunk.start,
                        score=pred.score,
                        analysis_explanation=pred.analysis_explanation,
                        recognition_metadata=pred.recognition_metadata,
                    )
                    per_text_results[text_idx].append(adjusted_pred)

        # Deduplicate overlapping entities for texts that had multiple chunks
        for text_idx in multi_chunk_texts:
            per_text_results[text_idx] = self.deduplicate_overlapping_entities(
                per_text_results[text_idx]
            )

        return per_text_results

    def _process_chunks(
        self,
        chunks: List[TextChunk],
        process_func: Callable[[str], List["RecognizerResult"]],
    ) -> List["RecognizerResult"]:
        """Process text chunks and adjust entity offsets.

        :param chunks: List of TextChunk objects with text and position information
        :param process_func: Function that takes chunk text and returns
            RecognizerResult objects
        :return: List of RecognizerResult with adjusted offsets
        """
        predictions, _ = self._process_chunks_marking_edges(chunks, process_func)
        return predictions

    def _process_chunks_marking_edges(
        self,
        chunks: List[TextChunk],
        process_func: Callable[[str], List["RecognizerResult"]],
    ) -> Tuple[List["RecognizerResult"], List[Tuple[bool, bool]]]:
        """Process text chunks and mark predictions cut by an inner chunk edge.

        A prediction touches an inner edge when only whitespace separates it
        from the start of any chunk but the first, or from the end of any
        chunk but the last. Such a prediction may be a partial entity that
        the neighbouring chunk saw whole.

        :param chunks: List of TextChunk objects with text and position information
        :param process_func: Function that takes chunk text and returns
            RecognizerResult objects
        :return: Tuple of the RecognizerResult list with adjusted offsets and
            a parallel list of (start_at_edge, end_at_edge) flags
        """
        all_predictions = []
        at_chunk_edge = []
        last = len(chunks) - 1

        for idx, chunk in enumerate(chunks):
            chunk_predictions = process_func(chunk.text)

            # Create new RecognizerResult objects with adjusted offsets
            # to avoid mutating the original predictions
            for pred in chunk_predictions:
                adjusted_pred = RecognizerResult(
                    entity_type=pred.entity_type,
                    start=pred.start + chunk.start,
                    end=pred.end + chunk.start,
                    score=pred.score,
                    analysis_explanation=pred.analysis_explanation,
                    recognition_metadata=pred.recognition_metadata,
                )
                all_predictions.append(adjusted_pred)
                at_chunk_edge.append(
                    (
                        idx > 0 and not chunk.text[: pred.start].strip(),
                        idx < last and not chunk.text[pred.end :].strip(),
                    )
                )

        return all_predictions, at_chunk_edge

    def deduplicate_overlapping_entities(
        self,
        predictions: List["RecognizerResult"],
        overlap_threshold: float = 0.5,
        at_chunk_edge: Optional[List[Tuple[bool, bool]]] = None,
    ) -> List["RecognizerResult"]:
        """Remove duplicate entities from overlapping chunks.

        The highest-scoring prediction is kept, unless it touches an inner
        chunk edge and its only duplicate contains it and extends past that
        edge without touching an edge on the same side. The overlap guarantees
        the neighbouring chunk saw that entity whole, so its prediction is
        kept instead of the possibly partial one.

        :param predictions: List of RecognizerResult objects
        :param overlap_threshold: Overlap ratio threshold to consider duplicates
            (default: 0.5)
        :param at_chunk_edge: Optional list, parallel to predictions, of
            (start_at_edge, end_at_edge) flags marking predictions that touch
            an inner chunk edge (default: none do)
        :return: Deduplicated list of RecognizerResult sorted by position
        """
        if not predictions:
            return predictions
        if at_chunk_edge is None:
            at_chunk_edge = [(False, False)] * len(predictions)

        def is_duplicate(pred: "RecognizerResult", kept: "RecognizerResult") -> bool:
            # Check if same entity type and overlapping positions
            if pred.entity_type != kept.entity_type:
                return False
            overlap_start = max(pred.start, kept.start)
            overlap_end = min(pred.end, kept.end)
            if overlap_start >= overlap_end:
                return False

            # Calculate overlap ratio
            overlap_len = overlap_end - overlap_start
            pred_len = pred.end - pred.start
            kept_len = kept.end - kept.start
            if pred_len <= 0 or kept_len <= 0:
                return False

            # Check if overlap exceeds threshold
            return overlap_len / min(pred_len, kept_len) > overlap_threshold

        def completes_cut(
            pred: "RecognizerResult",
            pred_edge: Tuple[bool, bool],
            kept: "RecognizerResult",
            kept_edge: Tuple[bool, bool],
        ) -> bool:
            # pred must contain kept and extend past a side where kept is cut
            if pred.start > kept.start or pred.end < kept.end:
                return False
            extends_start = (
                kept_edge[0] and not pred_edge[0] and pred.start < kept.start
            )
            extends_end = kept_edge[1] and not pred_edge[1] and pred.end > kept.end
            return extends_start or extends_end

        # Sort by score descending to keep highest scoring entities
        order = sorted(
            range(len(predictions)), key=lambda i: predictions[i].score, reverse=True
        )
        unique = []
        unique_at_edge = []

        for idx in order:
            pred = predictions[idx]
            duplicates = [
                i for i, kept in enumerate(unique) if is_duplicate(pred, kept)
            ]
            if not duplicates:
                unique.append(pred)
                unique_at_edge.append(at_chunk_edge[idx])
            elif len(duplicates) == 1 and completes_cut(
                pred,
                at_chunk_edge[idx],
                unique[duplicates[0]],
                unique_at_edge[duplicates[0]],
            ):
                # The kept result may be cut by a chunk edge, prefer the
                # prediction from the chunk that saw the entity whole
                unique[duplicates[0]] = pred
                unique_at_edge[duplicates[0]] = at_chunk_edge[idx]

        # Sort by position for consistent output
        return sorted(unique, key=lambda p: p.start)
