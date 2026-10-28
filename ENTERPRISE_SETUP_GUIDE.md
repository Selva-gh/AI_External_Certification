# AI External Certification Tracker — Enterprise Build Guide (Power Platform)

Target architecture:

    Power Apps  ->  SharePoint List  ->  Power Automate  ->  Power BI
                          |
                          +--> JSON Backup Archive (daily snapshot)

This moves the tracker off the single-file / browser-storage prototype and onto a
proper M365 backend. It delivers:

- Multi-user updates (everyone edits the same list)
- No browser-storage issues (nothing depends on localStorage)
- No data loss (central storage + daily JSON backups)
- Real-time dashboards (Power BI on the live list)
- Automatic backups (Power Automate nightly export)
- Audit trail (SharePoint Created/Modified By + Modified Date, plus version history)

> You need: a SharePoint site (Team site), permission to create lists, and a
> Power Platform environment (Power Apps + Power Automate). Power BI Desktop/Service
> for dashboards. Ask your M365 / Power Platform admin if you are unsure.

--------------------------------------------------------------------------------

## 1. SharePoint List — the single source of truth

Create a list named **AI_External_Certifications** on your SharePoint site.

### Columns

| Display name        | Internal type        | Notes                                                        |
|---------------------|----------------------|--------------------------------------------------------------|
| Title               | Single line          | Default column. Use for a row label or hide it.              |
| EmpID               | Single line of text  | e.g. 1320548. Keep as text (leading-zero / ID safe).         |
| EmployeeName        | Single line of text  |                                                              |
| JL                  | Single line of text  | Text, not Number — real data has values like "NOBA".         |
| Team                | Single line of text  | e.g. Charter                                                 |
| Manager             | Single line of text  | or Person/Group if you want real identities                  |
| CertificationName   | Choice               | choices below                                                |
| Status              | Choice               | Yet to Plan / Planned / Certified / Not Passed / Rescheduled |
| PlannedDate         | Date only            |                                                              |
| CompletionDate      | Date only            |                                                              |
| Area                | Choice (or text)     | NBOP, MIS, NPM, Framework, SM360, Pandora, OFS, PCAT, ECF, Architecture, Other |
| Remarks             | Multiple lines       | plain text                                                   |
| UpdatedStatus       | Calculated           | formula below                                                |

**CertificationName choices** (match the prototype exactly):
- Claude Certified Associate – Foundations
- Claude Certified Developer – Foundations
- Claude Certified Architect – Foundations
- Claude Certified Architect – Professional
- Amazon AI Practitioner
- AWS Agentic AI Essentials
- OCI AI Foundation
- GitHub Copilot
- Salesforce AI Associate
- Other

> Tip: real data has free-text certs ("Google certification", "IBM ... ", etc.).
> Either add them as choices, enable "Can add values manually" on the Choice column,
> or map them to "Other" during import.

### UpdatedStatus calculated column

Mirrors the prototype's auto-status logic. Set column type = Calculated, return type = Single line of text:

    =IF(NOT(ISBLANK(CompletionDate)),"Certified",
        IF(NOT(ISBLANK(PlannedDate)),"Planned","Yet to Plan"))

Note: a calculated column cannot "respect" manual Not Passed / Rescheduled states.
If you need those preserved, keep **Status** as the editable field and treat
**UpdatedStatus** as an informational fallback, exactly like the prototype
(which preserves Not Passed / Rescheduled and otherwise auto-derives).

### Audit trail (built in)
SharePoint already tracks **Created**, **Created By**, **Modified**, **Modified By**.
Turn on **List settings -> Versioning settings -> Create a version each time you edit**
to get a full change history per record.

--------------------------------------------------------------------------------

## 2. Seed the list from the current prototype data

You already have the 200 records. Two ways in:

**Option A — Quick (Excel/Grid):**
1. Export from the prototype: Manager View -> Export to Excel (CSV), or use the
   Save to JSON file button.
2. Open the list -> "Edit in grid view" -> paste rows. Match columns left to right.

**Option B — Power Automate one-time import:**
1. Put the exported JSON in a SharePoint document library.
2. Build a manual flow: Get file content -> Parse JSON -> Apply to each ->
   Create item in AI_External_Certifications.
   Use the JSON schema from the prototype's exported file (fields: emp, name, jl,
   team, mgr, cert, status, planned, completion, area, remarks).

Field mapping (prototype JSON -> SharePoint):

    emp->EmpID  name->EmployeeName  jl->JL  team->Team  mgr->Manager
    cert->CertificationName  status->Status  planned->PlannedDate
    completion->CompletionDate  area->Area  remarks->Remarks

--------------------------------------------------------------------------------

## 3. Power Apps — the front end (replaces the HTML)

