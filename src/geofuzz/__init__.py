"""geofuzz - pathological geometry generation for testing GIS pipelines."""

from geofuzz.corpus import as_feature, corpus_cases, mutation_catalog, write_corpus
from geofuzz.generate import generate, generate_case, new_seed
from geofuzz.geometry import (
    GEOMETRY_TYPES,
    UnsupportedGeometryError,
    longitude_extent,
    positions,
)
from geofuzz.mutations import MUTATIONS, UnsupportedMutationError, applicable

__version__ = "0.1.0"

__all__ = [
    "GEOMETRY_TYPES",
    "MUTATIONS",
    "UnsupportedGeometryError",
    "UnsupportedMutationError",
    "__version__",
    "applicable",
    "as_feature",
    "corpus_cases",
    "generate",
    "generate_case",
    "longitude_extent",
    "mutation_catalog",
    "new_seed",
    "positions",
    "write_corpus",
]
