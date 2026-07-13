import pytest

from tests import assert_result
from presidio_analyzer.predefined_recognizers import InVehicleRegistrationRecognizer


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
