import time
from pathlib import Path

import pytest
import yaml

import presidio_analyzer
from tests import assert_result
from presidio_analyzer.predefined_recognizers import UrlRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider


@pytest.fixture(scope="module")
def recognizer():
    return UrlRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["URL"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score",
    [
        # fmt: off
        # Valid URLs
        ("https://www.microsoft.com/", 1, ((0, 26),), 0.6,),
        ("http://www.microsoft.com/", 1, ((0, 25),), 0.6,),
        ("http://www.microsoft.com", 1, ((0, 24),), 0.6,),
        ("http://microsoft.com", 1, ((0, 20),), 0.6,),
        ("http://microsoft.site", 1, ((0, 21),), 0.6,),
        ("http://microsoft.webcam", 1, ((0, 23),), 0.6,),
        ("http://microsoft.vlaanderen", 1, ((0, 27),), 0.6,),
        ("https://webhook.site/a8eedfd6-9d8a-44e0-b0fc-cc7d517db5dc?q=1&b=2", 1, ((0, 65),), 0.6,),
        ("https://www.microsoft.com/store/abc/", 1, ((0, 36),), 0.6,),
        ("microsoft.com", 1, ((0, 13),), 0.5,),
        ("my domains: microsoft.com google.co.il", 2, ((12, 25), (26, 38),), 0.5),
        ('"https://presidio.dataprivacystack.org/"', 1, ((0, 40),), 0.6),
        ("'https://presidio.dataprivacystack.org/'", 1, ((0, 40),), 0.6),
        # URLs with credentials: the user and password are part of the URL
        ("https://user:pass@example.com/path", 1, ((0, 34),), 0.6),
        ("http://alice@proxy.example.net", 1, ((0, 30),), 0.6),
        ("db: https://admin:hunter2@db.internal.example.org/console", 1, ((4, 57),), 0.6),
        ("https://deploy:p%40ss!@git.example.com/team/repo.git", 1, ((0, 52),), 0.6),

        # Invalid URLs
        ("www.microsoft", 0, (), 0),
        ("http://microsoft", 0, (), 0),
        ("'www.microsoft'", 0, (), 0),
        # fmt: on
    ],
)
def test_when_all_urls_then_succeed(
        text, expected_len, expected_positions, expected_score, recognizer, entities
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, expected_score)


def test_long_valid_hostname_still_detected(recognizer, entities):
    # The host length bound is the DNS maximum, so a long but well-formed
    # hostname is matched exactly as before.
    host = "a." * 60 + "example"  # 127 chars, far below the 253 limit
    text = f"http://{host}.com/path"
    results = recognizer.analyze(text, entities)
    assert len(results) == 1
    assert_result(results[0], entities[0], 0, len(text), 0.6)


def test_repeated_dot_input_does_not_backtrack(recognizer, entities):
    # The host portion previously used an unbounded run that overlapped the
    # following dot separator, so a long run of dots backtracked quadratically
    # against the TLD alternation. It must now finish in time linear in length.
    text = "." * 3000
    start = time.time()
    results = recognizer.analyze(text, entities)
    elapsed = time.time() - start
    assert results == []
    assert elapsed < 15


def test_url_credentials_do_not_swallow_a_following_email(recognizer, entities):
    # "," is not part of the user info, so an address after a comma is not
    # read as the user of the URL before it.
    text = "https://example.com,bob@example.org"
    results = recognizer.analyze(text, entities)
    assert any(r.start == 0 and r.end == 19 for r in results)
    assert all(r.end <= 19 or r.start >= 20 for r in results)


def test_url_without_credentials_does_not_backtrack(recognizer, entities):
    # The user info part is optional and bounded, so a long run of user info
    # characters with no "@" fails fast.
    text = "https://" + "a:" * 3000
    start = time.time()
    results = recognizer.analyze(text, entities)
    elapsed = time.time() - start
    assert results == []
    assert elapsed < 15


def test_url_with_credentials_detected_when_loaded_from_default_yaml():
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "UrlRecognizer"]
    assert len(entries) == 1

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [entries[0]],
        }
    ).create_recognizer_registry()
    assert [type(r).__name__ for r in registry.recognizers] == ["UrlRecognizer"]

    text = "db: https://admin:hunter2@db.internal.example.org/console"
    results = registry.recognizers[0].analyze(text, ["URL"])
    assert len(results) == 1
    assert_result(results[0], "URL", 4, len(text), 0.6)
