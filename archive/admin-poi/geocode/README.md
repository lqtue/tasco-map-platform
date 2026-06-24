# Vietnam Admin Boundary Dataset — Current + Past (2025 merger)

Authoritative admin-boundary dataset for a reverse-geocoding API that returns the
**current** and **past** administrative name for a coordinate. This package is the
*source of truth* (polygons + keys + attributes). Point-in-polygon, boundary
handling, and any H3/precompute serving layer are left to the consuming infra.

CRS: **EPSG:4326** (lon/lat) for every layer.

## Files

> **Layout note:** the three `*.parquet` data files live under [`data/`](data/) (gitignored — bulk
> data, ~150 MB). Code/docs (`geocode.py`, `MANIFEST.json`, `osm_validation_flags.csv`,
> `requirements.txt`) are tracked at the module root. Run with
> `pip install -r requirements.txt && python3 geocode.py` (reads `data/*.parquet`).

| File | Rows | What |
|---|---|---|
| `admin_current.parquet` | 3,321 | Post-merger wards/communes (2025), 34 provinces. GeoParquet. |
| `admin_past.parquet` | 10,622 | Pre-merger units: 10,610 wards/communes + 12 island districts. 63 provinces. Clean partition. GeoParquet. |
| `crosswalk.parquet` | 38,455 | past↔current area-overlap relations (the merger mapping; incl. 13 island-district rows). |
| `osm_validation_flags.csv` | 26 | Records flagged during OSM cross-check (for review). |

Reverse-geocoding model: run point-in-polygon **independently** on `admin_current`
and `admin_past`; return each side's hit. On `admin_past`, prefer the `tier="ward"`
match and fall back to `tier="district"` (island zones only) when no ward matches.
Use `crosswalk` to enrich with "this current ward was formed from these past wards".

## Schema — `admin_current`

| Column | Type | Notes |
|---|---|---|
| `current_id` | str | **Primary key.** Official 2025 code (`ma`). Unique, stable. |
| `ward_name` | str | **Bare** name (no type word), whitespace-normalised. Compose display as `ward_type + ward_name`. |
| `ward_type` | str | lowercase: `xã` / `phường` / `đặc khu` (special island zone). |
| `province_id` | str | Province code (`matinh`). 34 distinct. |
| `province_name` | str | **Bare** name — e.g. `Hà Nội`, `Hồ Chí Minh`, `Khánh Hòa` (type prefix split out). |
| `province_type` | str | lowercase: `thành phố` (6 cities) / `tỉnh`. |
| `population` | float | Cleaned; **null** where source said "đang cập nhật" (66 rows). |
| `area_km2_off` | float | Official area; null/0 in a few rows (3). |
| `area_km2_geom` | float | Geodesic area from geometry (WGS84). Always present. |
| `lat`,`lon` | float | Official admin-centre point (not polygon centroid). |
| `former_units` | str | Free-text list of pre-merger units (`truocsapnhap`). |
| `ward_name_ascii`,`province_ascii` | str | Diacritics-stripped, lowercased, for search/matching. |
| `osm_rel_id` | Int64 | Matched OSM relation id (admin_level 6). Present on 3,316/3,321; null = no OSM counterpart (3 islands + 2 divergences). Stable join key for future OSM refreshes. |
| `wikidata` | str | Wikidata QID from OSM (948 wards). |
| `osm_name_match` | bool | True (3,297) = OSM name confirms ours exactly; False = matched by geometry only, name differs (review-worthy); null = no OSM match. |
| `geometry` | MultiPolygon | Validated (0 invalid). No internal overlaps. |

> Do **not** key on `matinhxa` from the raw source — it has 13 collisions (all in HCMC). `current_id` is the only safe key.

## Schema — `admin_past`

| Column | Type | Notes |
|---|---|---|
| `past_id` | str | **Primary key** (`ma_xa`). 4 duplicate source rows removed (3 exact + 1 geometric duplicate: "Púng Bánh" 04231≡04228). |
| `ward_name` | str | **Bare** name, whitespace-normalised. |
| `ward_type` | str | lowercase: `xã` / `phường` / `thị trấn` / `huyện` (island tier) / `khu vực quân sự đặc biệt`. |
| `district_id`,`district_name` | str | Pre-merger district tier (abolished in 2025; kept for "past" answers). `district_name` is bare. |
| `district_type` | str | lowercase: `huyện` / `quận` / `thị xã` / `thành phố` (100% populated). |
| `province_id`,`province_name` | str | 63 pre-merger provinces; `province_name` **bare** (same spelling as `admin_current`). |
| `province_type` | str | lowercase: `thành phố` (5 cities) / `tỉnh`. |
| `area_km2_geom` | float | Geodesic area (WGS84). |
| `*_ascii` | str | Search/matching forms. |
| `tier` | str | `ward` (10,610) or `district` (12 records covering the 13 island zones — see below). Prefer `ward`; use `district` only as the island fallback. |
| `geometry` | MultiPolygon | 9 invalid source geoms repaired (`make_valid`); overlaps resolved into a clean partition — a coordinate matches **exactly one** past unit. |

### Island history (the 13 `đặc khu`)

