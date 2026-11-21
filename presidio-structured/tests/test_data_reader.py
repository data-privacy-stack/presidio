import json

import pytest

from presidio_structured import CsvReader, JsonLinesReader, JsonReader

# "José" and "Bogotá" are not valid UTF-8 when written as cp1252.
LATIN1_NAME = "José"
LATIN1_CITY = "Bogotá"


@pytest.fixture
def cp1252_csv(tmp_path):
    path = tmp_path / "people.csv"
    path.write_bytes(f"name,city\n{LATIN1_NAME},{LATIN1_CITY}\n".encode("cp1252"))
    return path


@pytest.fixture
def cp1252_json(tmp_path):
    path = tmp_path / "person.json"
    body = json.dumps({"name": LATIN1_NAME, "city": LATIN1_CITY}, ensure_ascii=False)
    path.write_bytes(body.encode("cp1252"))
    return path


@pytest.fixture
def cp1252_jsonl(tmp_path):
    path = tmp_path / "people.jsonl"
    body = json.dumps({"name": LATIN1_NAME, "city": LATIN1_CITY}, ensure_ascii=False)
    path.write_bytes(f"{body}\n".encode("cp1252"))
    return path


@pytest.fixture
def ascii_json(tmp_path):
    path = tmp_path / "ascii.json"
    path.write_text(json.dumps({"name": "John Doe", "id": 1}), encoding="ascii")
    return path


def test_when_csv_reader_has_encoding_then_it_is_used_for_read(cp1252_csv):
    df = CsvReader(encoding="cp1252").read(cp1252_csv)

    assert df.to_dict("records") == [{"name": LATIN1_NAME, "city": LATIN1_CITY}]


def test_when_csv_read_gets_encoding_then_it_overrides_the_reader_one(cp1252_csv):
    df = CsvReader(encoding="utf-8").read(cp1252_csv, encoding="cp1252")

    assert df.to_dict("records") == [{"name": LATIN1_NAME, "city": LATIN1_CITY}]


def test_when_csv_reader_has_no_encoding_then_utf8_file_still_reads(tmp_path):
    path = tmp_path / "utf8.csv"
    path.write_text(f"name,city\n{LATIN1_NAME},{LATIN1_CITY}\n", encoding="utf-8")

    df = CsvReader().read(path)

    assert df.to_dict("records") == [{"name": LATIN1_NAME, "city": LATIN1_CITY}]


def test_when_csv_read_gets_other_kwargs_then_they_reach_read_csv(cp1252_csv):
    df = CsvReader(encoding="cp1252").read(cp1252_csv, usecols=["name"])

    assert list(df.columns) == ["name"]


def test_when_json_reader_has_encoding_then_it_is_used_for_read(cp1252_json):
    data = JsonReader(encoding="cp1252").read(cp1252_json)

    assert data == {"name": LATIN1_NAME, "city": LATIN1_CITY}


def test_when_json_read_gets_encoding_then_it_overrides_the_reader_one(cp1252_json):
    data = JsonReader(encoding="utf-8").read(cp1252_json, encoding="cp1252")

    assert data == {"name": LATIN1_NAME, "city": LATIN1_CITY}


def test_when_default_json_reader_gets_encoding_then_it_is_used(cp1252_json):
    data = JsonReader().read(cp1252_json, encoding="cp1252")

    assert data == {"name": LATIN1_NAME, "city": LATIN1_CITY}


def test_when_json_reader_has_no_encoding_then_ascii_file_still_reads(ascii_json):
    data = JsonReader().read(ascii_json)

    assert data == {"name": "John Doe", "id": 1}


def test_when_json_read_gets_other_kwargs_then_they_reach_json_load(ascii_json):
    data = JsonReader(encoding="ascii").read(ascii_json, parse_int=float)

    assert isinstance(data["id"], float)


def test_when_jsonl_is_read_then_each_line_is_a_record_in_file_order(tmp_path):
    path = tmp_path / "people.jsonl"
    path.write_text(
        '{"name": "John Doe", "id": 1}\n{"name": "Jane Roe", "id": 2}\n',
        encoding="utf-8",
    )

    records = JsonLinesReader().read(path)

    assert records == [{"name": "John Doe", "id": 1}, {"name": "Jane Roe", "id": 2}]


def test_when_jsonl_has_blank_lines_then_they_are_skipped(tmp_path):
    path = tmp_path / "people.jsonl"
    path.write_text(
        '{"name": "John Doe"}\r\n\r\n   \n{"name": "Jane Roe"}\n\n', encoding="utf-8"
    )

    records = JsonLinesReader().read(path)

    assert records == [{"name": "John Doe"}, {"name": "Jane Roe"}]


def test_when_jsonl_line_is_invalid_then_error_names_the_line_not_its_content(
    tmp_path,
):
    path = tmp_path / "people.jsonl"
    path.write_text('{"name": "John Doe"}\n{"name": "Jane Roe"\n', encoding="utf-8")

    with pytest.raises(ValueError) as excinfo:
        JsonLinesReader().read(path)

    assert str(excinfo.value) == (
        f"Invalid JSON on line 2 of {path}: Expecting ',' delimiter"
    )


def test_when_jsonl_reader_has_encoding_then_it_is_used_for_read(cp1252_jsonl):
    records = JsonLinesReader(encoding="cp1252").read(cp1252_jsonl)

    assert records == [{"name": LATIN1_NAME, "city": LATIN1_CITY}]


def test_when_jsonl_read_gets_encoding_then_it_overrides_the_reader_one(cp1252_jsonl):
    records = JsonLinesReader(encoding="utf-8").read(cp1252_jsonl, encoding="cp1252")

    assert records == [{"name": LATIN1_NAME, "city": LATIN1_CITY}]


def test_when_jsonl_read_gets_other_kwargs_then_they_reach_json_loads(tmp_path):
    path = tmp_path / "ids.jsonl"
    path.write_text('{"id": 1}\n{"id": 2}\n', encoding="utf-8")

    records = JsonLinesReader().read(path, parse_int=float)

    assert all(isinstance(record["id"], float) for record in records)
