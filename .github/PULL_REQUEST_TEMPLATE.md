**What this changes**

**Checklist**

- [ ] `ruff check .` passes
- [ ] `ruff format .` applied
- [ ] `pytest` passes
- [ ] New mutations follow the four design rules (deterministic, pure, honest, loud)
- [ ] New mutations have property tests verified without shapely
- [ ] Corpus regenerated if the mutation registry changed (`geofuzz corpus --out corpus`)
- [ ] README and CHANGELOG updated
