import pytest

from tests import assert_result_within_score_range
from presidio_analyzer.predefined_recognizers import IpRecognizer


@pytest.fixture(scope="module")
def recognizer():
    return IpRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["IP_ADDRESS"]


def assert_results_match(
    results,
    expected_positions,
    expected_score_ranges,
    entities,
    max_score,
):
    ordered_results = sorted(results, key=lambda result: (result.start, result.end))
    for res, (st_pos, fn_pos), (st_score, fn_score) in zip(
        ordered_results, expected_positions, expected_score_ranges
    ):
        if fn_score == "max":
            fn_score = max_score
        assert_result_within_score_range(
            res, entities[0], st_pos, fn_pos, st_score, fn_score
        )


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # IPv4 tests
        ("microsoft.com 192.168.0.1", 1, ((14, 25),), ((0.6, 0.81),),),
        ("my ip: 192.168.0", 0, (), (),),
        # IPv6 tests
        ("microsoft.com 684D:1111:222:3333:4444:5555:6:77", 1, ((14, 47),), ((0.6, 0.81),),),  # noqa: E501
        ("my ip: 684D:1111:222:3333:4444:5555:6:77", 1, ((7, 40),), ((0.6, 0.81),),),  # noqa: E501
        ("684D:1111:222:3333:4444:5555:77", 0, (), (),),
        ("2345:0425:2CA1:0000:0000:0567:5673:23b5", 1, (), (),),  # noqa: E501
        ("2345:0425:2CA1::0567:5673:23b5", 1, (), (),),
        ("2400:c401::5054:ff:fe1b:b031", 1, (), (),),
        ("Use local ipv6 ::", 1, ((15, 17),), ((0.05, 0.15),),),
        # IPv6 loopback (::1) should match at high confidence
        ("my ip: ::1", 1, ((7, 10),), ((0.6, 0.81),),),
        ("connecting from ::1", 1, ((16, 19),), ((0.6, 0.81),),),
        # bare :: and ::1 in same string should each match once
        ("src=:: dst=::1", 2, ((4, 6), (11, 14)), ((0.05, 0.15), (0.6, 0.81)),),
        # fmt: on
    ],
)
def test_when_all_ips_then_succeed(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    assert_results_match(
        results, expected_positions, expected_score_ranges, entities, max_score
    )


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        ("2400:c401::5054:ff:fe1b:b031", 1, ((0, 28),), ((0.6, 0.81),),),
        ("fe80::1", 1, ((0, 7),), ((0.6, 0.81),),),
        ("2001:db8::8a2e:370:7334", 1, ((0, 23),), ((0.6, 0.81),),),
        ("2001:db8:85a3::8a2e:370", 1, ((0, 23),), ((0.6, 0.81),),),
        ("2001:db8::1", 1, ((0, 11),), ((0.6, 0.81),),),
        ("fe80::1%eth0", 1, ((0, 12),), ((0.6, 0.81),),),
        # Regression for issue #1476: 1 group before :: must match fully
        ("A099::09C0:876A:130B", 1, ((0, 20),), ((0.6, 0.81),),),
        # fmt: on
    ],
)
def test_when_ipv6_compression_then_succeed(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    assert_results_match(
        results, expected_positions, expected_score_ranges, entities, max_score
    )


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # IPv6 addresses in realistic contexts
        ("Server IP: 2001:db8::1", 1, ((11, 22),), ((0.6, 0.81),),),
        ("Connect to [2001:db8::1]:8080", 1, ((12, 23),), ((0.6, 0.81),),),
        ("my ip is 2400:c401::5054:ff:fe1b:b031", 1, ((9, 37),), ((0.6, 0.81),),),
        ("Gateway: fe80::1 on interface", 1, ((9, 16),), ((0.6, 0.81),),),
        ("Visit http://[2001:db8::1]/path", 1, ((14, 25),), ((0.6, 0.81),),),
        ("SSH to user@2001:db8::1", 1, ((12, 23),), ((0.6, 0.81),),),
        # fmt: on
    ],
)
def test_when_ipv6_in_context_then_succeed(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    assert_results_match(
        results, expected_positions, expected_score_ranges, entities, max_score
    )


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # IPv4-mapped addresses (::ffff:x.x.x.x) — RFC 4291 §2.5.5.2
        # These represent IPv4 addresses in IPv6 notation and should be
        # redacted as a single span to avoid leaking the ::ffff: prefix.
        ("::ffff:192.0.2.1", 1, ((0, 16),), ((0.6, 0.81),),),
        ("::ffff:10.0.0.1", 1, ((0, 15),), ((0.6, 0.81),),),
        ("::ffff:172.16.0.1", 1, ((0, 17),), ((0.6, 0.81),),),
        ("::ffff:127.0.0.1", 1, ((0, 16),), ((0.6, 0.81),),),
        ("::ffff:255.255.255.255", 1, ((0, 22),), ((0.6, 0.81),),),
        ("::ffff:0.0.0.0", 1, ((0, 14),), ((0.6, 0.81),),),
        # With leading zero variant (::ffff:0:x.x.x.x)
        ("::ffff:0:192.168.1.1", 1, ((0, 20),), ((0.6, 0.81),),),
        ("::ffff:0000:10.0.0.1", 1, ((0, 20),), ((0.6, 0.81),),),
        # In context — full span must be redacted, not just the IPv4 part
        ("Mapped: ::ffff:192.168.1.1", 1, ((8, 26),), ((0.6, 0.81),),),
        ("Connect to ::ffff:10.0.0.1 now", 1, ((11, 26),), ((0.6, 0.81),),),
        ("[::ffff:192.168.1.1]:80", 1, ((1, 19),), ((0.6, 0.81),),),
        # IPv4-compatible addresses (::x.x.x.x) — RFC 4291 (deprecated)
        ("::192.168.1.1", 1, ((0, 13),), ((0.6, 0.81),),),
        ("::10.0.0.1", 1, ((0, 10),), ((0.6, 0.81),),),
        # Invalid — bad IPv4 octets should not match the mapped pattern
        ("::ffff:256.0.0.1", 0, (), (),),
        ("::ffff:192.168.1", 0, (), (),),
        # fmt: on
    ],
)
def test_when_ipv4_mapped_then_full_span_redacted(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    assert_results_match(
        results, expected_positions, expected_score_ranges, entities, max_score
    )


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # IPv4-embedded addresses (hex:...:x.x.x.x) — RFC 4291 §2.2 form 3
        # These embed an IPv4 address after hex groups with :: compression.
        # The full address must be redacted as a single span.
        ("2001:db8::192.168.1.1", 1, ((0, 21),), ((0.6, 0.81),),),
        ("2001:db8:1::192.0.2.1", 1, ((0, 21),), ((0.6, 0.81),),),
        ("64:ff9b::192.0.2.1", 1, ((0, 18),), ((0.6, 0.81),),),
        ("2001:db8:85a3::8a2e:192.168.0.1", 1, ((0, 31),), ((0.6, 0.81),),),
        # Should recognize expanded IPv6 before :: — RFC 4291 §2.2 form 3
        ("0:0:0:0:0:FFFF:129.144.52.38", 1, ((0, 28),), ((0.6, 0.81),),),
        ("2001:db8:0:0:0:0:192.168.1.1", 1, ((0, 28),), ((0.6, 0.81),),),
        # In context
        ("NAT64: 64:ff9b::198.51.100.1", 1, ((7, 28),), ((0.6, 0.81),),),
        ("Tunnel to 2001:db8::10.0.0.1", 1, ((10, 28),), ((0.6, 0.81),),),
        # Invalid — bad IPv4 octets
        ("2001:db8::256.1.1.1", 0, (), (),),
        # fmt: on
    ],
)
def test_when_ipv4_embedded_then_full_span_redacted(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    assert_results_match(
        results, expected_positions, expected_score_ranges, entities, max_score
    )


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # Multiple IP addresses in same text
        ("IPv4: 192.168.1.1, IPv6: 2001:db8::1", 2, ((6, 17), (25, 36)), ((0.6, 0.81), (0.6, 0.81)),),
        ("Primary: 10.0.0.1, Secondary: 172.16.0.1", 2, ((9, 17), (30, 40)), ((0.6, 0.81), (0.6, 0.81)),),
        ("IPs: 192.168.1.1, 10.0.0.1, 2001:db8::1", 3, ((5, 16), (18, 26), (28, 39)), ((0.6, 0.81), (0.6, 0.81), (0.6, 0.81)),),
        # fmt: on
    ],
)
def test_when_multiple_ips_then_all_found(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    assert_results_match(
        results, expected_positions, expected_score_ranges, entities, max_score
    )


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # These should NOT be detected as IP addresses
        ("MAC address aa:bb:cc:dd:ee:ff", 0, (), (),),
        ("Time 12:34:56", 0, (), (),),
        ("Ratio 1:2:3:4", 0, (), (),),
        ("CSS color #ff00aa", 0, (), (),),
        ("Version 1.2.3", 0, (), (),),
        ("Port 80:443", 0, (), (),),
        ("abc:def:ghi", 0, (), (),),
        ("123:abc", 0, (), (),),
        ("file:///path/to/file", 0, (), (),),
        ("std::cout", 0, (), (),),
        ("MyClass::toString", 0, (), (),),
        (":::", 0, (), (),),
        # fmt: on
    ],
)
def test_when_non_ip_pattern_then_no_match(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    assert_results_match(
        results, expected_positions, expected_score_ranges, entities, max_score
    )


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # Edge cases for boundary detection
        ("IP192.168.1.1text", 0, (), (),),
        ("text192.168.1.1", 0, (), (),),
        ("(192.168.1.1)", 1, ((1, 12),), ((0.6, 0.81),),),
        ("'2001:db8::1'", 1, ((1, 12),), ((0.6, 0.81),),),
        ("IP: 192.168.1.1.", 1, ((4, 15),), ((0.6, 0.81),),),
        ("192.168.1.1,", 1, ((0, 11),), ((0.6, 0.81),),),
        ("[2001:db8::1]", 1, ((1, 12),), ((0.6, 0.81),),),
        ("Server IP: 2400:c401::5054:ff:fe1b:b031.", 1, ((11, 39),), ((0.6, 0.81),),),
        ("2001:db8::1.", 1, ((0, 11),), ((0.6, 0.81),),),
        # IPv6 should not match when glued to surrounding text
        ("fe80::1text", 0, (), (),),
        ("text2001:db8::1", 0, (), (),),
        # 192.168.1.1 is matched, but the trailing .1 should not be included
        ("192.168.1.1.1", 1, ((0, 11),), ((0.6, 0.81),),),
        # fmt: on
    ],
)
def test_when_ip_at_boundary_then_correct_span(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    assert_results_match(
        results, expected_positions, expected_score_ranges, entities, max_score
    )


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # Should be rejected by validation
        ("256.256.256.256", 0, (), (),),
        ("192.168.1.256", 0, (), (),),
        ("gggg:hhhh::1234", 0, (), (),),
        ("192.168.1", 0, (), (),),
        ("300.168.1.1", 0, (), (),),
        ("12345:db8::1", 0, (), (),),
        ("2001::db8::1", 0, (), (),),
        # Regression for issue #1476: multiple :: in an address must not match
        ("2001::25de::cade", 0, (), (),),
        # Zone suffixes are not valid for IPv4
        # IPv4 address substring is valid and should still be matched
        ("192.168.2.1@eth0", 1, ((0, 11),), ((0.6, 0.81),),),
        # Word-adjacent IPv4-mapped/embedded should not match full span
        # Plain IPv4 portion will still match independently
        ("text::ffff:192.0.2.1", 1, ((11, 20),), ((0.6, 0.81),),),
        ("foo2001:db8::10.0.0.1", 1, ((13, 21),), ((0.6, 0.81),),),
        # fmt: on
    ],
)
def test_when_invalid_ip_then_no_match(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    assert_results_match(
        results, expected_positions, expected_score_ranges, entities, max_score
    )


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # Additional IPv4 edge cases
        ("localhost 127.0.0.1", 1, ((10, 19),), ((0.6, 0.81),),),
        ("Broadcast 255.255.255.255", 1, ((10, 25),), ((0.6, 0.81),),),
        ("Private 10.0.0.0", 1, ((8, 16),), ((0.6, 0.81),),),
        ("Link-local 169.254.1.1", 1, ((11, 22),), ((0.6, 0.81),),),
        ("Subnet 172.16.0.0", 1, ((7, 17),), ((0.6, 0.81),),),
        ("Default 0.0.0.0", 1, ((8, 15),), ((0.6, 0.81),),),
        # Additional IPv6 edge cases
        ("Unspecified ::", 1, ((12, 14),), ((0.05, 0.15),),),
        ("Loopback ::1", 1, ((9, 12),), ((0.6, 0.81),),),
        ("Multicast ff02::1", 1, ((10, 17),), ((0.6, 0.81),),),
        # fmt: on
    ],
)
def test_when_special_ip_variants_then_succeed(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    assert_results_match(
        results, expected_positions, expected_score_ranges, entities, max_score
    )


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # IPv4 CIDR
        ("192.168.1.0/24", 1, ((0, 14),), ((0.6, 0.81),),),
        ("10.0.0.0/8", 1, ((0, 10),), ((0.6, 0.81),),),
        ("0.0.0.0/0", 1, ((0, 9),), ((0.6, 0.81),),),
        ("192.168.1.1/32", 1, ((0, 14),), ((0.6, 0.81),),),
        # IPv6 CIDR
        ("2001:db8::/32", 1, ((0, 13),), ((0.6, 0.81),),),
        ("fe80::/10", 1, ((0, 9),), ((0.6, 0.81),),),
        ("::1/128", 1, ((0, 7),), ((0.6, 0.81),),),
        # IPv6 CIDR with zone index
        (f"fe80::1%eth0/64", 1, ((0, 15),), ((0.6, 0.81),),),
        (f"2001:db8::%eth0/128", 1, ((0, 19),), ((0.6, 0.81),),),
        # Unspecified with CIDR
        ("::/0", 1, ((0, 4),), ((0.05, 0.15),),),
        ("::/128", 1, ((0, 6),), ((0.05, 0.15),),),
        # IPv4-mapped and embedded with CIDR
        ("::ffff:192.168.1.0/96", 1, ((0, 21),), ((0.6, 0.81),),),
        ("64:ff9b::192.0.2.0/96", 1, ((0, 21),), ((0.6, 0.81),),),
        # CIDR in context
        ("Subnet: 192.168.1.0/24", 1, ((8, 22),), ((0.6, 0.81),),),
        ("Prefix: 2001:db8::/32", 1, ((8, 21),), ((0.6, 0.81),),),
        ("Route is 10.0.0.0/8.", 1, ((9, 19),), ((0.6, 0.81),),),
        ("Use 2001:db8::/32.", 1, ((4, 17),), ((0.6, 0.81),),),
        # Invalid CIDR suffix, base IP still redacted
        ("10.0.0.0/123", 1, ((0, 8),), ((0.6, 0.81),),),
        ("2001:db8::/9999", 1, ((0, 10),), ((0.6, 0.81),),),
        # fmt: on
    ],
)
def test_when_cidr_notation_then_largest_span_redacted(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    assert_results_match(
        results, expected_positions, expected_score_ranges, entities, max_score
    )
