"""Hypothesis integration."""

from __future__ import annotations

import math

import pytest
from hypothesis import HealthCheck, given, settings

from geofuzz import generate
from geofuzz.strategies import (
    pathological_geometries,
    pathological_linestrings,
    pathological_points,
    pathological_polygons,
)
from tests.predicates import ordinates

FAST = settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])


@FAST
@given(pathological_polygons())
def test_polygon_strategy_yields_polygons(geometry):
    assert geometry["type"] == "Polygon"
    assert len(geometry["coordinates"][0]) >= 4


@FAST
@given(pathological_linestrings())
def test_linestring_strategy_yields_linestrings(geometry):
    assert geometry["type"] == "LineString"


@FAST
@given(pathological_points())
def test_point_strategy_yields_points(geometry):
    assert geometry["type"] == "Point"


@FAST
@given(pathological_geometries("polygon", mutations=["nan_coordinates"]))
def test_explicit_mutations_are_honoured(geometry):
    assert any(not math.isfinite(value) for value in ordinates(geometry))


def test_strategy_examples_stay_reproducible_via_seed():
    """The strategy is a pure function of the seed, so failures replay exactly."""
    assert generate(geometry="polygon", mutation_count=1, seed=123) == generate(
        geometry="polygon", mutation_count=1, seed=123
    )


@pytest.mark.filterwarnings("ignore::hypothesis.errors.NonInteractiveExampleWarning")
def test_strategy_rejects_inapplicable_mutation():
    strategy = pathological_geometries("point", mutations=["self_intersection"])
    with pytest.raises(Exception):
        strategy.example()
