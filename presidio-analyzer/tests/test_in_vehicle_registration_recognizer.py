import pytest
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.predefined_recognizers import InVehicleRegistrationRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests import assert_result


@pytest.fixture(scope="module")
def recognizer():
    return InVehicleRegistrationRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["IN_VEHICLE_REGISTRATION"]


@pytest.mark.parametrize(
    "text, expected_len, expected_position, expected_score",
    [
        # fmt: off
        ("KA53ME3456", 1, (0, 10), 1),
        ("KA99ME3456", 1, (0, 10), 0.50),
        ("MN2412", 1, (0, 6), 0.01),
        ("MCX1243", 1, (0, 7), 0.2),
        ("I15432", 1, (0, 6), 0.01),
        ("DL3CJI0001", 1, (0, 10), 1),
        # Zero-padded district codes for states whose district set is stored
        # single-digit (DL-01..DL-09, GJ-01..GJ-09) — previously scored 0.5.
        ("DL01CA1234", 1, (0, 10), 1),
        ("GJ09AB1234", 1, (0, 10), 1),
        ("ABNE123456", 0, (), (),),
        ("My Bike's registration number is OD02BA2341 with a lot of text beyond",
         1, (33, 43), 1),
        # Plates are commonly written with spaces or hyphens between groups.
        # Separated forms stay at the weak pattern score: validation only
        # drops an unknown state or district, and context lifts real plates.
        ("MH 12 AB 1234", 1, (0, 13), 0.30),
        ("KA-01-EA-1234", 1, (0, 13), 0.30),
        ("DL 3C AB 1234", 1, (0, 13), 0.30),
        ("DL-3C-AB-1234", 1, (0, 13), 0.30),
        ("DL 3 CAB 1234", 1, (0, 13), 0.30),
        ("mh 12 ab 1234", 1, (0, 13), 0.30),
        ("RTA: vehicle MH 12 AB 1234 vs two-wheeler", 1, (13, 26), 0.30),
        # Unknown state or district code: dropped.
        ("XY 99 AB 1234", 0, (), (),),
        ("MH 99 AB 1234", 0, (), (),),
        # Mixed separators and a 0000 series are not plates.
        ("MH 12-AB 1234", 0, (), (),),
        ("MH 12 AB 0000", 0, (), (),),
        # Clinical and pharmacy text of the same shape, often upper case.
        ("HR 72 BP 120", 0, (), (),),
        ("PO 1 BD 1000", 0, (), (),),
        ("PO 10 MG 1000", 0, (), (),),
        ("IV 12 MG 1234", 0, (), (),),
        ("SC 5 MG 2000", 0, (), (),),
        ("GIVE 5 OR 10 MG 1000 UNITS", 1, (7, 20), 0.30),
        ("HR 12 BP 1234", 1, (0, 13), 0.30),
        ("give 5 or 10 mg 1000 units", 1, (7, 20), 0.30),
        # fmt: on
    ],
)
def test_when_regn_in_text_then_all_regns_found(
    text,
    expected_len,
    expected_position,
    expected_score,
    recognizer,
    entities,
):
    results = recognizer.analyze(text, entities)

    assert len(results) == expected_len
    if results:
        assert_result(
            results[0],
            entities[0],
            expected_position[0],
            expected_position[1],
            expected_score,
        )


def test_list_length():
    """
    Tests for static counts of each metadata lists defined
    :return: True/False
    """
    assert len(InVehicleRegistrationRecognizer.in_old_states) == 3
    assert len(InVehicleRegistrationRecognizer.in_non_standard_state_or_ut) == 1
    assert len(InVehicleRegistrationRecognizer.in_states) == 29
    assert len(InVehicleRegistrationRecognizer.in_old_union_territories) == 2
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_wb) == 97
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_up) == 85
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_uk) == 20
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_ts) == 37
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_tr) == 8
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_tn) == 98
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_sk) == 8
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_rj) == 57
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_py) == 5
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_pb) == 98
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_or) == 30
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_od) == 34
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_nl) == 10
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_mz) == 8
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_mp) == 70
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_mn) == 7
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_ml) == 10
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_mh) == 50
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_ld) == 9
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_la) == 2
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_kl) == 98
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_ka) == 70
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_jh) == 23
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_hr) == 98
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_hp) == 98
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_gj) == 39
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_ga) == 12
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_dl) == 13
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_dn) == 1
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_dd) == 3
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_ch) == 4
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_cg) == 30
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_br) == 38
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_as) == 33
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_ar) == 20
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_ap) == 2
    assert len(InVehicleRegistrationRecognizer.in_vehicle_dist_an) == 1
    assert len(InVehicleRegistrationRecognizer.in_vehicle_diplomatic_codes) == 3
    assert len(InVehicleRegistrationRecognizer.in_vehicle_armed_forces_codes) == 11
    assert len(InVehicleRegistrationRecognizer.in_vehicle_foreign_mission_codes) == 41


@pytest.fixture(scope="module")
def yaml_analyzer(tmp_path_factory, spacy_nlp_engine):
    conf = tmp_path_factory.mktemp("conf") / "recognizers.yaml"
    conf.write_text(
        """
supported_languages:
  - en
recognizers:
  - name: InVehicleRegistrationRecognizer
    supported_languages:
      - en
    type: predefined
    enabled: true
    country_code: in
"""
    )
    registry = RecognizerRegistryProvider(conf_file=conf).create_recognizer_registry()
    return AnalyzerEngine(registry=registry, nlp_engine=spacy_nlp_engine)


@pytest.mark.parametrize(
    "text, expected_start, expected_end, expected_score",
    [
        # Context word before the plate lifts the weak separated match.
        ("Vehicle no. MH 12 AB 1234 was involved", 12, 25, 0.65),
        ("RTO registration KA-01-EA-1234 noted.", 17, 30, 0.65),
        # Unseparated plates are unchanged: validated to the maximum score.
        ("Vehicle no. MH12AB1234 was involved", 12, 22, 1.0),
    ],
)
def test_when_enabled_in_yaml_then_plate_with_context_scores_high(
    text, expected_start, expected_end, expected_score, yaml_analyzer
):
    """Context words lift separated plates through the YAML-configured analyzer."""
    results = yaml_analyzer.analyze(
        text, language="en", entities=["IN_VEHICLE_REGISTRATION"]
    )

    assert len(results) == 1
    result = results[0]
    assert result.entity_type == "IN_VEHICLE_REGISTRATION"
    assert (result.start, result.end) == (expected_start, expected_end)
    assert result.score == pytest.approx(expected_score)


@pytest.mark.parametrize(
    "text",
    [
        "GIVE 5 OR 10 MG 1000 UNITS",
        "HR 12 BP 1234",
        "PO 1 BD 1000",
        "Ambulance KA-01-EA-1234 brought the patient in.",
    ],
)
def test_when_enabled_in_yaml_then_separated_match_without_context_stays_below_04(
    text, yaml_analyzer
):
    """Without context, separated matches never reach the 0.4 threshold."""
    results = yaml_analyzer.analyze(
        text, language="en", entities=["IN_VEHICLE_REGISTRATION"]
    )

    assert all(result.score < 0.4 for result in results)