Every 2025 `đặc khu` (special island zone) was a pre-merger **huyện (district) of the
same name** — except **Thổ Châu** (a former xã under Phú Quốc) and **Phú Quý** (stored
under the old spelling **"Phú Quí"**, standardised here to "Phú Quý"). Islands that had
commune subdivisions keep their `ward`-tier records (e.g. a point on Phú Quốc → *Xã Cửa
Dương*). For islands that never had wards (Hoàng Sa, Côn Đảo, Bạch Long Vĩ, Cồn Cỏ) and
for the maritime extent beyond the islet communes (Trường Sa), a **`district`-tier record**
was added (`past_id = "H-<ma_huyen>"`), shaped to the current đặc khu extent minus existing
wards, and carrying the **historical province** (e.g. Phú Quốc → Kiên Giang, Côn Đảo →
Bà Rịa-Vũng Tàu, Phú Quý → Bình Thuận). Result: **all 13 đặc khu return a past name.**

## Schema — `crosswalk`

One row per (past ward × current ward) that overlap. Key columns:

| Column | Notes |
|---|---|
| `past_id`,`current_id` | Foreign keys to the two layers. |
| `ov_km2` | Overlap area (geodesic km²). |
| `pct_of_past`,`pct_of_current` | Overlap as % of each unit's area. |
| `is_primary_for_past` | True = the current ward holding the largest share of this past ward (clean many→1 mapping; primary share is median 99%). |
| `is_primary_for_current` | True = the dominant past ward of this current ward. |
| `significant` | True for real relations; filter on this to drop digitisation slivers. |

Merger shape: each current ward was formed from a **mean of 11.6** past wards
(median 11, max 30). Only ~466 past wards (4.4%) genuinely straddle a new boundary.

## Data-quality / provenance

**Field audit:** no nulls/empties in source. Cleaned: "đang cập nhật" placeholders →
null; comma thousands-separators parsed; 4 duplicate past wards dropped; 9 invalid
past geometries repaired; `admin_past` self-overlaps resolved into a clean partition;
old spelling "Phú Quí" standardised to "Phú Quý"; 12 island-district history records added (covering all 13 đặc khu).

**Name standardisation:** all `*_name` fields hold the **bare proper name only** (no unit-type word),
whitespace-collapsed and spelled identically across both layers (`Hà Nội` is `Hà Nội` in current and
past, not "Thủ đô Hà Nội" vs "Hà Nội"). The unit type lives in a separate lowercase `*_type` column
(`ward_type`, `district_type`, `province_type`). Compose a display label as `Type + Name`
(e.g. `thành phố` + `Hà Nội` → "Thành phố Hà Nội"); `*_ascii` columns are the bare name, de-diacriticised.

**Shape audit (geodesic km²):**

| | km² |
|---|---:|
| Past footprint | 331,923 |
| Current footprint | 334,040 |
| Overlap (both) | 329,015 |
| Only past (not in current) | 2,908 (0.88%) |
| Only current (not in past) | 5,026 (1.50%) |
| Past internal self-overlap | 0 (resolved — was ~150, one duplicate ward) |

**OSM cross-check** (`vietnam-latest.osm.pbf`, current extract; OSM new communes are
`admin_level=6`): **99.4%** of current ward names match OSM exactly; **3,316/3,321**
current wards contain an OSM commune; the 26 exceptions are in `osm_validation_flags.csv`
(3 are offshore `đặc khu` islands OSM doesn't map; ~21 are near-identical
spelling/boundary nuances; 2 are genuine name divergences to review). OSM carries
**no official 2025 code** — only `wikidata` (~30%) and the OSM relation id are stable —
so any OSM enrichment must join by name+geometry, not by code.

## Slivers & differences — how they're handled

Three distinct cases; only one ever made a coordinate lookup ambiguous, and it is now fixed.

| Case | What it is | A coordinate there → | Treatment in this dataset |
|---|---|---|---|
| **A. Current↔past gaps** (7,934 km²) | Coastline/island digitisation differs between the two source layers | hit on one layer, `null` on the other | **Kept as-is.** Return per-side null — it's real, not an error. Each layer is internally complete; they just disagree on coast/island edges. |
| **B. Past self-overlaps** (was ~150 km², one duplicate ward) | Two past wards covered the same ground → a point matched 2 past wards | was **ambiguous** | **Resolved.** `admin_past` is now a clean partition (smaller-ward-wins, then duplicate dropped). A point now matches **exactly one** past ward. |
| **C. Crosswalk slivers** | Thin past×current overlaps along mismatched borders in `crosswalk.parquet` | n/a — only affects the mapping table | Flagged via `significant`; ignore for coordinate lookup. |

So: **inside Vietnam a coordinate yields exactly one current and one past ward.** On the coast/islands it may yield one side only (Case A) — that is the correct, honest answer, not a gap to patch.

## Other caveats for the consuming API

- **13 `đặc khu` island zones** now all have `past` coverage (ward where it existed, else a `district`-tier record with the historical province). A coordinate in far Trường Sa/Hoàng Sa open water beyond the đặc khu polygon can still be null on both layers — that is outside any mapped unit.
- Areas: prefer `area_km2_geom` for consistency; `area_km2_off` is the official figure but ~220 current rows differ from geometry by >20%.
- `osm_rel_id` is null for 5 current wards (3 islands + 2 name divergences); `osm_name_match=False` rows (≈19) matched by geometry but the OSM name differs — both sets are worth a manual glance, listed in `osm_validation_flags.csv`.

## Source files

- Current: `VietnamWardBoundary2025.geojson` ("Merged Data", 2025).
- Past: `Việt Nam (phường xã) - 63.geojson` (pre-merger commune level).
- Past district tier reference: `Việt Nam (quận huyện) - 63.geojson` (705 districts).
