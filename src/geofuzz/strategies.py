"""Hypothesis strategies.

Requires the ``hypothesis`` extra: ``pip install geofuzz[hypothesis]``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from geofuzz.generate import generate

try:
    from hypothesis import strategies as st
except ImportError as exc:  # pragma: no cover - import guard
    raise ImportError(
        "geofuzz.strategies requires hypothesis. Install with: pip install 'geofuzz[hypothesis]'"
    ) from exc

__all__ = [
    "pathological_geometries",
    "pathological_linestrings",
    "pathological_points",
    "pathological_polygons",
]

_MAX_SEED = 2**32 - 1


def pathological_geometries(
    geometry: str = "polygon",
    mutations: Sequence[str] | None = None,
    vertices: int = 8,
    mutation_count: int | None = None,
) -> st.SearchStrategy[dict[str, Any]]:
    """Strategy over pathological GeoJSON geometries.

    Hypothesis shrinks the seed, so minimized examples stay reproducible via
    ``geofuzz.generate(seed=...)``. Geometry-level shrinking arrives in v0.2.
    """
    if mutations is None and mutation_count is None:
        mutation_count = 1
    return st.integers(min_value=0, max_value=_MAX_SEED).map(
        lambda seed: generate(
            geometry=geometry,
            mutations=mutations,
            seed=seed,
            vertices=vertices,
            mutation_count=mutation_count,
        )
    )


def pathological_points(**kwargs: Any) -> st.SearchStrategy[dict[str, Any]]:
    """Strategy over pathological Points."""
    return pathological_geometries("point", **kwargs)


def pathological_linestrings(**kwargs: Any) -> st.SearchStrategy[dict[str, Any]]:
    """Strategy over pathological LineStrings."""
    return pathological_geometries("linestring", **kwargs)


def pathological_polygons(**kwargs: Any) -> st.SearchStrategy[dict[str, Any]]:
    """Strategy over pathological Polygons."""
    return pathological_geometries("polygon", **kwargs)
