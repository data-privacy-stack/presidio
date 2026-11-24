import pytest

from tests import assert_result
from presidio_analyzer.predefined_recognizers import EmailRecognizer


@pytest.fixture(scope="module")
def recognizer():
    return EmailRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["EMAIL_ADDRESS"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions",
    [
        # fmt: off
        # valid email addresses
        ("info@presidio.site", 1, ((0, 18),),),
        ("my email address is info@presidio.site", 1, ((20, 38),),),
        ("try one of these emails: info@presidio.site or anotherinfo@presidio.site",
            2,
         ((25, 43), (47, 72),),),
        # valid internationalized (IDN / RFC 3490 punycode) email addresses
        ("user@xn--80ak6aa92e.com", 1, ((0, 23),),),
        ("a@xn--d1acufc.xn--p1ai", 1, ((0, 22),),),
        ("my email is user@xn--80ak6aa92e.com today", 1, ((12, 35),),),
        # invalid email address
        ("my email is info@presidio.", 0, ()),
        # non-email text is still not matched
        ("this is not an email: hello-world here", 0, ()),
        # fmt: on
    ],
)
def test_when_all_email_addresses_then_succeed(
    text, expected_len, expected_positions, recognizer, entities, max_score
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, max_score)


def test_when_email_recognizer_offline_then_detects_valid_email():
    """Test that EmailRecognizer in offline mode detects emails using bundled snapshot."""
    rec = EmailRecognizer(offline=True)
    results = rec.analyze("Contact us at test@presidio.org for details", ["EMAIL_ADDRESS"])
    assert len(results) == 1
    assert results[0].start == 14
    assert results[0].end == 31


def test_when_email_recognizer_offline_then_uses_empty_suffix_list_urls(monkeypatch):
    """Test that offline=True instantiates TLDExtract with suffix_list_urls=()."""
    import tldextract
    recorded_kwargs = {}

    original_tldextract_cls = tldextract.TLDExtract

    def mock_tldextract(*args, **kwargs):
        recorded_kwargs.update(kwargs)
        return original_tldextract_cls(*args, **kwargs)

    monkeypatch.setattr(tldextract, "TLDExtract", mock_tldextract)

    rec = EmailRecognizer(offline=True)
    assert rec.offline is True
    assert recorded_kwargs.get("suffix_list_urls") == ()
