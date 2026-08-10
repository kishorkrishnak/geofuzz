# Contributing

Bug reports, new mutations, and reports of real-world pathology are welcome. See
[Reporting pathology](#reporting-pathology) if you have hit a geometry in production
that broke something.

## Setup

```bash
git clone https://github.com/kishorkrishnak/geofuzz
cd geofuzz
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
```

## Checks

Run all three before opening a pull request. CI runs the same commands.

```bash
ruff check .
ruff format .
pytest
```

Tests must pass on Python 3.10 through 3.13.

## Adding a mutation

A new mutation is a single function plus tests.

1. **Write it** in `src/geofuzz/mutations.py`, registered with `@_register`:

   ```python
   @_register(
       "degenerate_ring",
       ("polygon",),
       "Ring with fewer than three distinct positions.",
   )
   def _degenerate_ring(geometry: Geometry, rng: random.Random) -> Geometry:
       ring = geometry["coordinates"][0][:-1]
       collapsed = [list(ring[0]), list(ring[0])]
       return {"type": "Polygon", "coordinates": [[*collapsed, list(collapsed[0])]]}
   ```

2. **Follow the four design rules.** These are enforced by the test suite:

   - **Deterministic.** Draw all randomness from the passed `rng`. Never touch the
     global `random` module, and never use `Date`/time/`os.urandom` as an input.
   - **Pure.** Never modify the input geometry. Build and return a new one. The
     `map_positions` and `replace_positions` helpers in `geometry.py` do this for you.
   - **Honest.** Introduce your own pathology and no other. If your mutation leaves a
     polygon ring unclosed as a side effect, that is a bug — the test suite checks it.
   - **Loud.** Declare the geometry families you support. Applying a mutation to an
     unsupported family raises rather than silently doing nothing.

3. **Test the property, not the implementation.** Add a test to
   `tests/test_mutations.py` asserting the output actually has the pathology you claim,
   across many seeds:

   ```python
   @pytest.mark.parametrize("seed", SEEDS)
   def test_degenerate_ring_has_fewer_than_three_distinct_positions(seed):
       geometry = generate(geometry="polygon", mutations=["degenerate_ring"], seed=seed)
       ...
   ```

   Verify with a predicate in `tests/predicates.py` rather than with shapely, so the
   tests do not depend on the geometry stack the library is used to test.

4. **Regenerate the corpus**, since it is derived from the registry:

   ```bash
   geofuzz corpus --out corpus
   ```

   CI fails if the committed corpus does not match what the generator produces.

5. **Document it** in the README mutation table and in `CHANGELOG.md`.

## Reporting pathology

If you have real geometry that broke a real pipeline, open an issue with:

- what the input was (shape of the pathology, not necessarily the data itself);
- what the pipeline did wrong — crash, hang, or silent corruption;
- whether the failure was visible or silent.

If the data is sensitive, describe its shape and a synthetic equivalent can be built.

## Scope

The following are out of scope and unlikely to be merged: raster fuzzing, PostGIS
integration, network and API fuzzing, distributed execution, a web UI, and file formats
beyond GeoJSON.

Format-level fuzzing of GDAL and GEOS is covered by OSS-Fuzz. Adding format support
would require a GDAL dependency, which the core package does not have.

## Commits

Conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`.

## License

Contributions are accepted under the MIT License.
