"""Same seed + same configuration must produce the same case, always."""

from __future__ import annotations

import json
import random

import pytest

from geofuzz import generate, generate_case
from geofuzz.geometry import GEOMETRY_TYPES

ALL_MUTATION_SETS = {
    "point": ["extreme_coordinates", "nan_coordinates"],
    "linestring": ["self_intersection", "duplicate_vertices", "antimeridian"],
    "polygon": ["self_intersection", "duplicate_vertices", "antimeridian"],
}


@pytest.mark.parametrize("geometry_type", GEOMETRY_TYPES)
def test_same_seed_produces_identical_geometry(geometry_type):
    mutations = ALL_MUTATION_SETS[geometry_type]
    first = generate(geometry=geometry_type, mutations=mutations, seed=817231)
    second = generate(geometry=geometry_type, mutations=mutations, seed=817231)
    assert json.dumps(first) == json.dumps(second)


@pytest.mark.parametrize("geometry_type", GEOMETRY_TYPES)
def test_different_seeds_produce_different_geometry(geometry_type):
    first = generate(geometry=geometry_type, seed=1)
    second = generate(geometry=geometry_type, seed=2)
    assert json.dumps(first) != json.dumps(second)


def test_generation_does_not_touch_global_random_state():
    """A caller's own random stream must be unaffected by generation."""
    random.seed(99)
    expected = [random.random() for _ in range(5)]

    random.seed(99)
    before = random.random()
    generate(geometry="polygon", mutations=["self_intersection"], seed=5)
    after = [before] + [random.random() for _ in range(4)]

    assert after == expected


def test_omitted_seed_is_reported_and_replayable():
    case = generate_case(geometry="polygon", mutation_count=2)
    seed = case["provenance"]["seed"]
    replayed = generate_case(
        geometry="polygon", mutations=case["provenance"]["mutations"], seed=seed
    )
    assert replayed["geometry"] == case["geometry"]


def test_provenance_records_applied_mutations():
    case = generate_case(
        geometry="polygon", mutations=["duplicate_vertices", "antimeridian"], seed=7
    )
    assert case["provenance"] == {
        "seed": 7,
        "geometry": "polygon",
        "vertices": 8,
        "mutations": ["duplicate_vertices", "antimeridian"],
    }


def test_random_mutation_selection_is_seed_stable():
    first = generate_case(geometry="polygon", mutation_count=3, seed=4242)
    second = generate_case(geometry="polygon", mutation_count=3, seed=4242)
    assert first["provenance"]["mutations"] == second["provenance"]["mutations"]
    assert len(first["provenance"]["mutations"]) == 3


def test_mutations_and_mutation_count_are_mutually_exclusive():
    with pytest.raises(ValueError):
        generate_case(geometry="polygon", mutations=["antimeridian"], mutation_count=1)
