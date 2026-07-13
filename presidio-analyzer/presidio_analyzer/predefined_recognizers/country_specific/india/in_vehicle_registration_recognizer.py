from typing import List, Optional, Tuple

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer


class InVehicleRegistrationRecognizer(PatternRecognizer):
    """
    Recognizes Indian Vehicle Registration Number issued by RTO.

    Reference(s):
    https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_India
    https://en.wikipedia.org/wiki/Regional_Transport_Office
    https://en.wikipedia.org/wiki/List_of_Regional_Transport_Office_districts_in_India

    The registration scheme changed over time with multiple formats
    in play over the years
    India has multiple active patterns for registration plates issued to different
    vehicle categories

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
        for different strings to be used during pattern matching.
    This can allow a greater variety in input e.g. by removing dashes or spaces
    """

    COUNTRY_CODE = "in"

    PATTERNS = [
        Pattern(
            "India Vehicle Registration (Very Weak)",
            r"\b[A-Z]{1}(?!0000)[0-9]{4}\b",
            0.01,
        ),
        Pattern(
            "India Vehicle Registration (Very Weak)",
            r"\b[A-Z]{2}(?!0000)\d{4}\b",
            0.01,
        ),
        Pattern(
            "India Vehicle Registration (Very Weak)",
            r"\b(I)(?!00000)\d{5}\b",
            0.01,
        ),
        Pattern(
            "India Vehicle Registration (Weak)",
            r"\b[A-Z]{3}(?!0000)\d{4}\b",
            0.20,
        ),
        Pattern(
            "India Vehicle Registration (Medium)",
            r"\b\d{1,3}(CD|CC|UN)[1-9]{1}[0-9]{1,3}\b",
            0.40,
        ),
        Pattern(
            "India Vehicle Registration",
            r"\b[A-Z]{2}\d{1}[A-Z]{1,3}(?!0000)\d{4}\b",
            0.50,
        ),
        Pattern(
            "India Vehicle Registration",
            r"\b[A-Z]{2}\d{2}[A-Z]{1,2}(?!0000)\d{4}\b",
            0.50,
        ),
        Pattern(
            "India Vehicle Registration",
            r"\b[2-9]{1}[1-9]{1}(BH)(?!0000)\d{4}[A-HJ-NP-Z]{2}\b",
            0.85,
        ),
        Pattern(
            "India Vehicle Registration",
            r"\b(?!00)\d{2}(A|B|C|D|E|F|H|K|P|R|X)\d{6}[A-Z]{1}\b",
            0.85,
        ),
    ]

    CONTEXT = ["RTO", "vehicle", "plate", "registration"]

    # fmt: off
    in_vehicle_foreign_mission_codes = {
        84, 85, 89, 93, 94, 95, 97, 98, 99, 102, 104, 105, 106, 109, 111, 112,
        113, 117, 119, 120, 121, 122, 123, 125, 126, 128, 133, 134, 135, 137,
        141, 145, 147, 149, 152, 153, 155, 156, 157, 159, 160
    }

    in_vehicle_armed_forces_codes = {
        'A', 'B', 'C', 'D', 'E', 'F', 'H', 'K', 'P', 'R', 'X'}
    in_vehicle_diplomatic_codes = {"CC", "CD", "UN"}
    in_vehicle_dist_an = {"01"}
    in_vehicle_dist_ap = {"39", "40"}
    in_vehicle_dist_ar = {
        "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12",
        "13", "14", "15", "16", "17", "19", "20", "22"
    }
    in_vehicle_dist_as = {
        "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12",
        "13", "14", "15", "16", "17", "18", "19", "20", "22", "23", "24", "25",
        "26", "27", "28", "29", "30", "31", "32", "33", "34"
    }
    in_vehicle_dist_br = {
        "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "19",
        "21", "22", "24", "25", "26", "27", "28", "29", "30", "31", "32", "33",
        "34", "37", "38", "39", "43", "44", "45", "46", "50", "51", "52", "53",
        "55", "56"
    }
    in_vehicle_dist_cg = {
        "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12",
        "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24",
        "25", "26", "27", "28", "29", "30"
    }
    in_vehicle_dist_ch = {"01", "02", "03", "04"}
    in_vehicle_dist_dd = {"01", "02", "03"}
    in_vehicle_dist_dn = {"09"}  # old list
    in_vehicle_dist_dl = {
        "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"}
    in_vehicle_dist_ga = {
        "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"}
    in_vehicle_dist_gj = {
        "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13",
        "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25",
        "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37",
        "38", "39"
    }
    in_vehicle_dist_hp = {
        "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12",
        "13", "14", "15", "16", "17", "18", "19", "20", "22", "23", "24", "25",
        "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37",
        "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49",
        "50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60", "61",
        "62", "63", "64", "65", "66", "67", "68", "69", "70", "71", "72", "73",
        "74", "75", "76", "77", "78", "79", "80", "81", "82", "83", "84", "85",
        "86", "87", "88", "89", "90", "91", "92", "93", "94", "95", "96", "97",
        "98", "99"
    }
    in_vehicle_dist_hr = {
        "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12",
        "13", "14", "15", "16", "17", "18", "19", "20", "22", "23", "24", "25",
        "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37",
        "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49",
        "50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60", "61",
        "62", "63", "64", "65", "66", "67", "68", "69", "70", "71", "72", "73",
        "74", "75", "76", "77", "78", "79", "80", "81", "82", "83", "84", "85",
        "86", "87", "88", "89", "90", "91", "92", "93", "94", "95", "96", "97",
        "98", "99"
    }
    in_vehicle_dist_jh = {
        "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12",
        "13", "14", "15", "16", "17", "18", "19", "20", "22", "23", "24"
    }
    in_vehicle_dist_jk = {
        "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12",
        "13", "14", "15", "16", "17", "18", "19", "20", "22"
    }
    in_vehicle_dist_ka = {
        "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12",
        "13", "14", "15", "16", "17", "18", "19", "20", "22", "23", "24", "25",
        "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37",
        "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49",
        "50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60", "61",
        "62", "63", "64", "65", "66", "67", "68", "69", "70", "71"
    }
    in_vehicle_dist_kl = {
        "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12",
        "13", "14", "15", "16", "17", "18", "19", "20", "22", "23", "24", "25",
        "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37",
        "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49",
        "50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60", "61",
        "62", "63", "64", "65", "66", "67", "68", "69", "70", "71", "72", "73",
        "74", "75", "76", "77", "78", "79", "80", "81", "82", "83", "84", "85",
        "86", "87", "88", "89", "90", "91", "92", "93", "94", "95", "96", "97",
        "98", "99"
    }
    in_vehicle_dist_la = {"01", "02"}
    in_vehicle_dist_ld = {"01", "02", "03", "04", "05", "06", "07", "08", "09"}
    in_vehicle_dist_mh = {
        "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12",
        "13", "14", "15", "16", "17", "18", "19", "20", "22", "23", "24", "25",
        "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37",
        "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49",
        "50", "51"
    }
    in_vehicle_dist_ml = {
        "01", "02", "03", "04", "05", "06", "07", "08", "09", "10"}
    in_vehicle_dist_mn = {"01", "02", "03", "04", "05", "06", "07"}
    in_vehicle_dist_mp = {
        "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12",
        "13", "14", "15", "16", "17", "18", "19", "20", "22", "23", "24", "25",
        "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37",
        "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49",
        "50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60", "61",
        "62", "63", "64", "65", "66", "67", "68", "69", "70", "71"
    }
    in_vehicle_dist_mz = {"01", "02", "03", "04", "05", "06", "07", "08"}
    in_vehicle_dist_nl = {"01", "02", "03", "04", "05", "06", "07", "08", "09", "10"}
    in_vehicle_dist_od = {
        "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12",
        "13", "14", "15", "16", "17", "18", "19", "20", "22", "23", "24", "25",
        "26", "27", "28", "29", "30", "31", "32", "33", "34", "35"
    }
    in_vehicle_dist_or = {
        "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12",
        "13", "14", "15", "16", "17", "18", "19", "20", "22", "23", "24", "25",
        "26", "27", "28", "29", "30", "31"
    }  # old list
    in_vehicle_dist_pb = {
        "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12",
        "13", "14", "15", "16", "17", "18", "19", "20", "22", "23", "24", "25",
        "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37",
        "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49",
        "50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60", "61",
        "62", "63", "64", "65", "66", "67", "68", "69", "70", "71", "72", "73",
        "74", "75", "76", "77", "78", "79", "80", "81", "82", "83", "84", "85",
        "86", "87", "88", "89", "90", "91", "92", "93", "94", "95", "96", "97",
        "98", "99"
    }
    in_vehicle_dist_py = {"01", "02", "03", "04", "05"}
    in_vehicle_dist_rj = {
        "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12",
        "13", "14", "15", "16", "17", "18", "19", "20", "22", "23", "24", "25",
        "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37",
        "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49",
        "50", "51", "52", "53", "54", "55", "56", "57", "58"
    }
    in_vehicle_dist_sk = {"01", "02", "03", "04", "05", "06", "07", "08"}
    in_vehicle_dist_tn = {
        "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12",
        "13", "14", "15", "16", "17", "18", "19", "20", "22", "23", "24", "25",
        "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37",
        "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49",
        "50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60", "61",
        "62", "63", "64", "65", "66", "67", "68", "69", "70", "71", "72", "73",
        "74", "75", "76", "77", "78", "79", "80", "81", "82", "83", "84", "85",
        "86", "87", "88", "89", "90", "91", "92", "93", "94", "95", "96", "97",
        "98", "99"
    }
    in_vehicle_dist_tr = {"01", "02", "03", "04", "05", "06", "07", "08"}
    in_vehicle_dist_ts = {
        "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12",
        "13", "14", "15", "16", "17", "18", "19", "20", "22", "23", "24", "25",
        "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37",
        "38"
    }
    in_vehicle_dist_uk = {
        "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12",
        "13", "14", "15", "16", "17", "18", "19", "20"
    }
    in_vehicle_dist_up = {
        "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "22", "23",
        "24", "25", "26", "27", "28", "29", "30", "31", "32", "33", "34", "35",
        "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46", "47",
        "48", "49", "50", "51", "52", "53", "54", "55", "56", "57", "58", "59",
        "60", "61", "62", "63", "64", "65", "66", "67", "68", "69", "70", "71",
        "72", "73", "74", "75", "76", "77", "78", "79", "80", "81", "82", "83",
        "84", "85", "86", "87", "88", "89", "90", "91", "92", "93", "94", "95",
        "96"
    }
    in_vehicle_dist_wb = {
        "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12",
        "13", "14", "15", "16", "17", "18", "19", "20", "22", "23", "24", "25",
        "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37",
        "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49",
        "50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60", "61",
        "62", "63", "64", "65", "66", "67", "68", "69", "70", "71", "72", "73",
        "74", "75", "76", "77", "78", "79", "80", "81", "82", "83", "84", "85",
        "86", "87", "88", "89", "90", "91", "92", "93", "94", "95", "96", "97",
        "98"
    }
    in_union_territories = {"AN", "CH", "DH", "DL", "JK", "LA", "LD", "PY"}
    in_old_union_territories = {"CT", "DN"}
    in_states = {
        "AP", "AR", "AS", "BR", "CG", "GA", "GJ", "HR", "HP", "JH", "KA", "KL",
        "MP", "MH", "MN", "ML", "MZ", "NL", "OD", "PB", "RJ", "SK", "TN", "TS",
        "TR", "UP", "UK", "WB", "UT"
    }
    in_old_states = {"UL", "OR", "UA"}
    in_non_standard_state_or_ut = {"DD"}

    state_rto_district_map = {
        "AN": in_vehicle_dist_an,
        "AP": in_vehicle_dist_ap,
        "AR": in_vehicle_dist_ar,
        "AS": in_vehicle_dist_as,
        "BR": in_vehicle_dist_br,
        "CG": in_vehicle_dist_cg,
        "CH": in_vehicle_dist_ch,
        "DD": in_vehicle_dist_dd,
        "DN": in_vehicle_dist_dn,
        "DL": in_vehicle_dist_dl,
        "GA": in_vehicle_dist_ga,
        "GJ": in_vehicle_dist_gj,
        "HP": in_vehicle_dist_hp,
        "HR": in_vehicle_dist_hr,
        "JH": in_vehicle_dist_jh,
        "JK": in_vehicle_dist_jk,
        "KA": in_vehicle_dist_ka,
        "KL": in_vehicle_dist_kl,
        "LA": in_vehicle_dist_la,
        "LD": in_vehicle_dist_ld,
        "MH": in_vehicle_dist_mh,
        "ML": in_vehicle_dist_ml,
        "MN": in_vehicle_dist_mn,
        "MP": in_vehicle_dist_mp,
        "MZ": in_vehicle_dist_mz,
        "NL": in_vehicle_dist_nl,
        "OD": in_vehicle_dist_od,
        "OR": in_vehicle_dist_or,
        "PB": in_vehicle_dist_pb,
        "PY": in_vehicle_dist_py,
        "RJ": in_vehicle_dist_rj,
        "SK": in_vehicle_dist_sk,
        "TN": in_vehicle_dist_tn,
        "TR": in_vehicle_dist_tr,
        "TS": in_vehicle_dist_ts,
        "UK": in_vehicle_dist_uk,
        "UP": in_vehicle_dist_up,
        "WB": in_vehicle_dist_wb,
    }

    two_factor_registration_prefix = set()
    two_factor_registration_prefix |= in_union_territories
    two_factor_registration_prefix |= in_states
    two_factor_registration_prefix |= in_old_states
    two_factor_registration_prefix |= in_old_union_territories
    two_factor_registration_prefix |= in_non_standard_state_or_ut
    # fmt: on

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "IN_VEHICLE_REGISTRATION",
        replacement_pairs: Optional[List[Tuple[str, str]]] = None,
        name: Optional[str] = None,
    ):
        self.replacement_pairs = (
            replacement_pairs
            if replacement_pairs
            else [("-", ""), (" ", ""), (":", "")]
        )
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def validate_result(self, pattern_text: str) -> bool:
        """Determine absolute value based on calculation."""
        sanitized_value = EntityRecognizer.sanitize_value(
            pattern_text, self.replacement_pairs
        )
        return self.__check_vehicle_registration(sanitized_value)

    def __check_vehicle_registration(self, sanitized_value: str) -> bool:
        # print('check function called')
        is_valid_registration = None  # deliberately not typecasted or set to bool False
        # logic here
        if len(sanitized_value) >= 8:
            first_two_char = sanitized_value[:2].upper()
            dist_code: str = ""

            if first_two_char in self.two_factor_registration_prefix:
                if sanitized_value[2].isdigit():
                    if sanitized_value[3].isdigit():
                        dist_code = sanitized_value[2:4]
                    else:
                        dist_code = sanitized_value[2:3]

                    registration_digits = sanitized_value[-4:]
                    if registration_digits.isnumeric():
                        if 0 < int(registration_digits) <= 9999:
                            district_set = self.state_rto_district_map.get(
                                first_two_char, ""
                            )
                            # Some states store single-digit district codes
                            # ("1".."9") while a modern plate zero-pads them
                            # ("DL01"); normalise the leading zero so a valid
                            # padded district still matches.
                            if dist_code and (
                                dist_code in district_set
                                or str(int(dist_code)) in district_set
                            ):
                                is_valid_registration = True

                for diplomatic_vehicle_code in self.in_vehicle_diplomatic_codes:
                    if diplomatic_vehicle_code in sanitized_value:
                        vehicle_prefix = sanitized_value.partition(
                            diplomatic_vehicle_code
                        )[0]
                        if vehicle_prefix.isnumeric() and (
                            1 <= int(vehicle_prefix) <= 80
                            or int(vehicle_prefix)
                            in self.in_vehicle_foreign_mission_codes
                        ):
                            is_valid_registration = True

        return is_valid_registration
