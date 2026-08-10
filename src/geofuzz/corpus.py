"""Static corpus generation.

The corpus is a fixed, reproducible set of pathological files that can be used
as test fixtures without installing or calling geofuzz at all.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from geofuzz.generate import generate_case
from geofuzz.geometry import GEOMETRY_TYPES
from geofuzz.mutations import MUTATIONS, applicable

_FAMILY_OF = {"point": "point", "linestring": "line", "polygon": "polygon"}
_PAIRS_PER_TYPE = 4


def corpus_cases(seed: int = 0) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield ``(filename, case)`` for the full corpus, deterministically."""
    counter = seed
    for geometry_type in GEOMETRY_TYPES:
        names = applicable(_FAMILY_OF[geometry_type])

        yield (
            _named(geometry_type, ["clean"], counter),
            generate_case(geometry=geometry_type, mutations=[], seed=counter),
        )
        counter += 1

        for name in names:
            yield (
                _named(geometry_type, [name], counter),
                generate_case(geometry=geometry_type, mutations=[name], seed=counter),
            )
            counter += 1

        for first, second in _pairs(names)[:_PAIRS_PER_TYPE]:
            yield (
                _named(geometry_type, [first, second], counter),
                generate_case(geometry=geometry_type, mutations=[first, second], seed=counter),
            )
            counter += 1


def write_corpus(directory: Path, seed: int = 0) -> list[Path]:
    """Write every corpus case as a GeoJSON Feature carrying its provenance."""
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    for filename, case in corpus_cases(seed=seed):
        path = directory / filename
        path.write_text(json.dumps(as_feature(case), indent=2) + "\n", encoding="utf-8")
        written.append(path)
    return written


def as_feature(case: dict[str, Any]) -> dict[str, Any]:
    """Wrap a case as a GeoJSON Feature with provenance in ``properties``."""
    return {
        "type": "Feature",
        "geometry": case["geometry"],
        "properties": {"geofuzz": case["provenance"]},
    }


def _pairs(names: list[str]) -> list[tuple[str, str]]:
    return [(first, second) for index, first in enumerate(names) for second in names[index + 1 :]]


def _named(geometry_type: str, parts: list[str], counter: int) -> str:
    return f"{geometry_type}__{'+'.join(parts)}__{counter:04d}.geojson"


def mutation_catalog() -> list[dict[str, Any]]:
    """Return the registry as plain data, for docs and the CLI."""
    return [
        {
            "name": mutation.name,
            "families": sorted(mutation.families),
            "description": mutation.description,
        }
        for mutation in MUTATIONS.values()
    ]
