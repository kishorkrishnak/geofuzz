---
name: New mutation
about: Propose a pathology geofuzz should be able to generate
title: ''
labels: mutation
---

**The pathology**

What does the geometry look like, and what makes it pathological?

**Geometry families**

Which of point / line / polygon does it apply to?

**Where you hit it**

Did this break something real? A crash, a hang, or silent corruption? Silent
corruption is the most valuable category.

**How to detect it**

How would a test verify a geometry actually has this property, without relying on
shapely or GEOS?
