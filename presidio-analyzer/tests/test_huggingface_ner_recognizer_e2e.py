"""End-to-end tests for HuggingFaceNerRecognizer with real model loading.

Unlike test_huggingface_ner_recognizer.py (fully mocked), these tests
download real models from the HuggingFace Hub and exercise the actual
transformers/optimum pipelines. They are the only coverage for the
recognizer's load() path against real library behavior.

Two tiers:

1. Mechanics tests with hf-internal-testing/tiny-random-bert (~100KB).
   The weights are random, so they assert on mechanics (spans, types,
   thresholds, torch/ort parity), not on meaningful predictions.
2. Semantic tests with the Stanford de-identifier — the model family used
   by conf/hf_ner_onnx.yaml and already downloaded by the engine tests (conftest
   references the torch variant). These assert on actual PII detection,
   and the ort test covers the mixed-layout repo scenario (ONNX under
   onnx/, tokenizer at root) that requires subfolder/file_name scoping.
"""

import pytest
from presidio_analyzer import RecognizerResult
from presidio_analyzer.predefined_recognizers import (
    HuggingFaceNerRecognizer,
)

TINY_MODEL = "hf-internal-testing/tiny-random-bert"
TINY_TEXT = "John Smith works at Contoso in Berlin since 2019."
# Random-weight model emits LABEL_0/LABEL_1; map both so output is non-empty.
TINY_LABEL_MAPPING = {"LABEL_0": "PERSON", "LABEL_1": "LOCATION"}


def _assert_valid_results(results, text):
    assert isinstance(results, list)
    assert len(results) > 0
    for r in results:
        assert isinstance(r, RecognizerResult)
        assert r.entity_type in ("PERSON", "LOCATION")
        assert 0 <= r.start < r.end <= len(text)
        assert 0.0 <= r.score <= 1.0


def test_hf_recognizer_e2e_torch_backend():
    """Real torch pipeline end-to-end on a tiny random model."""
    pytest.importorskip("torch", reason="torch is not installed")

    rec = HuggingFaceNerRecognizer(
        model_name=TINY_MODEL,
        backend="torch",
        device="cpu",
        label_mapping=TINY_LABEL_MAPPING,
        threshold=0.0,
    )
    results = rec.analyze(TINY_TEXT, entities=["PERSON", "LOCATION"])
    _assert_valid_results(results, TINY_TEXT)


def test_hf_recognizer_e2e_ort_backend():
    """Real ONNX Runtime pipeline end-to-end on a tiny random model.

    The repo has no .onnx weights, so this also exercises optimum's
    export-on-the-fly path (export=True forwarded via **model_kwargs).
    """
    pytest.importorskip(
        "optimum.onnxruntime", reason="optimum-onnx is not installed"
    )

    rec = HuggingFaceNerRecognizer(
        model_name=TINY_MODEL,
        backend="ort",
        label_mapping=TINY_LABEL_MAPPING,
        threshold=0.0,
        export=True,
    )
    results = rec.analyze(TINY_TEXT, entities=["PERSON", "LOCATION"])
    _assert_valid_results(results, TINY_TEXT)


def test_hf_recognizer_e2e_torch_and_ort_agree_on_spans():
    """Both backends run the same model; spans and scores should match."""
    pytest.importorskip("torch", reason="torch is not installed")
    pytest.importorskip(
        "optimum.onnxruntime", reason="optimum-onnx is not installed"
    )

    common = dict(
        model_name=TINY_MODEL,
        label_mapping=TINY_LABEL_MAPPING,
        threshold=0.0,
    )
    torch_results = HuggingFaceNerRecognizer(
        backend="torch", device="cpu", **common
    ).analyze(TINY_TEXT, entities=["PERSON", "LOCATION"])
    ort_results = HuggingFaceNerRecognizer(
        backend="ort", export=True, **common
    ).analyze(TINY_TEXT, entities=["PERSON", "LOCATION"])

    torch_spans = [(r.entity_type, r.start, r.end) for r in torch_results]
    ort_spans = [(r.entity_type, r.start, r.end) for r in ort_results]
    assert torch_spans == ort_spans
    for tr, orr in zip(torch_results, ort_results):
        assert abs(tr.score - orr.score) < 1e-3


DEID_TEXT = (
    "Hi, I'm Dr. Sarah Chen from Mount Sinai Hospital. "
    "Please call me at 555-123-4567 on March 5th, 2026."
)
DEID_LABEL_MAPPING = {
    "PATIENT": "PERSON",
    "HCW": "PERSON",
    "HOSPITAL": "ORGANIZATION",
    "VENDOR": "ORGANIZATION",
    "DATE": "DATE_TIME",
    "PHONE": "PHONE_NUMBER",
    "ID": "ID",
}
DEID_ENTITIES = ["PERSON", "ORGANIZATION", "DATE_TIME", "PHONE_NUMBER"]


def _assert_deid_detections(results, text):
    detected = {(r.entity_type, text[r.start : r.end]) for r in results}
    assert ("PERSON", "Dr. Sarah Chen") in detected
    assert ("ORGANIZATION", "Mount Sinai Hospital") in detected
    assert ("PHONE_NUMBER", "555-123-4567") in detected


def test_hf_recognizer_e2e_torch_stanford_deidentifier():
    """Real PII detection with the torch backend on the Stanford model."""
    pytest.importorskip("torch", reason="torch is not installed")

    rec = HuggingFaceNerRecognizer(
        model_name="StanfordAIMI/stanford-deidentifier-base",
        backend="torch",
        device="cpu",
        label_mapping=DEID_LABEL_MAPPING,
        threshold=0.5,
    )
    results = rec.analyze(DEID_TEXT, entities=DEID_ENTITIES)
    _assert_deid_detections(results, DEID_TEXT)


def test_hf_recognizer_e2e_ort_mixed_layout_repo():
    """Real PII detection with ort on a mixed-layout repo.

    onnx-community/stanford-deidentifier-base-ONNX keeps config/tokenizer at
    the repo root and ONNX files under onnx/. This is the scenario that
    requires subfolder/file_name to be scoped to the model loader only —
    regression coverage for the pipeline-level kwarg leak.
    """
    pytest.importorskip(
        "optimum.onnxruntime", reason="optimum-onnx is not installed"
    )

    rec = HuggingFaceNerRecognizer(
        model_name="onnx-community/stanford-deidentifier-base-ONNX",
        backend="ort",
        subfolder="onnx",
        # INT8 variant: same detections as model.onnx on this text, but a
        # 105MB download instead of 416MB (matters in CI, no HF cache there).
        file_name="model_quantized.onnx",
        label_mapping=DEID_LABEL_MAPPING,
        threshold=0.5,
    )
    results = rec.analyze(DEID_TEXT, entities=DEID_ENTITIES)
    _assert_deid_detections(results, DEID_TEXT)
