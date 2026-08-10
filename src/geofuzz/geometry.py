"""Base geometry construction and coordinate plumbing.

Geometries are plain GeoJSON dicts, never GEOS objects: the whole point is to
build things a geometry engine would refuse to construct.
"""

from __future__ import annotations

import math
import random
from collections.abc import Iterable
from typing import Any

GEOMETRY_TYPES: tuple[str, ...] = ("point", "linestring", "polygon")

_GEOJSON_TYPE = {"point": "Point", "linestring": "LineString", "polygon": "Polygon"}
_FAMILY = {"Point": "point", "LineString": "line", "Polygon": "polygon"}

Position = list[float]
Geometry = dict[str, Any]


class UnsupportedGeometryError(ValueError):
    """Raised for a geometry type geofuzz does not model yet."""


def family(geometry: Geometry) -> str:
    """Return the routing family (``point`` / ``line`` / ``polygon``)."""
    try:
        return _FAMILY[geometry["type"]]
    except KeyError as exc:
        raise UnsupportedGeometryError(
            f"Unsupported geometry type: {geometry.get('type')!r}"
        ) from exc


def build(geometry_type: str, rng: random.Random, vertices: int = 8) -> Geometry:
    """Build a clean, valid base geometry of the requested type."""
    normalized = str(geometry_type or "").strip().lower()
    if normalized not in GEOMETRY_TYPES:
        raise UnsupportedGeometryError(
            f"Unknown geometry type {geometry_type!r}. Supported: {', '.join(GEOMETRY_TYPES)}."
        )
    builders = {"point": _build_point, "linestring": _build_linestring, "polygon": _build_polygon}
    builder = builders[normalized]
    return builder(rng, vertices)


def _origin(rng: random.Random) -> tuple[float, float]:
    return rng.uniform(-170.0, 170.0), rng.uniform(-80.0, 80.0)


def _build_point(rng: random.Random, vertices: int) -> Geometry:
    lon, lat = _origin(rng)
    return {"type": "Point", "coordinates": [_r(lon), _r(lat)]}


def _build_linestring(rng: random.Random, vertices: int) -> Geometry:
    """Build a strictly x-monotone path.

    Monotonicity is deliberate: an x-monotone polyline can never self-intersect,
    so the clean base stays clean and ``self_intersection`` stays meaningful.
    """
    count = max(2, int(vertices))
    lon, lat = _origin(rng)
    coordinates = [[_r(lon), _r(lat)]]
    for _ in range(count - 1):
        previous = coordinates[-1]
        coordinates.append(
            [_r(previous[0] + rng.uniform(0.01, 0.1)), _r(previous[1] + rng.uniform(-0.1, 0.1))]
        )
    return {"type": "LineString", "coordinates": coordinates}


def _build_polygon(rng: random.Random, vertices: int) -> Geometry:
    """Build a convex ring from evenly spaced, jittered angles.

    Convexity is deliberate: it is what makes ``self_intersection`` reliable.
    """
    count = max(4, int(vertices))
    lon, lat = _origin(rng)
    radius = rng.uniform(0.05, 0.5)
    step = 2 * math.pi / count
    angles = [index * step + rng.uniform(0.0, step * 0.6) for index in range(count)]
    ring = [
        [_r(lon + radius * math.cos(angle)), _r(lat + radius * math.sin(angle))] for angle in angles
    ]
    return {"type": "Polygon", "coordinates": [[*ring, list(ring[0])]]}


def _r(value: float) -> float:
    return round(value, 9)


def longitude_extent(longitudes: Iterable[float]) -> tuple[float, float, bool] | None:
    """Return ``(west, east, crosses_antimeridian)`` for WGS84 longitudes.

    A plain ``min``/``max`` reports a dateline-crossing geometry as spanning the globe: a
    0.16-degree polygon near Kamchatka comes out 359.84 degrees wide. When a crossing is
    detected the extent is returned in GeoJSON (RFC 7946 section 5.2) form, where
    ``west > east``.

    The rule is a heuristic, necessarily: two points at 170 and -170 could be a
    20-degree strip across the dateline or a 340-degree span the long way round. Real
    data is almost always the former. A crossing is reported only when the naive extent
    spans more than half the globe and the wrapped extent spans less, which keeps both
    ordinary and genuinely global datasets out of the crossing branch.
    """
    values = [float(value) for value in longitudes if math.isfinite(value)]
    if not values:
        return None

    naive_west, naive_east = min(values), max(values)
    if (naive_east - naive_west) <= 180.0:
        # A genuine crossing always leaves a naive extent wider than half the globe,
        # so anything narrower is ordinary data. Testing this first also avoids a
        # float-rounding trap, where the modulo below can make a 0.4-degree extent
        # come out an epsilon narrower than the original and read as a crossing.
        return naive_west, naive_east, False

    shifted = [value % 360.0 for value in values]
    shifted_west, shifted_east = min(shifted), max(shifted)
    if (shifted_east - shifted_west) >= 180.0:
        return naive_west, naive_east, False
    return (
        _r(((shifted_west + 180.0) % 360.0) - 180.0),
        _r(((shifted_east + 180.0) % 360.0) - 180.0),
        True,
    )


def positions(geometry: Geometry) -> list[Position]:
    """Return every mutable position; polygon ring-closing points are excluded."""
    geometry_type = geometry["type"]
    if geometry_type == "Point":
        return [list(geometry["coordinates"])]
    if geometry_type == "LineString":
        return [list(position) for position in geometry["coordinates"]]
    if geometry_type == "Polygon":
        return [list(position) for ring in geometry["coordinates"] for position in ring[:-1]]
    raise UnsupportedGeometryError(f"Unsupported geometry type: {geometry_type!r}")


def replace_positions(geometry: Geometry, new_positions: Iterable[Position]) -> Geometry:
    """Rebuild a geometry from positions in document order, re-closing rings."""
    remaining = iter([list(position) for position in new_positions])
    geometry_type = geometry["type"]

    if geometry_type == "Point":
        return {"type": "Point", "coordinates": next(remaining)}
    if geometry_type == "LineString":
        return {
            "type": "LineString",
            "coordinates": [next(remaining) for _ in geometry["coordinates"]],
        }
    if geometry_type == "Polygon":
        rings = []
        for ring in geometry["coordinates"]:
            rebuilt = [next(remaining) for _ in ring[:-1]]
            rings.append([*rebuilt, list(rebuilt[0])])
        return {"type": "Polygon", "coordinates": rings}
    raise UnsupportedGeometryError(f"Unsupported geometry type: {geometry_type!r}")


def map_positions(geometry: Geometry, transform) -> Geometry:
    """Return a new geometry with ``transform(index, position)`` applied to each position."""
    return replace_positions(
        geometry,
        [transform(index, position) for index, position in enumerate(positions(geometry))],
    )
