# AI External Certification Tracker

A self-contained web app for tracking AI external certifications across resources,
with self-service updates and leadership dashboards.

## How to run

Just open `certification-tracker.html` in any modern browser (Chrome/Edge/Firefox).
No server, no install, no internet needed. Data is saved in the browser's
`localStorage`, so it survives refreshes and restarts on that machine.

> To reset to the built-in sample data: open DevTools (F12) → Console → run
> `localStorage.removeItem('ai_cert_tracker_v1')` and refresh.

## Screens

| Screen | Purpose |
|--------|---------|
| 🏠 Home | Org-wide tiles (Certified / Planned / Yet to Plan / Total) + status, certification, and team completion charts |
| ➕ Add / Edit Certification | Resource self-service form: employee info + certification details |
| 📝 My Certifications | Gallery of a resource's own records (filter by Emp ID), with Edit / Delete |
| 👨‍💼 Manager View | Filterable team grid (Team / JL / Status / Certification / search), Export to Excel, Send Reminder |
| 📊 Leadership Dashboard | KPI %s, team adoption, certification mix, top certified employees, pending list |

## Dropdowns

**Certifications**
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

**Status:** Yet to Plan · Planned · Certified · Not Passed · Rescheduled

## Auto-calculated status logic

Mirrors the SharePoint `UpdatedStatus` calculated column:

- Completion Date set → **Certified**
- Planned Date set, no completion → **Planned**
- Neither date → **Yet to Plan**
- `Not Passed` / `Rescheduled` are explicit states and are preserved (not overwritten)

Status auto-updates when you change dates, but you can still override it manually.

## Export

Manager View → **Export to Excel** downloads a UTF-8 CSV (opens directly in Excel)
with columns: Sl., Emp#, Name, JL, Account/Team, Manager, Certification, Status,
Planned Date, Completion Date, Area, Remarks. The export respects the active filters.

---

## Mapping to the enterprise (Power Platform) stack

This prototype is intentionally 1:1 with the proposed production design, so it
doubles as a living spec. What's real here vs. what needs a backend:

| Capability | This prototype | Production target |
|------------|----------------|-------------------|
| Frontend / screens | ✅ fully working | Power Apps or React |
| Data storage | `localStorage` (single browser) | SharePoint List / Dataverse |
| Shared data across users | ❌ local only | SharePoint / Dataverse |
| Login / identity | Emp ID typed by user | Azure AD / M365 SSO |
| Auto status | ✅ in-app | SharePoint calculated column |
| Export to Excel | ✅ CSV | Power BI export / native |
| Executive dashboards | ✅ bar charts | Power BI |
| Reminder emails | stub (alert preview) | Power Automate flow |

### SharePoint list columns (target schema)

| Column | Type |
|--------|------|
| EmpID | Single line |
| EmployeeName | Single line |
| JL | Number |
| Team | Single line |
| Manager | Single line |
| CertificationName | Choice |
| Status | Choice |
| PlannedDate | Date |
| CompletionDate | Date |
| Area | Choice |
| Remarks | Multiple lines |
| UpdatedStatus | Calculated |

### Suggested migration path
1. Trial this prototype with a few resources to validate fields and workflow.
2. Stand up the SharePoint list with the schema above.
3. Rebuild the UI in Power Apps (or point a React build at Dataverse) using the
   same screens and dropdowns.
4. Add a Power Automate flow for pending-certification reminder emails.
5. Connect Power BI to the list for the executive dashboard.
