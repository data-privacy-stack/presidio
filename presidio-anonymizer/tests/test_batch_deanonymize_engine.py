# ruff: noqa: D101,D102,D103,I001

import pytest

from presidio_anonymizer import BatchDeanonymizeEngine
from presidio_anonymizer.deanonymize_engine import DeanonymizeEngine
from presidio_anonymizer.entities import (
    DictRecognizerResult,
    EngineResult,
    OperatorConfig,
    OperatorResult,
)
from presidio_anonymizer.operators import Decrypt


ENCRYPTED_TEXT = "My name is S184CMt9Drj7QaKQ21JTrpYzghnboTF9pn/neN8JME0="
DECRYPTED_TEXT = "My name is Chloë"
ENTITY = OperatorResult(start=11, end=55, entity_type="PERSON")
OPERATORS = {"DEFAULT": OperatorConfig(Decrypt.NAME, {"key": "WmZq4t7w!z%C&F)J"})}


@pytest.fixture(scope="module")
def engine():
    return BatchDeanonymizeEngine()


def test_package_root_exports_batch_deanonymize_engine():
    from presidio_anonymizer import (
        BatchDeanonymizeEngine as ExportedBatchDeanonymizeEngine,
    )

    assert ExportedBatchDeanonymizeEngine is BatchDeanonymizeEngine


def test_given_analyzer_result_we_deanonymize_list_correctly(engine):
    texts = [ENCRYPTED_TEXT, ENCRYPTED_TEXT]
    entities_list = [[ENTITY], [ENTITY]]

    deanonymize_results = engine.deanonymize_list(
        texts=texts, entities_list=entities_list, operators=OPERATORS
    )

    assert deanonymize_results == [DECRYPTED_TEXT, DECRYPTED_TEXT]


def test_given_analyzer_result_we_deanonymize_dict_correctly(engine):
    analyzer_results = [
        DictRecognizerResult(
            key="name", value=ENCRYPTED_TEXT, recognizer_results=[ENTITY]
        )
    ]

    deanonymize_results = engine.deanonymize_dict(
        anonymizer_results=analyzer_results, operators=OPERATORS
    )

    assert deanonymize_results == {"name": DECRYPTED_TEXT}


def test_given_nested_analyzer_result_we_deanonymize_dict_correctly(engine):
    analyzer_results = [
        DictRecognizerResult(
            key="customer",
            value={"profile": {"name": ENCRYPTED_TEXT}},
            recognizer_results=[
                DictRecognizerResult(
                    key="profile",
                    value={"name": ENCRYPTED_TEXT},
                    recognizer_results=[
                        DictRecognizerResult(
                            key="name",
                            value=ENCRYPTED_TEXT,
                            recognizer_results=[ENTITY],
                        )
                    ],
                )
            ],
        )
    ]

    deanonymize_results = engine.deanonymize_dict(
        anonymizer_results=analyzer_results, operators=OPERATORS
    )

    assert deanonymize_results == {"customer": {"profile": {"name": DECRYPTED_TEXT}}}


def test_given_empty_entities_we_return_text_unchanged(engine):
    deanonymize_results = engine.deanonymize_list(
        texts=[ENCRYPTED_TEXT], entities_list=[], operators=OPERATORS
    )

    assert deanonymize_results == [ENCRYPTED_TEXT]


def test_given_short_entities_list_we_keep_trailing_texts(engine):
    deanonymize_results = engine.deanonymize_list(
        texts=[ENCRYPTED_TEXT, "plain trailing text"],
        entities_list=[[ENTITY]],
        operators=OPERATORS,
    )

    assert deanonymize_results == [DECRYPTED_TEXT, "plain trailing text"]


def test_given_exact_type_list_values_we_route_through_injected_engine():
    deanonymize_engine = RecordingDeanonymizeEngine()
    engine = BatchDeanonymizeEngine(deanonymize_engine=deanonymize_engine)

    sentinel = object()
    deanonymize_results = engine.deanonymize_list(
        texts=[True, 7, 1.5, sentinel],
        entities_list=[[], [], [], []],
        operators=OPERATORS,
    )

    assert deanonymize_results == ["custom::True", "custom::7", "custom::1.5", sentinel]
    assert deanonymize_engine.calls == [
        ("True", [], OPERATORS),
        ("7", [], OPERATORS),
        ("1.5", [], OPERATORS),
    ]


def test_given_non_string_list_value_we_return_item_unchanged(engine):
    analyzer_results = [
        DictRecognizerResult(
            key="items",
            value=[ENCRYPTED_TEXT, ["nested", 123], object()],
            recognizer_results=[[ENTITY], [], []],
        )
    ]

    deanonymize_results = engine.deanonymize_dict(
        anonymizer_results=analyzer_results, operators=OPERATORS
    )

    assert deanonymize_results["items"][0] == DECRYPTED_TEXT
    assert deanonymize_results["items"][1] == ["nested", 123]
    assert type(deanonymize_results["items"][2]) is object


def test_given_scalar_dict_value_we_return_value_unchanged(engine):
    analyzer_results = [
        DictRecognizerResult(key="id", value=123, recognizer_results=[])
    ]

    deanonymize_results = engine.deanonymize_dict(
        anonymizer_results=analyzer_results, operators=OPERATORS
    )

    assert deanonymize_results == {"id": 123}


class RecordingDeanonymizeEngine(DeanonymizeEngine):
    def __init__(self):
        super().__init__()
        self.calls = []

    def deanonymize(self, text, entities, operators):
        self.calls.append((text, entities, operators))
        return EngineResult(text=f"custom::{text}")


def test_given_custom_deanonymizer_we_use_injected_engine():
    deanonymize_engine = RecordingDeanonymizeEngine()
    engine = BatchDeanonymizeEngine(deanonymize_engine=deanonymize_engine)

    deanonymize_results = engine.deanonymize_list(
        texts=[ENCRYPTED_TEXT], entities_list=[[ENTITY]], operators=OPERATORS
    )

    assert deanonymize_results == [f"custom::{ENCRYPTED_TEXT}"]
    assert deanonymize_engine.calls == [(ENCRYPTED_TEXT, [ENTITY], OPERATORS)]


def test_given_unsupported_kwargs_then_batch_api_rejects_them(engine):
    with pytest.raises(TypeError, match="unexpected keyword argument"):
        engine.deanonymize_list(
            texts=[ENCRYPTED_TEXT],
            entities_list=[[ENTITY]],
            operators=OPERATORS,
            language="en",
        )
