# Design: DB-Only Data Source (remove SEED_DATA)

Feature: db-only-data-source
Target file: certification-tracker.html (single-file app)
Entry point: Design-first (per user choice)

## Overview

Today the tracker ships its data as a hardcoded JavaScript constant `SEED_DATA`
(200+ records) baked into the HTML. A SharePoint REST data layer already exists
and can be toggled on. The goal is to make the **SharePoint List the single
source of truth** for data loaded and edited at runtime, and to **remove the
embedded `SEED_DATA` constant** so the app no longer carries a stale copy of the
data in code.

User request (verbatim intent): "delete constants as loaded existing updated
data already using DB."

Goals
- Remove `SEED_DATA`, `seed()`, `SEED_VERSION`, `SEED_VERSION_KEY`, and the
  seed/version-check branch in `load()`.
- Make `initData()` strictly DB-first: load from SharePoint at startup.
- Define clear empty / error / offline states (no silent blank dashboard).
- Preserve a safe recovery path (existing JSON "Load from file").

Non-goals
- Not changing the SharePoint schema or REST layer (already built).
- Not building a non-SharePoint server/DB.
- Not provisioning or seeding the SharePoint list (tenant-admin action; out of
  code scope, but a hard prerequisite ? see Migration Prerequisite).

## Architecture

Current (as-is) data flow:
- Startup `initData()`: if `spEnabled()` -> `spGetAll()` -> records; on error ->
  fall back to `load()`. Else -> `load()`.
- `load()`: reads localStorage; if `SEED_VERSION` changed or records empty ->
  `seed()`.
- `seed()`: `records = SEED_DATA.map(...)` -> `save()`.
- Writes (add/edit/delete) already persist to SharePoint when `spEnabled()`.
- `regenerateHtmlWithData()` rewrites the SEED_DATA block into a downloadable
  copy (depends on SEED_DATA + SEED_VERSION existing).

Target (to-be) data flow:
- SharePoint List (DB) -> records (runtime). localStorage is an optional cache
  only; there is no embedded constant.
- Startup `initData()` (DB-first):
  - if `spEnabled()`: try `spGetAll()` -> records -> renderAll() with status
    "loaded N from SharePoint"; on error -> ERROR state, do NOT fabricate data.
  - else (backend not configured): NOT-CONFIGURED state; records = [] or last
    cache.
- Removed: `SEED_DATA`, `seed()`, `SEED_VERSION`, `SEED_VERSION_KEY`, and the
  version-check branch inside `load()`.

## Components and Interfaces

Affected functions / symbols:
- `SEED_DATA` (const): DELETE.
- `SEED_VERSION` (const), `SEED_VERSION_KEY` (const): DELETE.
- `seed()`: DELETE.
- `load()`: repurpose to `loadCache()` that only reads any previously cached
  records from localStorage (never invents data), OR remove and replace its
  single call site. Recommended: keep a slimmed cache reader.
- `initData()`: rewrite to DB-first with NOT-CONFIGURED and ERROR states; remove
  the fall-through to seed().
- `regenerateHtmlWithData()` + its button: can no longer re-bake a constant.
  Option (a) remove; Option (b) repurpose to export current in-memory `records`
  to JSON (same as existing "Save to JSON file"). Recommended: (b)/remove to
  avoid dead code.
- Unchanged: `spGetAll`, `spCreate`, `spUpdate`, `spDelete`, `spGetDigest`,
  `spEnabled`, SharePoint config card, `loadFromFile()` (JSON recovery).

Interfaces (SharePoint REST, already implemented):
- GET list items -> array of records (spGetAll).
- POST create / MERGE update / DELETE per record (spCreate/spUpdate/spDelete).

## Data Models

Record (in-memory, unchanged):
- id: string (local uid, or "sp"+ListItemId when from SharePoint)
- spId: number (SharePoint list item Id; present only for DB-backed records)
- emp, name, jl, team, mgr, cert, status, planned (YYYY-MM-DD), completion
  (YYYY-MM-DD), area, remarks: strings

SharePoint list column mapping (unchanged): EmpID, EmployeeName, JL, Team,
Manager, CertificationName, Status, PlannedDate, CompletionDate, Area, Remarks.

localStorage keys after change:
- STORAGE_KEY (ai_cert_tracker_v1): optional cache of last loaded records.
- SP_CFG_KEY (ai_cert_sp_cfg_v1): SharePoint config (unchanged).
- REMOVED: SEED_VERSION_KEY (ai_cert_seed_version_v1).

## Correctness Properties

Property 1: DB is authoritative when enabled.
With `spEnabled()` true and the list reachable, `records` after startup equals
the SharePoint list contents (count and field values) ? no constant involved.
**Validates: Requirements 1.1, 1.2**

