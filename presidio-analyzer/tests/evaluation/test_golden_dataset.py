"""Integrity checks for the golden dataset.

These are pure-Python (no ``presidio-evaluator`` needed) and always run. The
end-to-end smoke evaluation lives in ``test_evaluation_smoke.py``.
"""

import json

import pytest

from tests.evaluation.evaluation import default_dataset_path
from tests.evaluation.generate_golden_en import build_dataset, dataset_to_json


@pytest.fixture(scope="module")
def raw_dataset():
    with open(default_dataset_path(), encoding="utf-8") as f:
        return json.load(f)


class TestDatasetIntegrity:
    def test_dataset_matches_generator(self):
        # The JSON file is generated, never hand-edited; regenerate with
        # `python -m tests.evaluation.generate_golden_en` after changing
        # the sample definitions.
        committed = default_dataset_path().read_text(encoding="utf-8")
        assert committed == dataset_to_json(build_dataset()), (
            "datasets/golden_en.json is out of sync with "
            "generate_golden_en.py; regenerate it with "
            "`python -m tests.evaluation.generate_golden_en`"
        )

    def test_sample_ids_are_unique(self, raw_dataset):
        ids = [sample["id"] for sample in raw_dataset["samples"]]
        assert len(ids) == len(set(ids))

    def test_spans_match_text_offsets(self, raw_dataset):
        for sample in raw_dataset["samples"]:
            text = sample["text"]
            for span in sample["spans"]:
                sliced = text[span["start"] : span["end"]]
                assert sliced == span["entity_value"], (
                    f"{sample['id']}: span [{span['start']}:{span['end']}] is "
                    f"{sliced!r}, expected {span['entity_value']!r}"
                )

    def test_span_entity_types_are_declared(self, raw_dataset):
        declared = set(raw_dataset["entities"])
        for sample in raw_dataset["samples"]:
            for span in sample["spans"]:
                assert span["entity_type"] in declared, (
                    f"{sample['id']}: {span['entity_type']} missing from "
                    f"the dataset's declared entity list"
                )

    def test_every_declared_entity_has_gold_spans(self, raw_dataset):
        annotated = {
            span["entity_type"]
            for sample in raw_dataset["samples"]
            for span in sample["spans"]
        }
        assert annotated == set(raw_dataset["entities"])

    def test_negative_samples_have_no_spans(self, raw_dataset):
        for sample in raw_dataset["samples"]:
            if sample["category"] == "negative":
                assert sample["spans"] == []
