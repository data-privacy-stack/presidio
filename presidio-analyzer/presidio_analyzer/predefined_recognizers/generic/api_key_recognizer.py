import re
from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer

# The AWS secret access key has no distinguishing structure of its own -- it is
# 40 characters of base64, which is indistinguishable from a hash, an id, or a
# slice of an encoded blob. It is therefore anchored on the credential name that
# AWS itself documents: the shared-credentials-file setting
# ``aws_secret_access_key`` and the environment variable
# ``AWS_SECRET_ACCESS_KEY``.
#
# PatternRecognizer matches with the ``regex`` module, which supports
# variable-length lookbehind, so the anchor can be excluded from the reported
# span and only the secret itself is returned.
AWS_SECRET_ANCHOR = (
    r"(?<=(?i:aws_secret_access_key)[\"']?[ \t]{0,8}[:=][ \t]{0,8}[\"']?)"
)


def _case_sensitive(regex: str) -> str:
    """Keep credential formats case-sensitive under registry-level regex flags.

    ``RecognizerListLoader.get`` assigns the registry's ``global_regex_flags``
    to every ``PatternRecognizer`` *after* construction, and the shipped
    registry configuration includes ``re.IGNORECASE``. Constructor flags
    therefore cannot keep a vendor prefix case-sensitive; the scoped
    ``(?-i:...)`` group can, because it travels with the pattern itself.

    Remove this only together with the flag assignment in
    ``recognizer_registry/recognizers_loader_utils.py``.
    """
    return rf"(?-i:{regex})"


