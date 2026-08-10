"""Each mutation must actually produce the property it advertises."""

from __future__ import annotations

import math

import pytest

from geofuzz import generate
from geofuzz.geometry import build, positions
from geofuzz.mutations import MUTATIONS, UnsupportedMutationError, applicable, apply
from tests.predicates import (
    geometry_is_self_intersecting,
    has_consecutive_duplicate,
    ordinates,
    rings_are_closed,
)

SEEDS = list(range(40))
PATHS = ["linestring", "polygon"]
ALL_TYPES = ["point", "linestring", "polygon"]


@pytest.mark.parametrize("geometry_type", PATHS)
@pytest.mark.parametrize("seed", SEEDS)
def test_self_intersection_actually_self_intersects(geometry_type, seed):
    geometry = generate(geometry=geometry_type, mutations=["self_intersection"], seed=seed)
    assert geometry_is_self_intersecting(geometry)


@pytest.mark.parametrize("geometry_type", PATHS)
@pytest.mark.parametrize("seed", SEEDS)
def test_clean_base_geometry_does_not_self_intersect(geometry_type, seed):
    geometry = generate(geometry=geometry_type, mutations=[], seed=seed)
    assert not geometry_is_self_intersecting(geometry)


@pytest.mark.parametrize("geometry_type", PATHS)
@pytest.mark.parametrize("seed", SEEDS)
def test_duplicate_vertices_creates_consecutive_duplicates(geometry_type, seed):
    geometry = generate(geometry=geometry_type, mutations=["duplicate_vertices"], seed=seed)
    assert has_consecutive_duplicate(geometry)


@pytest.mark.parametrize("geometry_type", ALL_TYPES)
@pytest.mark.parametrize("seed", SEEDS)
def test_extreme_coordinates_reach_float64_limits(geometry_type, seed):
    geometry = generate(geometry=geometry_type, mutations=["extreme_coordinates"], seed=seed)
    assert any(abs(value) > 1e300 for value in ordinates(geometry) if math.isfinite(value))


@pytest.mark.parametrize("geometry_type", ALL_TYPES)
@pytest.mark.parametrize("seed", SEEDS)
def test_nan_coordinates_inject_non_finite_values(geometry_type, seed):
    geometry = generate(geometry=geometry_type, mutations=["nan_coordinates"], seed=seed)
    assert any(not math.isfinite(value) for value in ordinates(geometry))


@pytest.mark.parametrize("geometry_type", PATHS)
@pytest.mark.parametrize("seed", SEEDS)
def test_antimeridian_straddles_the_dateline(geometry_type, seed):
    geometry = generate(geometry=geometry_type, mutations=["antimeridian"], seed=seed)
    longitudes = [position[0] for position in _all_positions(geometry)]
    assert any(value > 170 for value in longitudes)
    assert any(value < -170 for value in longitudes)


@pytest.mark.parametrize("geometry_type", ALL_TYPES)
@pytest.mark.parametrize("name", sorted(MUTATIONS))
@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_polygon_rings_stay_closed_under_every_mutation(geometry_type, name, seed):
    """A mutation must introduce only its own pathology, not unclosed rings."""
    family = {"point": "point", "linestring": "line", "polygon": "polygon"}[geometry_type]
    if name not in applicable(family):
        pytest.skip(f"{name} does not apply to {geometry_type}")
    geometry = generate(geometry=geometry_type, mutations=[name], seed=seed)
    assert rings_are_closed(geometry)


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_mutations_do_not_modify_their_input(name):
    import random as _random

    rng = _random.Random(0)
    family = "polygon"
    if family not in MUTATIONS[name].families:
        pytest.skip(f"{name} does not apply to polygons")
    base = build("polygon", rng, vertices=8)
    snapshot = [list(position) for position in positions(base)]
    apply(base, name, rng)
    assert [list(position) for position in positions(base)] == snapshot


def test_inapplicable_mutation_raises_clearly():
    with pytest.raises(UnsupportedMutationError, match="does not apply"):
        generate(geometry="point", mutations=["self_intersection"], seed=1)


def test_unknown_mutation_raises_clearly():
    with pytest.raises(UnsupportedMutationError, match="Unknown mutation"):
        generate(geometry="polygon", mutations=["not_a_real_mutation"], seed=1)


@pytest.mark.parametrize("seed", SEEDS)
def test_mutations_compose_without_cancelling(seed):
    """Composed mutations must each survive in the output."""
    geometry = generate(
        geometry="polygon",
        mutations=["self_intersection", "duplicate_vertices"],
        seed=seed,
    )
    assert geometry_is_self_intersecting(geometry)
    assert has_consecutive_duplicate(geometry)


def test_every_registered_mutation_declares_families_and_description():
    for mutation in MUTATIONS.values():
        assert mutation.families
        assert mutation.families <= {"point", "line", "polygon"}
        assert mutation.description


def _all_positions(geometry):
    from tests.predicates import all_positions

    return all_positions(geometry)
