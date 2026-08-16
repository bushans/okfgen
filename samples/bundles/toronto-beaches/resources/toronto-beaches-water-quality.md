---
type: Data Resource
title: toronto-beaches-water-quality
description: GeoJSON resource in dataset toronto-beaches-water-quality.
resource: "https://ckan0.cf.opendata.inter.prod-toronto.ca/datastore/dump/8102bd4c-83cd-4354-9788-eecc0c7a09b4"
tags:
  - open-data
  - resource
  - geojson
sources:
  - resource: "https://ckan0.cf.opendata.inter.prod-toronto.ca/datastore/dump/8102bd4c-83cd-4354-9788-eecc0c7a09b4"
    title: toronto-beaches-water-quality
    last_modified: 2026-08-15
generated:
  by: okfgen/0.1.2
  at: "2026-08-16T13:48:45+00:00"
format: GeoJSON
---

# Schema

| Column | Type |
|---|---|
| `beachId` | int4 |
| `beachName` | text |
| `siteName` | text |
| `collectionDate` | date |
| `eColi` | int4 |
| `geometry` | text |

# Examples

| beachId | beachName | siteName | collectionDate | eColi | geometry |
|---|---|---|---|---|---|
| 1 | Marie Curtis Park East Beach | 29W | 2026-08-14 | 240 | {"type": "Point", "coordinates": [-79.53 |
| 1 | Marie Curtis Park East Beach | 33W | 2026-08-14 | 20 | {"type": "Point", "coordinates": [-79.54 |
| 1 | Marie Curtis Park East Beach | 32W | 2026-08-14 | 30 | {"type": "Point", "coordinates": [-79.54 |

_Total rows: 101,182_

# Related

Referenced by:
- [Toronto Beaches Water Quality](/overview.md)
