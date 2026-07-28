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
# The signature segment is 152 characters (152 % 4 == 0) so that its final
# character is a full 6-bit base64url symbol and every one of the 64 symbols is
# reachable there. At 150 characters (150 % 4 == 2) the last character carries
# only 2 significant bits -- canonical unpadded base64url could then end only in
# A, Q, g or w, so the "-"/"_" fixtures below would not represent real tokens.
GITHUB_STATELESS_TOKEN = (
    "gh" + "s_123456789_" + "eyJ" + "A" * 140 + ".eyJ" + "B" * 200 + "." + "C" * 152
)
# A stateless installation token ends in a base64url signature, which may
# legitimately end with "-" or "_". Pinning the span to alphanumeric would
# under-report these by one character.
GITHUB_STATELESS_TOKEN_DASH_END = GITHUB_STATELESS_TOKEN[:-1] + "-"
GITHUB_STATELESS_TOKEN_UNDERSCORE_END = GITHUB_STATELESS_TOKEN[:-1] + "_"


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
        # "." is in the installation-token character set, so a greedy match must
        # not report the period that ends the sentence as part of the token.
        (
            f"Rotate {GITHUB_OPAQUE_INSTALLATION_TOKEN}.",
            1,
            ((7, 7 + len(GITHUB_OPAQUE_INSTALLATION_TOKEN)),),
            ((0.9, 0.9),),
        ),
        (
            GITHUB_STATELESS_TOKEN_DASH_END,
            1,
            ((0, len(GITHUB_STATELESS_TOKEN_DASH_END)),),
            ((0.9, 0.9),),
        ),
        (
            GITHUB_STATELESS_TOKEN_UNDERSCORE_END,
            1,
            ((0, len(GITHUB_STATELESS_TOKEN_UNDERSCORE_END)),),
            ((0.9, 0.9),),
        ),
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
        # The value keeps the documented base64 alphabet including "=", so the
        # exact-length right boundary is what rejects a longer padded run
        # instead of reporting its first 40 characters.
        ("AWS_SECRET_ACCESS_KEY=" + "A" * 40 + "=", 0, (), ()),
        ("AWS_SECRET_ACCESS_KEY=" + "A" * 40 + "/", 0, (), ()),
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
        # The installation-token minimum must be counted on the reported span,
        # not on characters that trailing-"." backtracking gives back. Both of
        # these reach 36 characters only by including dots that cannot end the
        # span, so neither may be reported.
        ("gh" + "s_" + "A" * 35 + ".", 0, (), ()),
        ("gh" + "s_A" + "." * 35, 0, (), ()),
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


def _case_scope_spans_whole_pattern(regex: str) -> bool:
    """Return True if a leading ``(?-i:`` group closes only at the very end.

    Checking the prefix alone would accept a group that closes early, leaving
    the rest of the pattern case-insensitive again under registry flags. Walk
    the regex tracking parenthesis depth, skipping escapes and character
    classes, and require the opening group to close on the last character.
    """
    if not regex.startswith("(?-i:"):
        return False

    depth = 0
    in_class = False
    escaped = False
    for index, char in enumerate(regex):
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif in_class:
            if char == "]":
                in_class = False
        elif char == "[":
            in_class = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index == len(regex) - 1
    return False


def test_every_default_pattern_scopes_case_sensitivity():
    """A pattern added without the case-sensitive wrapper would silently widen.

    The scoping is applied per pattern, so an unwrapped addition still passes
    every positive test while matching lowercase prose once the registry
    applies IGNORECASE. Assert the invariant structurally instead.
    """
    unscoped = [
        pattern.name
        for pattern in ApiKeyRecognizer.PATTERNS
        if not _case_scope_spans_whole_pattern(pattern.regex)
    ]
    assert unscoped == []


@pytest.mark.parametrize(
    "regex, expected",
    [
        (r"(?-i:\bAKIA[0-9A-Z]{16}\b)", True),
        (r"(?-i:(?:a|b)c)", True),
        (r"(?-i:[)])", True),
        (r"(?-i:\))", True),
        # Closes early: everything after the group is case-insensitive again.
        (r"(?-i:\bAKIA)[0-9A-Z]{16}", False),
        (r"\bAKIA[0-9A-Z]{16}\b", False),
    ],
)
def test_case_scope_detection(regex, expected):
    """The scope check must reject a group that does not enclose the pattern."""
    assert _case_scope_spans_whole_pattern(regex) is expected
