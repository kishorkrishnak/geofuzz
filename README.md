# geofuzz

[![CI](https://github.com/kishorkrishnak/geofuzz/actions/workflows/ci.yml/badge.svg)](https://github.com/kishorkrishnak/geofuzz/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Status: alpha](https://img.shields.io/badge/status-alpha-orange)](CHANGELOG.md)

Generates pathological vector geometry for testing GIS pipelines — self-intersecting
rings, duplicate vertices, coordinates at the float64 limit, `NaN` and `Infinity`
ordinates, geometry crossing the antimeridian — deterministically, so failures reproduce
from a seed.

You throw it at your own code and assert whatever your code should guarantee. geofuzz
produces the inputs; the checks are yours.

```python
from hypothesis import given
from geofuzz.strategies import pathological_polygons


@given(pathological_polygons())
def test_normalize_keeps_the_geometry(geom):
    result = normalize(geom)
    assert result is None or result["type"] in {"Polygon", "MultiPolygon"}
```

## Install

Not yet published to PyPI. Install from source:

```bash
pip install 'geofuzz @ git+https://github.com/kishorkrishnak/geofuzz'
pip install 'geofuzz[hypothesis] @ git+https://github.com/kishorkrishnak/geofuzz'
```

Requires Python 3.10+. The core package depends only on `click` — no GDAL, GEOS, or
shapely. Geometries are plain GeoJSON dicts, which is what allows the library to emit
values a geometry engine would refuse to construct.

## Usage

### Corpus files

Pre-generated files are in [`corpus/`](corpus/) and usable as fixtures without installing
the package.

```python
for path in pathlib.Path("corpus").glob("*.geojson"):
    feature = json.loads(path.read_text(), parse_constant=float)
    my_pipeline(feature["geometry"])
```

Each is a GeoJSON Feature whose `properties.geofuzz` records what produced it:

```json
"properties": {
  "geofuzz": {
    "seed": 12,
    "geometry": "polygon",
    "vertices": 8,
    "mutations": ["self_intersection", "antimeridian"]
  }
}
```

### Hypothesis strategies

Requires the `hypothesis` extra.

```python
from hypothesis import given
from geofuzz.strategies import pathological_polygons


@given(pathological_polygons())
def test_normalize_returns_a_polygon_or_nothing(geom):
    result = normalize(geom)
    assert result is None or result["type"] in {"Polygon", "MultiPolygon"}
```

Also `pathological_points`, `pathological_linestrings`, and `pathological_geometries()`.

### Python API

```python
from geofuzz import generate, generate_case

geom = generate(geometry="polygon", mutations=["self_intersection"], seed=42)

case = generate_case(geometry="linestring", mutation_count=2)
case["provenance"]["seed"]  # 3170924418
case["provenance"]["mutations"]  # ["duplicate_vertices", "antimeridian"]
```

| Argument | Default | Notes |
|---|---|---|
| `geometry` | `"polygon"` | `"point"`, `"linestring"`, or `"polygon"` |
| `mutations` | `None` | Explicit list, applied in order |
| `mutation_count` | `None` | Select N at random; mutually exclusive with `mutations` |
| `seed` | `None` | Random if omitted; the value used is recorded in provenance |
| `vertices` | `8` | Base vertex count before mutation |

### CLI

```bash
geofuzz generate --geometry polygon --mutations self_intersection,antimeridian --seed 42
geofuzz corpus --out corpus/
geofuzz list-mutations
```

## Mutations

| Mutation | Applies to | Description |
|---|---|---|
| `self_intersection` | line, polygon | Ring or path that crosses itself |
| `duplicate_vertices` | line, polygon | Repeated consecutive positions |
| `extreme_coordinates` | point, line, polygon | Ordinates at the float64 limit |
| `nan_coordinates` | point, line, polygon | `NaN` and `±Infinity` ordinates |
| `antimeridian` | line, polygon | Geometry straddling ±180 |

Mutations apply in the order given and compose. Requesting one that does not apply to a
geometry type raises `UnsupportedMutationError` rather than silently doing nothing. Each
introduces only its own pathology, does not modify its input, and draws all randomness
from a passed-in `random.Random`. These properties are covered by the test suite.

### JSON encoding

`nan_coordinates` emits `NaN` and `Infinity` tokens, which Python's `json` accepts and
strict RFC 8259 does not. Parse corpus files with `json.loads(text, parse_constant=float)`.

## Dateline-aware extent

One helper ships alongside the generator, because getting it wrong is the single most
common way a pipeline silently corrupts geospatial data:

```python
from geofuzz import longitude_extent

longitude_extent([179.9, -179.95])  # (179.9, -179.95, True)
longitude_extent([-134.0, -133.4])  # (-134.0, -133.4, False)
```

A plain `min`/`max` reports a dateline-crossing geometry as spanning the globe — a 0.16°
polygon near Kamchatka comes out 359.84° wide. When a crossing is detected the extent is
returned in GeoJSON (RFC 7946 §5.2) form, where `west > east`.

## Geometry types

`Point`, `LineString`, and `Polygon`. Multi-part types and `GeometryCollection` are on the
roadmap.

Base geometries are valid by construction: polygon rings are convex (vertices at evenly
spaced, jittered angles) and linestrings are strictly x-monotone, which cannot
self-intersect. An invalid output is therefore attributable to the mutation rather than to
the base geometry.

## Determinism

The same seed and configuration produce the same output.

A single seeded `random.Random` is threaded through base construction and each mutation in
turn. Mutation *selection* uses a separate derived stream, so a case generated with
`mutation_count=2` reproduces exactly when re-run with the recorded mutation list. The
global `random` module state is not modified.

CI regenerates the committed corpus on every run and fails if the output differs.

## Prior art

[GDAL's autotest suite](https://github.com/OSGeo/gdal/tree/master/autotest) contains a
large body of hostile geospatial test data, organised by driver rather than by pathology,
and structured as a regression suite for GDAL rather than a reusable library.
[OSS-Fuzz](https://github.com/google/oss-fuzz) continuously fuzzes GDAL and GEOS at the
C/C++ level, which is why geofuzz does not attempt byte-level format fuzzing.

geofuzz differs in generating rather than storing cases, composing several pathologies
into one geometry, and indexing by pathology rather than by format.

## Development

```bash
git clone https://github.com/kishorkrishnak/geofuzz
cd geofuzz
pip install -e '.[dev]'

ruff check .
ruff format .
pytest
```

Tests verify that each mutation produces the property it declares, using geometry
predicates in `tests/predicates.py` rather than shapely — so the tests do not depend on
the geometry stack the library is used to test.

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Roadmap

**Next — GeoParquet output.** An optional `geofuzz[parquet]` extra writing WKB via
pyarrow, plus a CRS field in the case model. GeoJSON cannot express a CRS (RFC 7946
removed it) or M coordinates, which puts the largest category of real pipeline failures —
missing, wrong, or out-of-domain CRS — out of reach. GeoParquet carries both.

**After that — more mutations.** Degenerate rings, zero-length lines, empty geometry,
excessive precision, high vertex counts, nested collections, Z and M dimensions, mixed
dimensionality. Multi-part geometries and `GeometryCollection`.

**Speculative.** Ready-made assertions for common pipeline shapes, and a runner that
applies them across the corpus in one call. An earlier version of this existed and was
removed: the assertions only fit functions returning geometry or bounds, which is a
minority of a real pipeline, and everything else needed the user to supply the check
anyway. Worth revisiting only with a clearer idea of what it should cover.

Out of scope: raster fuzzing, PostGIS integration, network and API fuzzing, distributed
execution, a web UI, and formats requiring GDAL (GeoPackage, Shapefile, FileGDB).

## License

MIT. See [LICENSE](LICENSE).
