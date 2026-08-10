"""Independent geometry predicates for tests.

Deliberately hand-written rather than delegating to shapely: the tests must
verify that a mutation produced the property it claims, without trusting the
same geometry stack the tool is meant to stress.
"""

from __future__ import annotations

import itertools
import math


def _orientation(a, b, c) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _sign(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def segments_properly_cross(p1, p2, p3, p4) -> bool:
    """True when two segments cross at an interior point of both."""
    d1, d2 = _sign(_orientation(p3, p4, p1)), _sign(_orientation(p3, p4, p2))
    d3, d4 = _sign(_orientation(p1, p2, p3)), _sign(_orientation(p1, p2, p4))
    return d1 * d2 < 0 and d3 * d4 < 0


def is_self_intersecting(path: list[list[float]], closed: bool) -> bool:
    """True when any two non-adjacent segments of the path properly cross."""
    points = path[:-1] if closed and path[0] == path[-1] else path
    count = len(points)
    segments = [
        (points[index], points[(index + 1) % count])
        for index in range(count if closed else count - 1)
    ]
    total = len(segments)
    for i in range(total):
        for j in range(i + 1, total):
            adjacent = j == i + 1 or (closed and i == 0 and j == total - 1)
            if adjacent:
                continue
            if segments_properly_cross(*segments[i], *segments[j]):
                return True
    return False


def geometry_is_self_intersecting(geometry: dict) -> bool:
    """Dispatch self-intersection checking on a GeoJSON geometry."""
    if geometry["type"] == "Polygon":
        return any(is_self_intersecting(ring, closed=True) for ring in geometry["coordinates"])
    if geometry["type"] == "LineString":
        return is_self_intersecting(geometry["coordinates"], closed=False)
    return False


def all_positions(geometry: dict) -> list[list[float]]:
    """Every position in a GeoJSON geometry, including ring-closing points."""
    if geometry["type"] == "Point":
        return [geometry["coordinates"]]
    if geometry["type"] == "LineString":
        return list(geometry["coordinates"])
    if geometry["type"] == "Polygon":
        return [position for ring in geometry["coordinates"] for position in ring]
    raise AssertionError(f"unexpected geometry type {geometry['type']!r}")


def ordinates(geometry: dict) -> list[float]:
    """Every ordinate value in a GeoJSON geometry."""
    return [value for position in all_positions(geometry) for value in position]


def has_consecutive_duplicate(geometry: dict) -> bool:
    """True when any path contains the same position twice in a row."""
    paths = geometry["coordinates"] if geometry["type"] == "Polygon" else [geometry["coordinates"]]
    for path in paths:
        for first, second in itertools.pairwise(path):
            if first == second:
                return True
    return False


def rings_are_closed(geometry: dict) -> bool:
    """True when every polygon ring starts and ends at the same position."""
    if geometry["type"] != "Polygon":
        return True
    return all(
        ring[0] == ring[-1] or _both_nan(ring[0], ring[-1]) for ring in geometry["coordinates"]
    )


def _is_nan(value) -> bool:
    return isinstance(value, float) and math.isnan(value)


def _both_nan(first, second) -> bool:
    return all(a == b or (_is_nan(a) and _is_nan(b)) for a, b in zip(first, second, strict=False))
