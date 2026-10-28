# Requirements Document

Feature: db-only-data-source
Derived from: design.md (design-first workflow)

## Introduction

Migrate the AI External Certification Tracker from a hardcoded `SEED_DATA`
JavaScript constant to the SharePoint List backend as the single runtime source
of truth, remove the constant, and provide a robust two-tier offline fallback
(localStorage cache + JSON backup). User intent: "delete constants as loaded
existing updated data already using DB."

Decisions confirmed with the user:
- Q2 (offline): keep a localStorage cache PLUS a JSON backup fallback; cached /
  backup data is always labelled "not live".
- Q3 (download button): repurpose into a plain JSON export of current records
  (own JSON format = array of record objects, same shape loadFromFile reads).
- Q4 / sequencing: embedded data already refreshed to 203 rows so the SharePoint
  list can be seeded from a current copy. SEED_DATA removal is GATED on the list
  being created, seeded, connected, and the page hosted on SharePoint.

## Glossary

- DB / backend: the SharePoint List "AI_External_Certifications" accessed via the
  SharePoint REST API using same-origin session auth.
- records: the in-memory array of certification record objects.
- SEED_DATA: the current hardcoded constant holding the dataset (to be removed).
- Tier 1 cache: localStorage snapshot of the last successful live load.
- Tier 2 backup: a JSON file export the user can re-import when no cache exists.
- live / not-live: whether displayed data came directly from the DB this session.

## Requirements

### Requirement 1: SharePoint is the runtime source of truth

**User Story:** As a user, I want the app to load certification data from the
SharePoint list at startup, so that the data is centralized and current.

#### Acceptance Criteria
1. WHEN the app starts AND the SharePoint backend is enabled and reachable THEN
   the system SHALL load all records from the SharePoint list into memory.
2. WHEN records are loaded from SharePoint THEN the system SHALL display the
   SharePoint record count and a live status indicator.
3. WHEN a record is added, edited, or deleted AND the backend is enabled THEN
   the system SHALL persist that change to the SharePoint list.
4. WHEN a write to SharePoint is attempted THEN the system SHALL run the Emp ID
   plus Certification de-duplication and conflict modal before committing.

### Requirement 2: Remove the hardcoded data constant

**User Story:** As a maintainer, I want no baked-in dataset in the file, so that
the code does not carry a stale copy of the data.

#### Acceptance Criteria
1. WHEN the migration is complete THEN the system SHALL contain no SEED_DATA
   constant, no seed() function, and no SEED_VERSION or SEED_VERSION_KEY.
2. WHEN the app starts THEN the system SHALL NOT populate records from any
   hardcoded dataset.
3. IF the SharePoint list is not yet created, seeded, connected, and the page
   hosted on SharePoint THEN the removal of SEED_DATA SHALL NOT be performed.

### Requirement 3: No silent blank dashboard

**User Story:** As a user, I want clear feedback when data cannot be loaded, so
that I am never shown an empty dashboard that looks like real data.

#### Acceptance Criteria
1. WHEN the backend is not configured THEN the system SHALL show a "No data
   backend configured" message rather than a silent empty dashboard.
2. WHEN a SharePoint load fails THEN the system SHALL show an error message with
   the reason and a Retry/Reload action.
3. WHEN cached or backup data is displayed THEN the system SHALL show a
   persistent "Offline - not live" banner.

### Requirement 4: Two-tier offline fallback

**User Story:** As a user, I want to still see data when the DB is unreachable,
so that I can keep working from a local cache or a JSON backup.

#### Acceptance Criteria
1. WHEN a SharePoint load succeeds THEN the system SHALL write the loaded records
   to the localStorage cache (Tier 1).
2. WHEN the backend is unreachable AND a localStorage cache exists THEN the
   system SHALL display the cached records with the offline banner.
3. WHEN the backend is unreachable AND no localStorage cache exists THEN the
   system SHALL offer Load from JSON file (Tier 2) to restore the most recent
   JSON backup.
4. WHEN the backend becomes reachable again AND the user clicks Reload THEN the
   system SHALL replace cache/backup data with live data and refresh the cache.

### Requirement 5: JSON export (repurposed download button)

**User Story:** As a user, I want to export the current data to a JSON file, so
that I have a backup I can restore offline.

#### Acceptance Criteria
1. WHEN the user clicks the export button THEN the system SHALL download the
   current in-memory records as a JSON array of record objects.
2. WHEN the JSON is exported THEN each object SHALL contain the fields: id, emp,
   name, jl, team, mgr, cert, status, planned, completion, area, remarks.
3. WHEN a previously exported JSON file is loaded via Load from JSON file THEN
   the system SHALL import it successfully (export and import use one format).
4. WHEN the migration is complete THEN the system SHALL NOT retain the old
   re-bake-SEED_DATA-into-HTML behavior.

### Requirement 6: Preserve existing safeguards

**User Story:** As a user, I want the existing data-quality features to keep
working after the migration, so that nothing else regresses.

#### Acceptance Criteria
1. WHEN importing, merging, or validating THEN the system SHALL keep the existing
   Emp ID plus Certification de-duplication behavior.
2. WHEN a conflict (same Emp plus Cert, different status/dates) occurs THEN the
   system SHALL show the existing conflict modal.
3. WHEN the file is edited THEN the system SHALL preserve all current screens and
   features except those explicitly removed in Requirements 2 and 5.4.

## JSON export format (reference)

An array of record objects:
[
  {
    "id": "sp42", "emp": "34101", "name": "Rajesh Selvaraj", "jl": "6",
    "team": "Charter", "mgr": "Saurabh Aggarwal",
    "cert": "Claude Certified Developer - Foundations", "status": "Planned",
    "planned": "2026-11-06", "completion": "", "area": "NBOP", "remarks": ""
  }
]

## Out of scope

- Two-way offline edit sync (edits made offline re-syncing to SharePoint).
- SharePoint list provisioning/seeding (tenant-admin action; prerequisite).
- Non-SharePoint databases / servers.