Property 2: No hardcoded data source remains.
After the change, no code path populates `records` from a baked-in dataset;
`SEED_DATA` and `seed()` no longer exist.
**Validates: Requirements 2.1, 2.2**

Property 3: No silent blank dashboard.
When the backend is unreachable or unconfigured, the app shows an explicit
state message and never presents an empty dashboard as if it were valid live
data.
**Validates: Requirements 3.1, 3.2, 3.3**

Property 4: Writes still persist and validate.
Add/edit/delete continue to persist to SharePoint when enabled, and the
de-duplication + conflict modal still run before writes.
**Validates: Requirements 1.3, 1.4, 6.1, 6.2**

## Error Handling

- NOT CONFIGURED (spEnabled() false): message "No data backend configured.
  Connect SharePoint or Load from JSON file." Tiles show 0 (expected).
- LOAD ERROR / OFFLINE (spGetAll throws or no network): apply the two-tier
  Offline Fallback Strategy below instead of showing a blank dashboard. Always
  show a persistent "Offline - showing cached/backup data (not live)" banner and
  a Reload button to retry the live DB.

## Offline Fallback Strategy (Q2 decision: CONFIRMED)

Decision: keep a minimal local cache AND an auto-maintained JSON backup, used in
this priority order when the SharePoint DB is unreachable/offline:

Tier 1 - localStorage cache (STORAGE_KEY):
- On every SUCCESSFUL spGetAll(), write the loaded records to localStorage
  (JSON). This is the "last known live" snapshot.
- When the DB is unreachable, load records from this cache and show the offline
  banner.

Tier 2 - JSON backup file fallback:
- Also, on every successful load, keep a downloadable JSON backup available
  (the existing "Save to JSON file" produces this; optionally the app can
  auto-offer / store the newest export).
- If localStorage has NO cache (fresh browser, cache cleared, or private mode),
  the app offers "Load from JSON file" (existing loadFromFile) so the user can
  restore the most recent JSON backup and keep working offline.
- This guarantees there is always a recovery source even without a cache.

Rules:
- Cache/backup data is ALWAYS labelled "not live" via the offline banner so it
  is never mistaken for current DB state.
- The moment the DB is reachable again, Reload replaces cache with live data and
  refreshes the cache + backup.
- Edits made while offline are a known limitation: they write to localStorage
  cache only and must be re-synced (out of scope for this change; flag to user).

## Testing Strategy

- Manual: with SharePoint disabled -> NOT-CONFIGURED state, no fabricated data.
- Manual: with SharePoint enabled + reachable -> N records load; counts match
  the list.
- Manual: with SharePoint enabled but unreachable (open locally) -> ERROR state
  + JSON recovery works.
- Static: grep the file to confirm zero references to SEED_DATA / seed() /
  SEED_VERSION remain; brace/paren balance unchanged; single script/style block.
- Regression: add/edit/delete still write to SharePoint; conflict modal + dedupe
  still fire.

## Migration Prerequisite and Sequencing (GATE)

Deleting SEED_DATA is only safe after ALL of:
1. SharePoint list AI_External_Certifications created with the exact columns
   (ENTERPRISE_SETUP_GUIDE.md section 1).
2. List SEEDED with current data (section 2) ? use the latest 203-row dataset as
   the seeding source.
3. Page HOSTED on the SharePoint site so same-origin auth works (section 9).
4. In-app SharePoint card: enabled, Test connection OK, Reload shows N records.

Recommended sequencing:
- Step 0: Backup snapshot (already done: certification-tracker.backup_*).
- Step 1: Refresh embedded data to the 203 rows (one-time) OR export current
  records to JSON, to seed the list from a current copy.
- Step 2: Create + seed the SharePoint list; verify in-app load.
- Step 3: ONLY THEN remove SEED_DATA and switch to DB-only.

No code deletion is performed until this gate is satisfied.

## Risks and Mitigations

- OneDrive rollback (folder has reverted edits mid-session): out-of-OneDrive
  backup created; re-verify after edits.
- Auth only when hosted on SharePoint: made visible via NOT-CONFIGURED/ERROR
  states instead of failing silently.
- Loss of offline fallback: mitigated by optional localStorage cache + JSON
  import recovery.
- Last-writer-wins on concurrent edits: pre-existing SharePoint limitation; out
  of scope.

## Open Questions

- Q1: Is the SharePoint list CREATED and SEEDED, and is the HTML HOSTED on the
  SharePoint site? (Deletion unsafe until yes.)
- Q2: RESOLVED - keep a minimal offline localStorage cache PLUS a JSON backup
  fallback (two-tier). See Offline Fallback Strategy. Cache/backup always
  labelled "not live".
- Q3: `regenerateHtmlWithData()` ? remove it, or repurpose to a JSON export?
- Q4: Before removal, refresh embedded data to the 203 rows to seed the list, or
  will you seed from your own CSV/Excel?