Build a Canvas app bound to the list. Rebuild the same five screens:

| Prototype screen            | Power Apps screen                                          |
|-----------------------------|-----------------------------------------------------------|
| Home dashboard              | Gallery + charts on aggregates of the list                |
| Add / Edit Certification    | Edit form (SharePointIntegration or custom Form control)  |
| My Certifications           | Gallery filtered to User().Email / current EmpID          |
| Manager View                | Filterable gallery + export                                |
| Leadership Dashboard        | Prefer Power BI tile embed (see section 5)                 |

Key points:
- Data source: SharePoint connector -> your site -> AI_External_Certifications.
- Identity: use `User().Email` / `User().FullName` to auto-fill who is editing
  (replaces the typed Emp ID in the prototype).
- Submitting a form writes straight to the list = instant multi-user sync.
- Reuse the Choice values above so dropdowns match.

--------------------------------------------------------------------------------

## 4. Power Automate — reminders + daily JSON backup

### 4a. Pending-certification reminder (recurrence)
- Trigger: Recurrence (e.g., weekly Monday 9am).
- Get items: Filter Query `Status ne 'Certified'`.
- (Optional) filter to records with a PlannedDate within N days.
- Send an email (Outlook) / Teams message to each Manager with their pending list.
This replaces the prototype's "Send Reminder" stub.

### 4b. Daily JSON backup snapshot (your backup archive)
Goal: SharePoint/AI_External_Certification/Backups/AI_Certification_Backup_YYYYMMDD.json

- Trigger: Recurrence, daily (e.g., 01:00).
- Get items from AI_External_Certifications (set a high top-count / pagination on).
- Select action to shape each item into the clean JSON schema
  (EmpID, EmployeeName, JL, Team, Manager, CertificationName, Status,
   PlannedDate, CompletionDate, Area, Remarks).
- Compose: `json(outputs of Select)`.
- Create file in the Backups library:
  - File name: `AI_Certification_Backup_@{formatDateTime(utcNow(),'yyyyMMdd')}.json`
  - File content: the composed JSON.
- (Optional) add a cleanup step to delete backups older than N days.

This gives the "daily snapshot" + "no data loss" guarantees in your diagram,
and the files are human-readable and re-importable via the flow in section 2B.

--------------------------------------------------------------------------------

## 5. Power BI — executive dashboards

- Get Data -> SharePoint Online List -> your site URL -> select
  AI_External_Certifications.
- In Power Query, keep the real columns; set PlannedDate/CompletionDate as Date.
- Build the same visuals the prototype shows:
  - Cards: Total, Certified, Planned, Yet to Plan (and %).
  - Status-wise bar, Certification-wise bar, Team completion %.
  - Top certified employees, pending list.
- Refresh: schedule in Power BI Service (e.g., every few hours) for near real-time.
- Optional: embed a Power BI tile back into the Power Apps Leadership screen.

--------------------------------------------------------------------------------

## 6. Rollout checklist

- [ ] Create SharePoint list with the schema in section 1.
- [ ] Turn on versioning for the audit trail.
- [ ] Seed the 200 records (section 2).
- [ ] Build the Power Apps canvas app (section 3) and share it with resources.
- [ ] Build the reminder + daily backup flows (section 4).
- [ ] Build and schedule the Power BI report (section 5).
- [ ] Decommission reliance on the HTML prototype (keep it as an offline viewer only).

## 7. How the prototype still helps

The HTML prototype stays useful as:
- A living spec: screens, dropdowns, and auto-status logic are already defined.
- An offline / personal viewer (with JSON Save/Load for ad-hoc sharing).
Once the SharePoint + Power Apps stack is live, it becomes the system of record and
the prototype is no longer where data is maintained.

--------------------------------------------------------------------------------

## 8. HTML Tracker -> Power Automate HTTP trigger -> SharePoint library

This is the lightweight sync used by the HTML tracker Cloud sync card. It lets the
single-file app auto-save all records to a shared SharePoint JSON file without a
full Power Apps rebuild.

    HTML Tracker -> Power Automate (HTTP trigger) -> Create/Update JSON file -> SharePoint library

### 8a. Build the flow (Power Automate -> Instant cloud flow)

1. Trigger: **When an HTTP request is received**.
   - Request Body JSON Schema: an array of record objects. Use:

         {
           "type": "array",
           "items": {
             "type": "object",
             "properties": {
               "id": { "type": "string" },
               "emp": { "type": "string" },
               "name": { "type": "string" },
               "jl": { "type": "string" },
               "team": { "type": "string" },
               "mgr": { "type": "string" },
               "cert": { "type": "string" },
               "status": { "type": "string" },
               "planned": { "type": "string" },
               "completion": { "type": "string" },
               "area": { "type": "string" },
               "remarks": { "type": "string" }
             }
           }
         }

   - Method: POST (set under the trigger "Show advanced options" if needed).

