import pytest
import spacy
from presidio_analyzer.nlp_engine import TransformersNlpEngine


def test_default_models():
    engine = TransformersNlpEngine()
    assert len(engine.models) > 0
    assert engine.models[0]["lang_code"] == "en"
    assert isinstance(engine.models[0]["model_name"], dict)


def test_validate_model_params_happy_path():
    model = {
        "lang_code": "en",
        "model_name": {
            "spacy": "en_core_web_sm",
            "transformers": "obi/deid_roberta_i2b2",
        },
    }

    TransformersNlpEngine._validate_model_params(model)


def test_transformers_pipe_adds_spans_and_scores(mocker):
    """Verify single-document predictions are stored as scored spaCy spans."""
    predictions = [
        {
            "entity_group": "PER",
            "start": 11,
            "end": 14,
            "score": 0.98,
        }
    ]
    pipeline = mocker.Mock(return_value=predictions)
    mocker.patch(
        "presidio_analyzer.nlp_engine.transformers_nlp_engine.hf_pipeline",
        return_value=pipeline,
    )

    nlp = spacy.blank("en")
    nlp.add_pipe(
        "presidio_transformers_ner",
        config={
            "model": "test-model",
            "alignment_mode": "strict",
            "spans_key": "test-entities",
        },
    )

    doc = nlp("my name is Dan")

    assert [(span.text, span.label_) for span in doc.spans["test-entities"]] == [
        ("Dan", "PER")
    ]
    assert doc.spans["test-entities"].attrs["scores"] == [0.98]


def test_transformers_pipe_batches_documents(mocker):
    """Verify batch predictions remain associated with their source documents."""
    pipeline = mocker.Mock(
        return_value=[
            [{"entity_group": "PER", "start": 0, "end": 3, "score": 0.98}],
            [{"entity_group": "ORG", "start": 0, "end": 6, "score": 0.92}],
        ]
    )
    mocker.patch(
        "presidio_analyzer.nlp_engine.transformers_nlp_engine.hf_pipeline",
        return_value=pipeline,
    )

    nlp = spacy.blank("en")
    nlp.add_pipe(
        "presidio_transformers_ner",
        config={"model": "test-model", "spans_key": "test-entities"},
    )

    docs = list(nlp.pipe(["Dan", "GitHub"], batch_size=2))

    assert [doc.spans["test-entities"][0].text for doc in docs] == ["Dan", "GitHub"]
    assert [doc.spans["test-entities"].attrs["scores"] for doc in docs] == [
        [0.98],
        [0.92],
    ]


@pytest.mark.parametrize(
    "key",
    [("lang_code"), ("model_name"), ("model_name.spacy"), ("model_name.transformers")],
)
def test_validate_model_params_missing_fields(key):
    model = {
        "lang_code": "en",
        "model_name": {
            "spacy": "en_core_web_sm",
            "transformers": "obi/deid_roberta_i2b2",
        },
    }
    keys = key.split(".")
    if len(keys) == 1:
        del model[keys[0]]
    else:
        del model[keys[0]][keys[1]]

    with pytest.raises(ValueError):
        TransformersNlpEngine._validate_model_params(model)
