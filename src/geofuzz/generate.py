"""Deterministic case generation.

Same seed + same configuration always produces the same geometry. A single
seeded RNG is threaded through base construction and every mutation in order.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from typing import Any

from geofuzz import mutations as mutation_registry
from geofuzz.geometry import Geometry, build, family

__all__ = ["generate", "generate_case", "new_seed"]

_MAX_SEED = 2**32 - 1


def new_seed() -> int:
    """Return a fresh random seed drawn from system entropy."""
    return random.Random().getrandbits(32)


def generate(
    *,
    geometry: str = "polygon",
    mutations: Sequence[str] | None = None,
    seed: int | None = None,
    vertices: int = 8,
    mutation_count: int | None = None,
) -> Geometry:
    """Generate one pathological geometry as a GeoJSON dict."""
    return generate_case(
        geometry=geometry,
        mutations=mutations,
        seed=seed,
        vertices=vertices,
        mutation_count=mutation_count,
    )["geometry"]


def generate_case(
    *,
    geometry: str = "polygon",
    mutations: Sequence[str] | None = None,
    seed: int | None = None,
    vertices: int = 8,
    mutation_count: int | None = None,
) -> dict[str, Any]:
    """Generate a geometry plus the provenance needed to reproduce it exactly."""
    if mutations is not None and mutation_count is not None:
        raise ValueError("Pass either `mutations` or `mutation_count`, not both.")

    resolved_seed = new_seed() if seed is None else int(seed) & _MAX_SEED
    rng = random.Random(resolved_seed)

    base = build(geometry, rng, vertices=vertices)
    selected = _resolve_mutations(base, mutations, mutation_count, _selection_rng(resolved_seed))

    mutated = base
    for name in selected:
        mutated = mutation_registry.apply(mutated, name, rng)

    return {
        "geometry": mutated,
        "provenance": {
            "seed": resolved_seed,
            "geometry": str(geometry).strip().lower(),
            "vertices": int(vertices),
            "mutations": list(selected),
        },
    }


def _selection_rng(seed: int) -> random.Random:
    """Separate stream for choosing mutations.

    Selection must not consume from the main stream, otherwise replaying a case
    from its recorded mutation list would diverge from the original.
    """
    return random.Random(seed ^ 0x5EED_5EED)


def _resolve_mutations(
    base: Geometry,
    mutations: Sequence[str] | None,
    mutation_count: int | None,
    rng: random.Random,
) -> list[str]:
    if mutations is not None:
        return [str(name).strip() for name in mutations if str(name).strip()]
    if mutation_count is None:
        return []

    available = mutation_registry.applicable(family(base))
    if not available:
        return []
    count = max(0, min(int(mutation_count), len(available)))
    return sorted(rng.sample(available, count), key=available.index)
