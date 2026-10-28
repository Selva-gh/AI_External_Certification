# How to run the AI Certification Tracker (local database)

The app now uses a REAL database: a SQLite file (certifications.db) served by a
small Python API (server.py). Data is read with SELECT and changed with
INSERT / UPDATE / DELETE at runtime.

## Requirements
- Python 3 (already installed). No pip packages needed - uses the standard
  library only (http.server + sqlite3).

## Start
1. Open a terminal in this folder.
2. Run:
       python server.py
3. You should see:
       DB API running at http://localhost:8000
       Open the app:  http://localhost:8000/certification-tracker.html
4. Open that URL in your browser.
   The app auto-detects the local API and loads the 203 records from the DB.

## What happens on edits
- Add a record  -> POST /api/records     (INSERT)
- Edit a record -> PUT  /api/records/<id> (UPDATE)
- Delete        -> DELETE /api/records/<id>
- View/refresh  -> GET  /api/records      (SELECT)
All changes are saved in certifications.db immediately.

## Files
- server.py            - the API server (start this)
- certifications.db    - the SQLite database (auto-created, seeded with 203 rows)
- seed_data.json       - the seed used ONLY on first run when the DB is empty
- certification-tracker.html - the app UI

## Reset the database
Stop the server, delete certifications.db, and start again - it will re-seed
from seed_data.json (203 records).

## Notes
- If you open certification-tracker.html directly (file://) WITHOUT the server,
  the app cannot reach the API; it will show the offline state and you can use
  "Load from JSON file". Always start server.py for live DB access.
- The server listens on 127.0.0.1:8000 (local machine only).


## Data sync behavior (DB + seed_data.json + local cache)

Every add / edit / delete keeps all three stores consistent:

ONLINE (server.py running):
- The change is written to the DB (certifications.db) via the API.
- The server immediately re-writes seed_data.json to mirror the DB.
- The browser updates its localStorage cache.
=> DB, seed_data.json, and cache all stay in sync.

OFFLINE (no server / server unreachable):
- The browser can only update its localStorage cache (it cannot write the
  .db or .json files - a browser has no file access without the server).
- The change is added to an offline queue (stored in localStorage).
- The top-right indicator shows "Offline - change queued (N pending)".
- Next time you open the app WITH the server running, the queued changes are
  automatically replayed to the API (POST /api/sync), which updates the DB and
  re-writes seed_data.json. Then the queue is cleared.
=> Offline edits are preserved and synced on reconnect.

Note: seed_data.json is now the live mirror of the DB (not just the first-run
seed). If you reset the DB by deleting certifications.db, it re-seeds from the
current seed_data.json.
