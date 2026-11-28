import re
from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer

# Whitespace allowed between the parts of a coordinate. It is short, bounded and
# single-line, so long runs of spaces cannot cause slow matching and a pair
# cannot span two lines of a table.
_WS = r"[ \t]{0,3}"

# Latitude and longitude values, written so that out-of-range values
# (for example 91.12345 or 181.12345) cannot match.
_LAT = r"(?:90(?:\.0{4,8})|[1-8]?\d\.\d{4,8})"
_LON = r"(?:180(?:\.0{4,8})|(?:1[0-7]\d|[1-9]?\d)\.\d{4,8})"

# Hemisphere letters must be uppercase, even though the registry compiles
# patterns case-insensitively: "12.50 s, 30.25 w" is not a coordinate.
_NS = r"(?-i:[NS])"
_EW = r"(?-i:[EW])"

_MINUTE_MARK = r"['′]"
_SECOND_MARK = r"(?:[\"″]|''|′′)"
_SECONDS = r"(?:([0-5]?\d(?:\.\d{1,6})?)" + _WS + _SECOND_MARK + _WS + r")?"

# Degrees, minutes and seconds. Minutes and seconds are range checked here;
# 90 and 180 degrees with non-zero minutes are rejected in invalidate_result.
_DMS_REGEX = (
    r"(?<![\w.])"
    r"(90|[1-8]?\d)"
    + _WS
    + r"°"
    + _WS
    + r"([0-5]?\d)"
    + _WS
    + _MINUTE_MARK
    + _WS
    + _SECONDS
    + r"("
    + _NS
    + r")"
    + _WS
    + r",?"
    + _WS
    + r"(180|1[0-7]\d|[1-9]?\d)"
    + _WS
    + r"°"
    + _WS
    + r"([0-5]?\d)"
    + _WS
    + _MINUTE_MARK
    + _WS
    + _SECONDS
    + r"("
    + _EW
    + r")(?![A-Za-z0-9])"
)


class GeoCoordinatesRecognizer(PatternRecognizer):
    """
    Recognize geographic coordinates (latitude and longitude) using regex.

    Supports four common notations:
    - Decimal degrees pair: 40.7128, -74.0060
    - Decimal degrees with hemisphere: 40.4461° N, 79.9822° W
    - Degrees, minutes and seconds: 40°26'46"N 79°58'56"W
    - geo URI: geo:40.7128,-74.0060

    Matches are range checked: latitude must be within +/-90 and longitude
    within +/-180, minutes and seconds must be below 60, and the (0, 0)
    "null island" placeholder is rejected. Hemisphere letters must be uppercase.

    Bare decimal pairs need at least four fractional digits on both numbers,
    which keeps prices and short measurements from matching. They still score
    low, since numeric pairs in telemetry or scientific text can look the same.

    The compact ISO 6709 string, NMEA sentences, EXIF text and keyed JSON values
    are not detected.

    ref :
    - ISO 6709:2022, Standard representation of geographic point location by
      coordinates (decimal degrees and degrees, minutes, seconds notations)
    - RFC 5870, A Uniform Resource Identifier for Geographic Locations
      ('geo' URI): https://datatracker.ietf.org/doc/html/rfc5870
    - WGS 84 (EPSG:4326), the default coordinate reference system of the geo URI

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param name: Name of the recognizer
    """

    PATTERNS = [
        Pattern(
            "Decimal degrees pair (weak)",
            r"(?<![\w.:])[+\-−]?"
            + _LAT
            + _WS
            + r","
            + _WS
            + r"[+\-−]?"
            + _LON
            + r"(?![\w]|\.\d)",
            0.2,
        ),
        Pattern(
            "Decimal degrees with hemisphere (medium)",
            r"(?<![\w.])(?:90(?:\.0{2,8})|[1-8]?\d\.\d{2,8})"
            + _WS
            + r"°?"
            + _WS
            + _NS
            + _WS
            + r",?"
            + _WS
            + r"(?:180(?:\.0{2,8})|(?:1[0-7]\d|[1-9]?\d)\.\d{2,8})"
            + _WS
            + r"°?"
            + _WS
            + _EW
            + r"(?![A-Za-z0-9])",
            0.4,
        ),
        Pattern("Degrees minutes seconds (strong)", _DMS_REGEX, 0.6),
        Pattern(
            "geo URI (strong)",
            r"(?<![\w])geo:[+-]?\d{1,3}(?:\.\d{1,10})?,[+-]?\d{1,3}(?:\.\d{1,10})?"
            r"(?:,[+-]?\d+(?:\.\d+)?)?(?:;[A-Za-z0-9-]+(?:=[\w.%-]*)?)*(?![\w])",
            0.6,
        ),
    ]

    # Context words are matched as substrings of lemmas, so "coordinate" also
    # boosts after "coordinates", the most common label, and unavoidably after
    # "coordinated". The score stays below 0.6 for bare pairs either way.
    CONTEXT = [
        "latitude",
        "longitude",
        "coordinate",
        "geolocation",
        "gps",
        "lat/long",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "GEO_COORDINATES",
        name: Optional[str] = None,
    ):
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def invalidate_result(self, pattern_text: str) -> bool:
        """
        Check that the detected text is a plausible pair of coordinates.

        :param pattern_text: Text detected as pattern by regex
        :return: True if invalidated (not a plausible coordinate pair)
        """
        dms = re.search(_DMS_REGEX, pattern_text)
        if dms:
            lat_deg, lat_min, lat_sec = (float(g or 0) for g in dms.group(1, 2, 3))
            lon_deg, lon_min, lon_sec = (float(g or 0) for g in dms.group(5, 6, 7))
            # 90 and 180 degrees are only valid with zero minutes and seconds.
            if lat_deg == 90 and (lat_min or lat_sec):
                return True
            if lon_deg == 180 and (lon_min or lon_sec):
                return True
            return not any((lat_deg, lat_min, lat_sec, lon_deg, lon_min, lon_sec))

        lat, lon = (float(n) for n in re.findall(r"\d+(?:\.\d+)?", pattern_text)[:2])
        # The geo URI pattern does not range check.
        if lat > 90 or lon > 180:
            return True
        # (0, 0) is a common "no fix" placeholder, not a real location.
        return lat == 0 and lon == 0
