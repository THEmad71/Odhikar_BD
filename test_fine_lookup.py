
import pytest

from src.odhikar.tools import fine_lookup


@pytest.mark.parametrize(
    "query",
    [
        "no_helmet",
        "helmet nai",
        "helmet chara",
        "amar helmet chilo na",
        "riding a motorcycle without wearing a helmet",
    ],
)
def test_fine_lookup_success(query):

    result = fine_lookup(
        offence=query,
        vehicle_type="motorcycle",
    )

    assert result["status"] == "success"
    assert result["offence_id"] == "no_helmet"
    assert result["max_fine_bdt"] == 10000


def test_fine_lookup_unknown_offence():

    result = fine_lookup(
        offence="unknown offence",
        vehicle_type="motorcycle",
    )

    assert result["status"] == "not_found"


def test_fine_lookup_vehicle_mismatch():

    result = fine_lookup(
        offence="no_helmet",
        vehicle_type="car",
    )

    assert result["status"] == "vehicle_mismatch"


def test_fine_lookup_empty_input():

    result = fine_lookup(
        offence="",
        vehicle_type="motorcycle",
    )

    assert result["status"] == "invalid_input"
