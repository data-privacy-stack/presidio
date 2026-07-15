def test_readme():
    """Exercise the README anonymizer example."""
    # Tests that the readme code snippet doesn't fail
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig, RecognizerResult

    # Initialize the engine with logger.
    engine = AnonymizerEngine()

    # Invoke the anonymize function with the text,
    # analyzer results (potentially coming from presidio-analyzer) and
    # Operators to get the anonymization output:
    result = engine.anonymize(
        text="My name is Bond, James Bond",
        analyzer_results=[
            RecognizerResult(entity_type="PERSON", start=11, end=15, score=0.8),
            RecognizerResult(entity_type="PERSON", start=17, end=27, score=0.8),
        ],
        operators={"PERSON": OperatorConfig("replace", {"new_value": "BIP"})},
    )

    print(result)


def test_readme_decrypt():
    """Exercise the README single-item deanonymize example."""
    from presidio_anonymizer import DeanonymizeEngine
    from presidio_anonymizer.entities import OperatorConfig, OperatorResult

    # Initialize the engine with logger.
    engine = DeanonymizeEngine()

    # Invoke the deanonymize function with the text, anonymizer results and
    # Operators to define the deanonymization type.
    result = engine.deanonymize(
        text="My name is S184CMt9Drj7QaKQ21JTrpYzghnboTF9pn/neN8JME0=",
        entities=[
            OperatorResult(start=11, end=55, entity_type="PERSON"),
        ],
        operators={"DEFAULT": OperatorConfig("decrypt", {"key": "WmZq4t7w!z%C&F)J"})},
    )

    print(result)


def test_readme_batch_decrypt():
    """Exercise the README batch deanonymize example."""
    from presidio_anonymizer import BatchDeanonymizeEngine
    from presidio_anonymizer.entities import OperatorConfig, OperatorResult

    engine = BatchDeanonymizeEngine()

    results = engine.deanonymize_list(
        texts=[
            "My name is S184CMt9Drj7QaKQ21JTrpYzghnboTF9pn/neN8JME0=",
            "My name is S184CMt9Drj7QaKQ21JTrpYzghnboTF9pn/neN8JME0=",
        ],
        entities_list=[
            [OperatorResult(start=11, end=55, entity_type="PERSON")],
            [OperatorResult(start=11, end=55, entity_type="PERSON")],
        ],
        operators={"DEFAULT": OperatorConfig("decrypt", {"key": "WmZq4t7w!z%C&F)J"})},
    )

    assert results == ["My name is Chloë", "My name is Chloë"]
