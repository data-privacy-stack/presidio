from presidio_anonymizer.entities import OperatorResult, EngineResult


def test_when_no_params_then_object_initialised_correctly():
    res = EngineResult()
    assert res.text is None
    assert res.items == []


def test_when_correct_params_then_object_initialised_correctly():
    ari = OperatorResult(0, 35, "type", "text", "hash")
    res = EngineResult("a", [ari])
    assert res.text == "a"
    assert res.items[0] == ari


def test_when_normalized_items_called_then_idexes_are_normalized():
    ari = OperatorResult(1, 2, "type", "cd", "hash")
    res = EngineResult("*****", [ari])
    res.normalize_item_indexes()
    assert res.items[0].start == 3
    assert res.items[0].end == 5


def test_when_set_text_then_text_is_set():
    res = EngineResult()
    res.set_text("a")
    assert res.text == "a"


def test_when_add_item_the_item_added():
    res = EngineResult()
    ari = OperatorResult(0, 35, "type", "text", "hash")
    res.add_item(ari)
    assert res.items[0] == ari


def test_when_eq_called_then_instances_are_equal():
    res = EngineResult()
    res.set_text("a")
    res2 = EngineResult()
    res2.set_text("a")

    assert res.__eq__(res2)


def test_when_not_eq_called_then_instances_are_not_equal():
    res = EngineResult()
    res.set_text("a")
    res2 = EngineResult()
    res2.set_text("b")

    assert res.__eq__(res2) is False


def test_when_items_differ_in_number_then_instances_are_not_equal():
    item = OperatorResult(0, 1, "PERSON", "x", "replace")
    other_item = OperatorResult(5, 9, "EMAIL_ADDRESS", "y", "replace")
    res = EngineResult("x", [item])
    res2 = EngineResult("x", [item, other_item])

    assert res.__eq__(res2) is False
    assert EngineResult("x", []).__eq__(res2) is False
