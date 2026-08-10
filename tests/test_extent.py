"""Dateline-aware longitude extent."""

from __future__ import annotations

import pytest

from geofuzz import generate, longitude_extent, positions


def longitudes_of(geometry):
    return [position[0] for position in positions(geometry)]


def test_ordinary_data_is_left_alone():
    assert longitude_extent([-134.0, -133.8, -133.4]) == (-134.0, -133.4, False)


def test_dateline_crossing_is_detected_and_reported_west_greater_than_east():
    west, east, crosses = longitude_extent([179.9, 179.95, -179.99, -179.95])

    assert crosses is True
    assert west > east  # RFC 7946 section 5.2 form
    assert west == pytest.approx(179.9)
    assert east == pytest.approx(-179.95)


def test_a_genuinely_global_dataset_is_not_read_as_crossing():
    assert longitude_extent([-180.0, -90.0, 0.0, 90.0, 180.0]) == (-180.0, 180.0, False)


def test_non_finite_values_are_ignored():
    assert longitude_extent([float("nan"), float("inf")]) is None
    assert longitude_extent([10.0, float("nan"), 20.0]) == (10.0, 20.0, False)


def test_empty_input_returns_none():
    assert longitude_extent([]) is None


def test_a_single_longitude_has_no_extent():
    assert longitude_extent([42.5]) == (42.5, 42.5, False)


@pytest.mark.parametrize("geometry_type", ["linestring", "polygon"])
@pytest.mark.parametrize("seed", range(20))
def test_antimeridian_mutation_produces_a_detectable_crossing(geometry_type, seed):
    geometry = generate(geometry=geometry_type, mutations=["antimeridian"], seed=seed)

    west, east, crosses = longitude_extent(longitudes_of(geometry))

    assert crosses is True
    assert west > east


@pytest.mark.parametrize("geometry_type", ["linestring", "polygon"])
@pytest.mark.parametrize("seed", range(20))
def test_clean_geometry_is_never_read_as_crossing(geometry_type, seed):
    geometry = generate(geometry=geometry_type, mutations=[], seed=seed)

    assert longitude_extent(longitudes_of(geometry))[2] is False


@pytest.mark.parametrize("seed", range(20))
def test_naive_min_max_is_wrong_where_this_helper_is_right(seed):
    """The reason this helper exists, pinned as a test."""
    geometry = generate(geometry="polygon", mutations=["antimeridian"], seed=seed)
    values = longitudes_of(geometry)

    naive_width = max(values) - min(values)
    west, east, _ = longitude_extent(values)
    true_width = (180.0 - west) + (east + 180.0)

    assert true_width < 5.0
    assert naive_width > 350.0
