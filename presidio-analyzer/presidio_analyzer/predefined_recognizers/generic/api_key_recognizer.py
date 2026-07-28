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
AWS_SECRET_ANCHOR = r"(?<=(?i:aws_secret_access_key)[\"']?[ \t]{0,8}[:=][ \t]{0,8}[\"']?)"  # noqa: E501


class ApiKeyRecognizer(PatternRecognizer):
    """
    Recognize provider-issued API keys, access keys and bearer tokens.

    Every pattern is anchored on a vendor-assigned, case-sensitive prefix (or,
    for the AWS secret access key, on the credential name AWS documents). Only
    credential formats whose prefix is stated in vendor documentation are
    included, so that a match is driven by an unambiguous structural marker
    rather than by string length or entropy.

    Note: the patterns are matched case-sensitively. Every prefix below is
    case-sensitive at the vendor, and matching case-insensitively (the
    PatternRecognizer default) would make markers such as ``AKIA`` or ``eyJ``
    fire on ordinary lowercase text.

    ref:
    - AWS access key ID prefixes (``AKIA``, ``ASIA``):
      https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_identifiers.html
    - AWS credential names (``aws_secret_access_key`` /
      ``AWS_SECRET_ACCESS_KEY``):
      https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html
    - GitHub token prefixes and base62 body:
      https://github.blog/engineering/platform-security/behind-githubs-new-authentication-token-formats/
    - Google API keys:
      https://cloud.google.com/docs/authentication/api-keys
    - Slack token prefixes:
      https://docs.slack.dev/authentication/tokens/
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
            r"\b(?:ABIA|ACCA|AKIA|ASIA)[0-9A-Z]{16}\b",
            0.9,
        ),
        Pattern(
            "AWS secret access key",
            AWS_SECRET_ANCHOR + r"[A-Za-z0-9/+=]{40}",
            0.8,
        ),
        # ghp_/gho_/ghu_/ghs_/ghr_ followed by 30 characters of base62 entropy
        # and a 6 character base62 CRC32 checksum.
        Pattern(
            "GitHub token",
            r"\bgh[pousr]_[A-Za-z0-9]{36}\b",
            0.9,
        ),
        Pattern(
            "GitHub fine-grained personal access token",
            r"\bgithub_pat_[A-Za-z0-9_]{82}\b",
            0.9,
        ),
        Pattern(
            "Google API key",
            r"\bAIza[0-9A-Za-z_-]{35}\b",
            0.9,
        ),
        Pattern(
            "Slack token",
            r"\bxox[abeprs]-[0-9A-Za-z-]{10,}",
            0.85,
        ),
        Pattern(
            "Slack app-level token",
            r"\bxapp-[0-9A-Za-z-]{10,}",
            0.85,
        ),
        # Only live-mode secret (sk_) and restricted (rk_) keys. Publishable
        # keys (pk_) are documented as safe to expose, and test-mode keys reach
        # sandbox data only.
        Pattern(
            "Stripe secret key",
            r"\b(?:sk|rk)_live_[0-9A-Za-z]{24,}",
            0.9,
        ),
        # A JWT header and payload are base64url-encoded JSON objects, so both
        # begin with "eyJ" (the encoding of '{"'). Requiring the marker on both
        # segments keeps ordinary dotted base64 out.
        Pattern(
            "JSON Web Token",
            r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}",
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
