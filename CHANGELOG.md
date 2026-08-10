# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Planned: an optional GeoParquet emitter writing WKB via pyarrow, plus a CRS field in the
case model. GeoJSON can express neither a CRS (RFC 7946 removed it) nor M coordinates,
which puts CRS-related failures — the largest category in practice — out of reach.

## [0.1.0] - 2026-08-10

Initial release.

### Added

- Deterministic generators for `Point`, `LineString`, and `Polygon`. Polygon rings are
  convex by construction and linestrings x-monotone, so an invalid output is attributable
  to the mutation rather than the base geometry.
- Five orthogonal mutations: `self_intersection`, `duplicate_vertices`,
  `extreme_coordinates`, `nan_coordinates`, `antimeridian`.
- Seeded generation with replayable provenance. Mutation selection draws from a separate
  RNG stream so a randomly mutated case replays exactly from its recorded mutation list.
  The global `random` state is never touched.
- Static corpus of 24 GeoJSON files, each carrying its own provenance.
- Hypothesis strategies: `pathological_geometries`, `pathological_points`,
  `pathological_linestrings`, `pathological_polygons`.
- `longitude_extent()`, a dateline-aware longitude extent helper returning RFC 7946
  §5.2 form (`west > east`) when a crossing is detected.
- CLI: `generate`, `corpus`, `list-mutations`.
- PEP 561 `py.typed` marker.

### Notes

- The core package has no GEOS, GDAL, or shapely dependency. Geometries are plain GeoJSON
  dicts so the library can emit values a geometry engine would refuse to construct.
- `nan_coordinates` emits `NaN` and `Infinity` tokens, which Python's `json` accepts but
  strict RFC 8259 does not. Parse corpus files with `parse_constant=float`.

[Unreleased]: https://github.com/kishorkrishnak/geofuzz/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/kishorkrishnak/geofuzz/releases/tag/v0.1.0