2. Action: **Compose** (optional) = `triggerBody()` so you can inspect the payload.

3. Action: **Create file** (SharePoint).
   - Site Address: your site.
   - Folder Path: /Shared Documents/AI_External_Certification/Backups  (or your library)
   - File Name: `AI_Certifications_latest.json`
     (or timestamped: `AI_Certifications_@{formatDateTime(utcNow(),'yyyyMMdd_HHmmss')}.json`)
   - File Content: `triggerBody()`  (the raw JSON array the HTML sent)

   Note: "Create file" fails if the file already exists. For a single rolling file,
   either (a) use **Update file** after a Get file metadata, or (b) always write a
   timestamped name and keep "latest" via a separate copy step. Simplest robust
   pattern: Try **Get file metadata** by path -> if found, **Update file**; else
   **Create file**. Or just always timestamp and treat the newest as current.

4. Action: **Response** (optional but recommended).
   - Status Code: 200
   - Body: `{ "ok": true, "count": @{length(triggerBody())} }`

5. Save. Copy the trigger URL from step 1 (the HTTP POST URL).

### 8b. Connect the HTML tracker

1. Open the tracker -> Bulk Upload screen -> **Cloud sync** card.
2. Paste the flow HTTP POST URL -> **Save URL**.
3. Leave **Auto-push after edits** checked. Now every add/edit/delete auto-pushes
   (debounced ~3s) the full record set to SharePoint. Use **Push now** to force it.

### 8c. Known limitations / cautions

- **The URL is a write key.** Anyone with it can POST to your flow. The tracker
  stores it only in the local browser (not in the shared HTML file) for this reason.
  Do not paste it into the file you share. Treat it like a password.
- **CORS:** browsers may block `fetch()` to the flow from a `file://` page or the
  SharePoint preview. If Push fails with a network/CORS error, run the HTML from a
  trusted host, or add a Response action with the header
  `Access-Control-Allow-Origin: *` (be aware this loosens access). The tracker shows
  the error and your data is still safe locally + via JSON file.
- **Last-writer-wins:** concurrent pushers overwrite each other. For true multi-user
  editing use the SharePoint List + Power Apps design (sections 1-5).
- **Pull is not wired** in this mode (auto-push only). The HTML does not read the file
  back automatically; use Load from JSON file if you need to re-import.

--------------------------------------------------------------------------------

## 9. HTML tracker as a LIVE SharePoint-backed app (runtime DB)

The tracker now has a built-in SharePoint data layer. When enabled, it loads from
and saves to a SharePoint list at runtime instead of the built-in SEED_DATA.

### 9a. One-time setup
1. Create the list from section 1 (AI_External_Certifications) with those exact
   internal column names: EmpID, EmployeeName, JL, Team, Manager, CertificationName,
   Status, PlannedDate, CompletionDate, Area, Remarks.
2. Upload certification-tracker.html to the SAME SharePoint site (e.g. a Site Assets
   or Documents library), and open it from there (Open in browser).
   - This is required so the page can authenticate as the logged-in user. A file
     opened from your desktop / OneDrive sync folder (file://) CANNOT auth to SharePoint.
3. In the app: Bulk Upload screen -> "SharePoint backend (database)" card:
   - Site URL: the site, e.g. https://tenant.sharepoint.com/sites/YourSite
   - List name: AI_External_Certifications
   - Tick "Use SharePoint as backend" -> Save settings.
   - Click "Test connection" (should say Connection OK), then "Reload from SharePoint".

### 9b. How it behaves at runtime
- On load: reads all list items -> records (falls back to built-in data if unreachable).
- Add / Edit (form): writes a Create or Update (MERGE) to the list for that record.
- Delete: removes the list item.
- Emp ID + Certification de-duplication and the conflict modal still apply before writes.
- Settings (site/list/enabled) are stored only in the local browser, not in the file.

### 9c. Seeding the list the first time
Use section 2 to load the 200 records into the list once (grid paste, or the
import flow). After that the list is the source of truth and the app edits it live.

### 9d. Limitations / notes
- Auth model = the logged-in user's SharePoint session + form digest. Works only
  when the page is hosted on that SharePoint site (not from file:// or the preview).
- Users need at least Contribute permission on the list to add/edit/delete.
- Choice columns (CertificationName, Status, Area): either pre-create all choices,
  enable "fill-in" choices, or values posted that are not in the choice set may be
  rejected by SharePoint. Keeping them as Single line of text avoids that entirely.
- For cross-network access without hosting on SharePoint, switch to an Azure AD app
  + MSAL login (bigger setup) instead of the same-origin session model used here.