class ApiKeyRecognizer(PatternRecognizer):
    """
    Recognize provider-issued API keys, access keys and bearer tokens.

    Every pattern is anchored on a vendor-assigned, case-sensitive prefix, a
    documented credential name, or a standards-defined structural marker.
    String length and entropy are supporting evidence rather than the primary
    signal.

    Note: case sensitivity is encoded inside every default pattern. The
    recognizer registry applies its global regex flags after constructing
    predefined recognizers, so constructor flags alone cannot preserve
    case-sensitive vendor prefixes in the default configuration.

    ref:
    - AWS access key ID prefixes (``AKIA``, ``ASIA``):
      https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_identifiers.html
    - AWS credential names (``aws_secret_access_key`` /
      ``AWS_SECRET_ACCESS_KEY``):
      https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html
    - AWS access key lengths:
      https://docs.aws.amazon.com/AmazonS3/latest/developerguide/MakingRequests.html
    - GitHub token prefixes and base62 body:
      https://github.blog/engineering/platform-security/behind-githubs-new-authentication-token-formats/
    - GitHub stateless installation tokens:
      https://github.blog/changelog/2026-05-15-github-app-installation-tokens-per-request-override-header/
    - Google API keys:
      https://cloud.google.com/docs/authentication/api-keys
    - Slack token prefixes:
      https://docs.slack.dev/authentication/tokens/
    - Slack token rotation formats:
      https://docs.slack.dev/authentication/using-token-rotation/
    - Stripe secret and restricted keys:
      https://docs.stripe.com/keys
    - JSON Web Token structure (RFC 7519, section 3):
      https://datatracker.ietf.org/doc/html/rfc7519#section-3

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param regex_flags: Regex flags to be used in regex matching
    :param name: Name of the recognizer
    """

    PATTERNS = [
        # The IAM unique ID prefix table lists four credential prefixes: AKIA
        # (access key), ASIA (temporary/STS access key ID), ABIA (STS service
        # bearer token) and ACCA (context-specific credential). The remaining
        # prefixes (AIDA, AROA, ANPA, ANVA, AGPA, AIPA, APKA, ASCA) identify
        # users, roles, groups and policies -- they are identifiers, not
        # credentials, and are deliberately excluded.
        Pattern(
            "AWS access key ID",
            _case_sensitive(r"\b(?:ABIA|ACCA|AKIA|ASIA)[0-9A-Z]{16}\b"),
            0.9,
        ),
        # The value keeps the full base64 alphabet including ``=``. Thirty random
        # bytes would encode to 40 characters with no padding, which would make
        # ``=`` impossible -- but AWS documents the length only, not the
        # generation algorithm, and its own credential-scanning guidance has used
        # ``[A-Za-z0-9/+=]{40}``. Narrowing the set on an inferred format would
        # trade a rare false positive (a run of padding after the credential
        # name) for a false negative on a real secret, which is the worse error
        # here. ``=`` stays in the right-boundary lookahead so the documented
        # exact length is still enforced.
        Pattern(
            "AWS secret access key",
            _case_sensitive(
                AWS_SECRET_ANCHOR + r"[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])"
            ),
            0.8,
        ),
        # ghp_/gho_/ghu_/ghs_/ghr_ followed by 30 characters of base62 entropy
        # and a 6 character base62 CRC32 checksum. GitHub App installation
        # tokens (ghs_) are separate because GitHub also issues a stateless,
        # JWT-format token and recommends accepting 36 or more characters from
        # its documented character set.
        Pattern(
            "GitHub token",
            _case_sensitive(r"\bgh[pour]_[A-Za-z0-9]{36}\b"),
            0.9,
        ),
        # GitHub's recommended ``ghs_[A-Za-z0-9.\-_]{36,}`` is written for
        # validation, where a right boundary is unnecessary. Presidio reports a
        # span, so the match must not end on ``.``: it is both a JWT segment
        # separator and ordinary sentence punctuation, and a greedy match would
        # otherwise report the period that ends a sentence as part of the
        # credential. ``-`` and ``_`` stay admissible at the end because a
        # base64url signature may legitimately end with either, and clipping one
        # would under-report a real token.
        #
        # The 36-character minimum is spelled ``{35,}`` plus one final character
        # so that the length is counted on what is *reported*. Asserting the
        # length in a lookahead instead would count trailing dots that the
        # consuming part then backtracks away, letting a short body such as
        # ``ghs_A....`` be reported.
        Pattern(
            "GitHub App installation token",
            _case_sensitive(r"\bghs_[A-Za-z0-9._-]{35,}[A-Za-z0-9_-]"),
            0.9,
        ),
        Pattern(
            "GitHub fine-grained personal access token",
            _case_sensitive(r"\bgithub_pat_[A-Za-z0-9_]{82}\b"),
            0.9,
        ),
        Pattern(
            "Google API key",
            _case_sensitive(r"\bAIza[0-9A-Za-z_-]{35}\b"),
            0.9,
        ),
        # Slack documents xoxb (bot), xoxp (user), xoxe- (rotation refresh),
        # xoxe.xoxb-/xoxe.xoxp- (rotated access), xapp (app-level), and xwfp
        # (workflow). The legacy xoxa/xoxr/xoxs prefixes are not in the current
        # documentation and are left out.
        Pattern(
            "Slack bot or user token",
            _case_sensitive(r"\bxox[bp]-[0-9A-Za-z-]{10,}"),
            0.85,
        ),
        Pattern(
            "Slack refresh token",
            _case_sensitive(r"\bxoxe-[0-9A-Za-z-]{10,}"),
            0.85,
        ),
        Pattern(
            "Slack rotated access token",
            _case_sensitive(r"\bxoxe\.xox[bp]-[0-9A-Za-z-]{10,}"),
            0.85,
        ),
        Pattern(
            "Slack app-level token",
            _case_sensitive(r"\bxapp-[0-9A-Za-z-]{10,}"),
            0.85,
        ),
        Pattern(
            "Slack workflow token",
            _case_sensitive(r"\bxwfp-[0-9A-Za-z-]{10,}"),
            0.85,
        ),
        # Secret (sk_) and restricted (rk_) keys are private in both live and
        # sandbox modes. Publishable keys (pk_) are documented as safe to
        # expose.
        Pattern(
            "Stripe secret or restricted key",
            _case_sensitive(r"\b(?:sk|rk)_(?:live|test)_[0-9A-Za-z]{24,}"),
            0.9,
        ),
        # This intentionally covers the common compact signed JWT subset whose
        # header and claims set both begin with '{"'. RFC 7519 also permits
        # other JSON serialization and JWE forms; those do not have an equally
        # precise textual marker and are outside this pattern's scope.
        Pattern(
            "Common compact signed JSON Web Token",
            _case_sensitive(
                r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\."
                r"[A-Za-z0-9_-]{8,}"
            ),
            0.6,
        ),
    ]

    CONTEXT = [
        "api",
        "key",
        "token",
        "secret",
        "credential",
        "authorization",
        "bearer",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "API_KEY",
        regex_flags: int = re.DOTALL | re.MULTILINE,
        name: Optional[str] = None,
    ):
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            global_regex_flags=regex_flags,
            name=name,
        )
