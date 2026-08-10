"""The corpus must be complete, reproducible, and self-describing."""

from __future__ import annotations

import json

from geofuzz import corpus_cases, generate, mutation_catalog, write_corpus
from geofuzz.geometry import GEOMETRY_TYPES
from geofuzz.mutations import MUTATIONS


def test_corpus_is_reproducible():
    first = [(name, case["geometry"]) for name, case in corpus_cases(seed=0)]
    second = [(name, case["geometry"]) for name, case in corpus_cases(seed=0)]
    assert json.dumps(first) == json.dumps(second)


def test_corpus_covers_every_geometry_type_and_mutation():
    names = [name for name, _ in corpus_cases(seed=0)]
    for geometry_type in GEOMETRY_TYPES:
        assert any(name.startswith(f"{geometry_type}__") for name in names)
    for mutation in MUTATIONS:
        assert any(mutation in name for name in names)


def test_corpus_filenames_are_unique():
    names = [name for name, _ in corpus_cases(seed=0)]
    assert len(names) == len(set(names))


def test_written_corpus_files_are_features_with_provenance(tmp_path):
    written = write_corpus(tmp_path, seed=0)
    assert written
    for path in written:
        document = json.loads(path.read_text(), parse_constant=float)
        assert document["type"] == "Feature"
        assert document["geometry"]["type"] in {"Point", "LineString", "Polygon"}
        provenance = document["properties"]["geofuzz"]
        assert set(provenance) == {"seed", "geometry", "vertices", "mutations"}


def test_corpus_case_can_be_replayed_from_its_provenance(tmp_path):
    written = write_corpus(tmp_path, seed=0)
    for path in written:
        document = json.loads(path.read_text(), parse_constant=float)
        provenance = document["properties"]["geofuzz"]
        replayed = generate(
            geometry=provenance["geometry"],
            mutations=provenance["mutations"],
            seed=provenance["seed"],
            vertices=provenance["vertices"],
        )
        assert json.dumps(replayed) == json.dumps(document["geometry"])


def test_mutation_catalog_matches_registry():
    catalog = mutation_catalog()
    assert {entry["name"] for entry in catalog} == set(MUTATIONS)
