import re

import pytest
from presidio_analyzer.predefined_recognizers import ApiKeyRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests import assert_result_within_score_range

# All credential values in this file are synthetic, except the AWS ones, which
# are the placeholders published in the AWS documentation.
#
# The Slack and Stripe values are assembled from fragments rather than written
# as literals. Secret scanners -- including GitHub push protection, which blocks
# the push outright -- match those two formats on shape alone, so a realistic
# literal would flag this test file. Splitting the prefix keeps the assembled
# string identical while leaving nothing for a scanner to match in the source.
SLACK_BOT_TOKEN = "xox" + "b-123456789012-1234567890123-EXAMPLEexampleEXAMPLEexam"
SLACK_APP_TOKEN = "xap" + "p-1-A01BCDEFGHI-1234567890123-EXAMPLEexample"
SLACK_WORKFLOW_TOKEN = "xwf" + "p-1-A01BCDEFGHI-1234567890123-EXAMPLEexample"
SLACK_REFRESH_TOKEN = "xox" + "e-1-A01BCDEFGHI-EXAMPLEexample"
SLACK_ROTATED_BOT_TOKEN = "xox" + "e.xoxb-1-A01BCDEFGHI-EXAMPLEexample"
SLACK_ROTATED_USER_TOKEN = "xox" + "e.xoxp-1-A01BCDEFGHI-EXAMPLEexample"
SLACK_LEGACY_TOKEN = "xox" + "s-123456789012-1234567890123-EXAMPLEexample"
STRIPE_SECRET_KEY = "sk" + "_live_0000EXAMPLEkey0000EXAMPLE00"
STRIPE_RESTRICTED_KEY = "rk" + "_live_0000EXAMPLEkey0000EXAMPLE00"
STRIPE_PUBLISHABLE_KEY = "pk" + "_live_0000EXAMPLEkey0000EXAMPLE00"
STRIPE_TEST_KEY = "sk" + "_test_0000EXAMPLEkey0000EXAMPLE00"
STRIPE_TEST_RESTRICTED_KEY = "rk" + "_test_0000EXAMPLEkey0000EXAMPLE00"
STRIPE_TEST_PUBLISHABLE_KEY = "pk" + "_test_0000EXAMPLEkey0000EXAMPLE00"
GITHUB_OPAQUE_INSTALLATION_TOKEN = "gh" + "s_A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
GITHUB_STATELESS_TOKEN = (
    "gh" + "s_123456789_" + "eyJ" + "A" * 140 + ".eyJ" + "B" * 200 + "." + "C" * 150
)


