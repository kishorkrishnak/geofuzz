"""Pathological mutations.

Every mutation is ``(geometry, rng) -> geometry``. Mutations never modify their
input, declare which geometry families they support, and are designed to be
orthogonal so they can be composed without cancelling each other out.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable
from dataclasses import dataclass

from geofuzz.geometry import Geometry, family, map_positions, positions

_EXTREME = 1.7976931348623157e308


class UnsupportedMutationError(ValueError):
    """Raised when a mutation cannot apply to the given geometry."""


@dataclass(frozen=True)
class Mutation:
    """A named pathology plus the families it applies to."""

    name: str
    families: frozenset[str]
    description: str
    apply: Callable[[Geometry, random.Random], Geometry]


MUTATIONS: dict[str, Mutation] = {}


def _register(name: str, families: tuple[str, ...], description: str):
    def decorator(function: Callable[[Geometry, random.Random], Geometry]):
        MUTATIONS[name] = Mutation(
            name=name, families=frozenset(families), description=description, apply=function
        )
        return function

    return decorator


def get(name: str) -> Mutation:
    """Look up a mutation by name."""
    try:
        return MUTATIONS[name]
    except KeyError as exc:
        raise UnsupportedMutationError(
            f"Unknown mutation {name!r}. Available: {', '.join(sorted(MUTATIONS))}."
        ) from exc


def applicable(geometry_family: str) -> list[str]:
    """Return mutation names that apply to a geometry family, in registry order."""
    return [name for name, mutation in MUTATIONS.items() if geometry_family in mutation.families]


def apply(geometry: Geometry, name: str, rng: random.Random) -> Geometry:
    """Apply one mutation, failing loudly if it does not fit the geometry."""
    mutation = get(name)
    geometry_family = family(geometry)
    if geometry_family not in mutation.families:
        raise UnsupportedMutationError(
            f"Mutation {name!r} does not apply to {geometry['type']} "
            f"(supports: {', '.join(sorted(mutation.families))})."
        )
    return mutation.apply(geometry, rng)


@_register(
    "self_intersection",
    ("line", "polygon"),
    "Ring or path that crosses itself, producing an invalid or non-simple geometry.",
)
def _self_intersection(geometry: Geometry, rng: random.Random) -> Geometry:
    """Swap adjacent ring vertices (polygon) or append a crossing spur (line)."""
    if family(geometry) == "polygon":
        ring = geometry["coordinates"][0][:-1]
        if len(ring) < 4:
            raise UnsupportedMutationError("self_intersection needs a ring of at least 4 vertices.")
        index = rng.randrange(len(ring))
        following = (index + 1) % len(ring)
        swapped = list(ring)
        swapped[index], swapped[following] = swapped[following], swapped[index]
        rings = [[*swapped, list(swapped[0])], *[list(r) for r in geometry["coordinates"][1:]]]
        return {"type": "Polygon", "coordinates": rings}

    coordinates = geometry["coordinates"]
    if len(coordinates) < 2:
        raise UnsupportedMutationError("self_intersection needs at least 2 vertices.")
    start, end = coordinates[0], coordinates[1]
    midpoint = [(start[0] + end[0]) / 2, (start[1] + end[1]) / 2]
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy) or 1.0
    offset = [-dy / length * 0.05, dx / length * 0.05]
    crossing = [
        [midpoint[0] + offset[0], midpoint[1] + offset[1]],
        [midpoint[0] - offset[0], midpoint[1] - offset[1]],
    ]
    return {"type": "LineString", "coordinates": [*[list(p) for p in coordinates], *crossing]}


@_register(
    "duplicate_vertices",
    ("line", "polygon"),
    "Repeated consecutive positions, which break naive dedup and ring-closure logic.",
)
def _duplicate_vertices(geometry: Geometry, rng: random.Random) -> Geometry:
    """Repeat a random position in place, once per ring or path."""
    if family(geometry) == "polygon":
        rings = []
        for ring in geometry["coordinates"]:
            body = ring[:-1]
            index = rng.randrange(len(body))
            expanded = [*body[: index + 1], list(body[index]), *body[index + 1 :]]
            rings.append([*[list(p) for p in expanded], list(expanded[0])])
        return {"type": "Polygon", "coordinates": rings}

    coordinates = geometry["coordinates"]
    index = rng.randrange(len(coordinates))
    expanded = [*coordinates[: index + 1], list(coordinates[index]), *coordinates[index + 1 :]]
    return {"type": "LineString", "coordinates": [list(p) for p in expanded]}


@_register(
    "extreme_coordinates",
    ("point", "line", "polygon"),
    "Coordinates at the float64 limits, which overflow projection and bounds maths.",
)
def _extreme_coordinates(geometry: Geometry, rng: random.Random) -> Geometry:
    """Replace a random subset of ordinates with values near the float64 maximum."""
    targets = _target_indices(geometry, rng)
    signs = {index: rng.choice((-1.0, 1.0)) for index in targets}
    axes = {index: rng.randrange(2) for index in targets}

    def transform(index: int, position: list[float]) -> list[float]:
        if index not in targets:
            return position
        updated = list(position)
        updated[axes[index]] = signs[index] * _EXTREME
        return updated

    return map_positions(geometry, transform)


@_register(
    "nan_coordinates",
    ("point", "line", "polygon"),
    "NaN and Infinity ordinates, the classic source of silent downstream corruption.",
)
def _nan_coordinates(geometry: Geometry, rng: random.Random) -> Geometry:
    """Replace a random subset of ordinates with NaN or +/-Infinity."""
    targets = _target_indices(geometry, rng)
    values = {index: rng.choice((math.nan, math.inf, -math.inf)) for index in targets}
    axes = {index: rng.randrange(2) for index in targets}

    def transform(index: int, position: list[float]) -> list[float]:
        if index not in targets:
            return position
        updated = list(position)
        updated[axes[index]] = values[index]
        return updated

    return map_positions(geometry, transform)


@_register(
    "antimeridian",
    ("line", "polygon"),
    "Geometry straddling the +/-180 meridian, where naive bbox maths spans the globe.",
)
def _antimeridian(geometry: Geometry, rng: random.Random) -> Geometry:
    """Translate longitudes so the geometry sits astride the dateline."""
    longitudes = [position[0] for position in positions(geometry) if math.isfinite(position[0])]
    if not longitudes:
        return geometry
    shift = 180.0 - (sum(longitudes) / len(longitudes))
    return map_positions(
        geometry,
        lambda _index, position: [_wrap_longitude(position[0] + shift), *position[1:]],
    )


def _wrap_longitude(longitude: float) -> float:
    if not math.isfinite(longitude):
        return longitude
    return round(((longitude + 180.0) % 360.0) - 180.0, 9)


def _target_indices(geometry: Geometry, rng: random.Random) -> set[int]:
    """Pick 1..n/3 positions to corrupt, always at least one."""
    total = len(positions(geometry))
    count = max(1, rng.randrange(1, max(2, total // 3 + 1)))
    return set(rng.sample(range(total), min(count, total)))
