# Implementation Plan

Feature: db-only-data-source
Target file: certification-tracker.html

## Overview

Migrate from the hardcoded SEED_DATA constant to the SharePoint List as the
runtime source of truth, with a two-tier offline fallback (localStorage cache +
JSON backup) and a repurposed JSON export. All NON-DESTRUCTIVE work is done
first; the DESTRUCTIVE removal of SEED_DATA is LAST and GATED on the SharePoint
list being created, seeded, connected, and the page hosted on SharePoint
(Requirement 2.3).

## Task Dependency Graph

```json
{
  "tasks": {
    "1": { "dependsOn": [] },
    "2": { "dependsOn": [] },
    "4": { "dependsOn": [] },
    "3": { "dependsOn": ["1", "2"] },
    "5": { "dependsOn": ["3", "4"] },
    "6": { "dependsOn": ["5"] },
    "7": { "dependsOn": ["6"] },
    "8": { "dependsOn": ["7"] }
  },
  "waves": [
    ["1", "2", "4"],
    ["3"],
    ["5"],
    ["6"],
    ["7"],
    ["8"]
  ]
}
```

- Tasks 1, 2, 4 have no dependencies and may run in parallel first (wave 1).
- Task 3 depends on 1 and 2.
- Task 5 depends on 3 and 4.
- Task 6 is a confirmation gate depending on 5.
- Task 7 (destructive) depends on 6.
- Task 8 depends on 7.

## Tasks

- [x] 1. Add offline cache write on successful SharePoint load (Tier 1)
  - In the SharePoint load path (initData / spReloadFromServer), after a
    successful spGetAll(), write records to localStorage (STORAGE_KEY).
  - Non-destructive; does not touch SEED_DATA.
  - _Requirements: 4.1, 4.4_

- [x] 2. Add offline/empty/error state rendering + banner
  - Implement NOT-CONFIGURED, LOAD-ERROR, and OFFLINE states with messages and
    a persistent "Offline - not live" banner + Reload action.
  - Ensure no silent blank dashboard.
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 3. Wire two-tier offline fallback into initData()
  - DB-first: if enabled+reachable -> live load (+cache). On failure: if cache
    exists -> show cache with offline banner (Tier 1); else -> prompt Load from
    JSON file (Tier 2).
  - Do NOT remove SEED_DATA yet; keep current seed path as the pre-gate default.
  - _Requirements: 4.2, 4.3, 3.2_

- [x] 4. Repurpose the download button to JSON export
  - Replace "Download file with current data as default" behavior: export
    current records as a JSON array of record objects (fields: id, emp, name,
    jl, team, mgr, cert, status, planned, completion, area, remarks).
  - Remove the HTML re-bake (regenerateHtmlWithData) logic.
  - Confirm the export round-trips through existing loadFromFile.
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 5. Verify safeguards still fire (regression)
  - Confirm Emp ID + Certification de-duplication, conflict modal, and all
    screens still work after tasks 1-4.
  - Static check: brace/paren balance; single script/style block.
  - _Requirements: 6.1, 6.2, 6.3_

- [x] 6. GATE: confirm SharePoint prerequisite before removal
  - PREREQUISITE (user-confirmed): list created with exact columns, seeded with
    current data, in-app Test connection OK, Reload shows expected count, page
    hosted on SharePoint.
  - Do not proceed to task 7 until confirmed.
  - _Requirements: 2.3_

- [x] 7. Remove SEED_DATA and make the app DB-only (DESTRUCTIVE, gated)
  - Delete SEED_DATA, seed(), SEED_VERSION, SEED_VERSION_KEY, and the
    seed/version branch in load().
  - Make initData() strictly DB-first (no seed fallback); rely on Tier 1/Tier 2
    for offline.
  - _Requirements: 2.1, 2.2, 1.1, 1.2_

- [x] 8. Post-removal verification + backup
  - Static: grep confirms zero SEED_DATA / seed() / SEED_VERSION references;
    structure balanced.
  - Manual: enabled+reachable loads live; disabled -> NOT-CONFIGURED; unreachable
    -> cache/JSON fallback with banner.
  - Refresh backup snapshots (OneDrive + non-OneDrive).
  - _Requirements: 1.1, 2.1, 3.1, 3.3, 4.2, 4.3_

## Notes

- The destructive task 7 is intentionally gated behind task 6; do not execute it
  until the user confirms the SharePoint list is seeded and the app loads live
  data.
- Tasks 1-5 are safe to perform now without affecting the current SEED_DATA
  fallback, so the app keeps working throughout.
- A backup snapshot already exists (certification-tracker.backup_*.html in both
  OneDrive and a non-OneDrive Documents folder).