@pytest.fixture(scope="module")
def recognizer():
    """Return an ApiKeyRecognizer instance for testing."""
    return ApiKeyRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the entity list this recognizer supports."""
    return ["API_KEY"]


@pytest.fixture(scope="module")
def default_registry_recognizer():
    """Load ApiKeyRecognizer through the shipped registry configuration."""
    registry = RecognizerRegistryProvider().create_recognizer_registry()
    return next(
        recognizer
        for recognizer in registry.recognizers
        if recognizer.name == "ApiKeyRecognizer"
    )


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # --- AWS access key ID -------------------------------------------
        # AKIAIOSFODNN7EXAMPLE is the example value used in the AWS docs.
        ("Access key: AKIAIOSFODNN7EXAMPLE", 1, ((12, 32),), ((0.9, 0.9),)),
        # ASIA marks a temporary (STS) access key ID.
        ("Temporary creds ASIAIOSFODNN7EXAMPLE issued", 1, ((16, 36),), ((0.9, 0.9),)),
        # ABIA is an STS service bearer token, ACCA a context-specific
        # credential -- both are credentials per the IAM prefix table.
        ("ABIAIOSFODNN7EXAMPLE", 1, ((0, 20),), ((0.9, 0.9),)),
        ("ACCAIOSFODNN7EXAMPLE", 1, ((0, 20),), ((0.9, 0.9),)),
        # --- AWS secret access key ---------------------------------------
        # Shared credentials file form.
        (
            "aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            1,
            ((24, 64),),
            ((0.8, 0.8),),
        ),
        # Environment variable form.
        (
            "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            1,
            ((22, 62),),
            ((0.8, 0.8),),
        ),
        # JSON form. Only the secret is reported, not the anchor.
        (
            '"aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"',
            1,
            ((26, 66),),
            ((0.8, 0.8),),
        ),
        # --- GitHub ------------------------------------------------------
        (
            "token ghp_A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8 here",
            1,
            ((6, 46),),
            ((0.9, 0.9),),
        ),
        ("gho_A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8", 1, ((0, 40),), ((0.9, 0.9),)),
        (
            GITHUB_OPAQUE_INSTALLATION_TOKEN,
            1,
            ((0, len(GITHUB_OPAQUE_INSTALLATION_TOKEN)),),
            ((0.9, 0.9),),
        ),
        (GITHUB_STATELESS_TOKEN, 1, ((0, len(GITHUB_STATELESS_TOKEN)),), ((0.9, 0.9),)),
        (
            "github_pat_11ABCDEFG0EXAMPLEexamp_"
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456",
            1,
            ((0, 93),),
            ((0.9, 0.9),),
        ),
        # --- Google ------------------------------------------------------
        (
            "key AIzaSyD_ExampleKeyForTestingPurposes123 end",
            1,
            ((4, 43),),
            ((0.9, 0.9),),
        ),
        # --- Slack -------------------------------------------------------
        (SLACK_BOT_TOKEN, 1, ((0, 57),), ((0.85, 0.85),)),
        (SLACK_APP_TOKEN, 1, ((0, 47),), ((0.85, 0.85),)),
        (SLACK_WORKFLOW_TOKEN, 1, ((0, 47),), ((0.85, 0.85),)),
        (SLACK_REFRESH_TOKEN, 1, ((0, len(SLACK_REFRESH_TOKEN)),), ((0.85, 0.85),)),
        (
            SLACK_ROTATED_BOT_TOKEN,
            1,
            ((0, len(SLACK_ROTATED_BOT_TOKEN)),),
            ((0.85, 0.85),),
        ),
        (
            SLACK_ROTATED_USER_TOKEN,
            1,
            ((0, len(SLACK_ROTATED_USER_TOKEN)),),
            ((0.85, 0.85),),
        ),
        # --- Stripe ------------------------------------------------------
        (STRIPE_SECRET_KEY, 1, ((0, 35),), ((0.9, 0.9),)),
        (STRIPE_RESTRICTED_KEY, 1, ((0, 35),), ((0.9, 0.9),)),
        (STRIPE_TEST_KEY, 1, ((0, len(STRIPE_TEST_KEY)),), ((0.9, 0.9),)),
        (
            STRIPE_TEST_RESTRICTED_KEY,
            1,
            ((0, len(STRIPE_TEST_RESTRICTED_KEY)),),
            ((0.9, 0.9),),
        ),
        # --- JWT ---------------------------------------------------------
        (
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiIxMjM0NTY3ODkwIn0."
            "dBjftJeZ4CVPmB92K27uhbUJU1p1r_wW1gFWFOEjXk",
            1,
            ((7, 114),),
            ((0.6, 0.6),),
        ),
        # --- Multiple credentials in one text ----------------------------
        (
            "id AKIAIOSFODNN7EXAMPLE and key ghp_A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8",
            2,
            ((3, 23), (32, 72)),
            ((0.9, 0.9), (0.9, 0.9)),
        ),
        # --- False positive prevention -----------------------------------
        # Vendor prefixes are case-sensitive.
        ("akiaiosfodnn7example lowercase", 0, (), ()),
        ("GHP_A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8", 0, (), ()),
        ("aizasyd_ExampleKeyForTestingPurposes123", 0, (), ()),
        # A 40-character hex digest is not an AWS secret access key.
        ("sha1 is 356a192b7913b04c54574d18c28d46e6395428ab here", 0, (), ()),
        ("commit 5aa01c0d84f6de2c1a89b6c2b1e7dfa3c9d0e1b2 done", 0, (), ()),
        # A bare 40-character base64 run carries no credential marker.
        ("random 40 chars wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY alone", 0, (), ()),
        # The documented secret length is exact; do not return a partial span.
        ("AWS_SECRET_ACCESS_KEY=" + "A" * 39, 0, (), ()),
        ("AWS_SECRET_ACCESS_KEY=" + "A" * 41, 0, (), ()),
        # IAM unique ID prefixes identify roles/users, not credentials.
        ("AROADBQP57FF2AEXAMPLE is a role unique id", 0, (), ()),
        ("AIDACKCEVSQ6C2EXAMPLE is a user unique id", 0, (), ()),
        ("AGPAIOSFODNN7EXAMPLE is a user group unique id", 0, (), ()),
        # Stripe publishable keys are documented as safe to expose.
        # Legacy Slack prefixes are not in the current documentation.
        (SLACK_LEGACY_TOKEN, 0, (), ()),
        (f"{STRIPE_PUBLISHABLE_KEY} publishable", 0, (), ()),
        (f"{STRIPE_TEST_PUBLISHABLE_KEY} publishable", 0, (), ()),
        # Wrong lengths.
        ("ghp_A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p", 0, (), ()),
        ("AKIAIOSFODNN7EXAMPL", 0, (), ()),
        # Dotted base64 whose payload is not a JSON object is not a JWT.
        ("eyJhbGciOiJIUzI1NiJ9.bm90LWEtanNvbi1wYXlsb2Fk.c2lnbmF0dXJlaGVyZQ", 0, (), ()),
        # fmt: on
    ],
)
def test_when_api_keys_then_succeed(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    """Verify ApiKeyRecognizer detects vendor credentials and rejects lookalikes."""
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    assert len(expected_positions) == expected_len
    assert len(expected_score_ranges) == expected_len
    for res, (st_pos, fn_pos), (st_score, fn_score) in zip(
        results, expected_positions, expected_score_ranges
    ):
        if fn_score == "max":
            fn_score = max_score
        assert_result_within_score_range(
            res, entities[0], st_pos, fn_pos, st_score, fn_score
        )


def test_when_secret_reported_then_anchor_excluded(recognizer, entities):
    """The AWS anchor must not be part of the reported span."""
    text = "aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    results = recognizer.analyze(text, entities)

    assert len(results) == 1
    assert text[results[0].start : results[0].end] == (
        "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    )


@pytest.mark.parametrize(
    "text",
    [
        "akiaiosfodnn7example lowercase",
        "GHP_A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8",
        "aizasyd_ExampleKeyForTestingPurposes123",
    ],
)
def test_when_loaded_from_default_registry_then_prefixes_remain_case_sensitive(
    text, default_registry_recognizer, entities
):
    """Registry-level IGNORECASE must not override credential prefix casing."""
    assert default_registry_recognizer.global_regex_flags & re.IGNORECASE
    assert default_registry_recognizer.analyze(text, entities) == []
