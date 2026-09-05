# Vendor Portal (vendor_mgmt) -- context for future work

Part of the IFMS prototype suite (4 independent apps under `E:\IFMS`): Employee Portal, Pensioner
Portal, Vendor Portal, and a back-office Admin Portal that talks to all three over their APIs.
Modeled on a GNCTD-style vendor/supplier onboarding + contract + invoice + payment SRS.

## Stack & ports
- Backend: FastAPI + SQLAlchemy 2.0 + PostgreSQL. Runs on **:9003**.
- Frontend: React (Vite) + Tailwind CSS (strictly Tailwind, no inline CSS). Runs on **:7003**.
- DB: `postgresql+psycopg2://vendor_db:vendor_db@localhost:5432/vendor_db` (see `backend/.env`).
- No migrations tool -- `Base.metadata.create_all()` on startup creates missing tables only; new
  columns on existing tables were added additively via `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
  (e.g. `stored_path` on VendorDocument/InvoiceDocument) rather than a destructive schema reset.

## Non-negotiable project conventions (apply to every portal, not just this one)
- Keep code simple enough for a junior dev to follow -- no premature abstraction.
- Tailwind CSS only, never inline `style=` CSS.
- Every table has `AuditMixin`: `is_active`, `is_deleted`, `server_date`, `operation_date`.
- Boolean DB columns stay native SQLAlchemy `Boolean` -- **do not** convert to `VARCHAR(1)` Y/N.
  Explicitly proposed and explicitly rejected project-wide; see `emp_mgmt_pro/CONTEXT.md` for the
  full reasoning if this comes up again.
- Hand-drawn SVG icons only, no icon library, no emoji.
- Never run git/GitHub commands yourself -- always give the user the exact command to run.

## Auth pattern (same shape in every portal, including admin_portal)
Two-step JWT login: `POST /auth/login` (field is `email`) returns a `pending_token` ->
`POST /auth/verify-otp` (any 6 digits accepted) returns the `access_token`. bcrypt used directly.
`app/masking.py` masks emails in failed-login audit log details (`mask_email`).

## Key backend modules
- `app/models.py` -- `Vendor`, `VendorDocument`, `VendorApplicationEvent`, `CredentialVerification`,
  `ProfileChangeRequest`, `Contract`, `Invoice`/`InvoiceDocument`, `Payment`, `AuditLog`.
- `app/storage.py` -- real local-disk file storage under `app/uploads/` for vendor/invoice
  documents: `validate_upload` / `save_upload` / `read_stored_file`. Documents have a `stored_path`
  column; `has_file` on the `VendorDocumentOut`/schemas is computed from `bool(stored_path)`.
- `app/routers/contracts.py` -- `invoiced_amount()` computes remaining contract value; invoice
  submission validates against it plus a date-range check.
- `app/routers/payments.py` -- `list_payments` supports `status`, `search`, `date_from`/`date_to`,
  `min`/`max_amount` query filters. `STAGE_SLA_DAYS = {"Initiated": 2, "Processing": 3}` in
  `contracts.py`/`payments.py` drives the SLA-based `expected_completion_date`.
- `app/routers/approver.py` -- reviewer queue lives at **`GET /approver/applications`**
  (not `/approver/queue` like the other two portals) for vendor registration applications, plus a
  **separate** `GET /approver/profile-changes` for post-approval profile edits. Review endpoints:
  `POST /approver/applications/{vendor_id}/review` (status Approved/Rejected/Returned) and
  `POST /approver/profile-changes/{id}/review` (status Approved/Rejected only -- no "Returned").
  Also has document-level (`/approver/documents/{id}/review`) and credential-verification-level
  (`/approver/credential-verifications/{id}/decision`) review endpoints not surfaced in
  admin_portal's unified queue (out of scope there for now). **admin_portal's `integrations.py`
  depends on the applications/profile-changes shape** -- keep them in sync.
- Already had Reports/MIS (`app/routers/reports.py`) and Audit Log (`app/routers/audit.py`,
  `app/csv_export.py`) before the other two portals did -- they were built by mirroring this app.

## Frontend notes
- Custom bilingual i18n, English-text-as-key style (`src/i18n/hi.js`), same pattern as pension_mgmt.
- `src/pages/ApplicationDateField.jsx` on Documents/Invoices/Profile/Register forms.
- `api/apiService.js` has `postForm()` (multipart upload) and `downloadFile()` (blob download) in
  addition to the usual get/post/put/del -- needed for real file upload/download, unlike the other
  two portals which don't yet have file uploads.

## Reviewer / approver accounts
**Unlike the other two portals, this one auto-seeds demo accounts** (`app/seed.py`,
`seed_demo_accounts`, called from `main.py` on startup if the `Vendor` table is empty): a reviewer
account `email=reviewer@vendor.gov.in` / `reviewer123` (role `reviewer`, pre-approved), plus a demo
approved vendor. This reviewer account is also **admin_portal's service account credential** for its
vendor-portal integration (`admin_portal/backend/.env`, `VENDOR_SERVICE_*`). Do not delete/rename it
without updating that file.

## Status (as of 2026-09-03)
Most mature of the three public portals. ~85-90% of SRS-derived functional coverage by the project
owner's informal estimate (per their explicit framing: "if functionality works, real third-party
verification like live PAN lookup counts as done" -- it's mocked, not a live API call). Real local
file storage, contract-remaining-value validation, payment filters, and SLA-based
expected-completion-date were all closed out as gaps earlier and are tested.

## Related
See `E:\IFMS\admin_portal\CONTEXT.md` for how the back-office Admin Portal calls into this app's
`/approver/*` endpoints via a service account, and `E:\IFMS\TESTING_GUIDE.md` for cross-portal
end-to-end test steps. The public landing page (`E:\IFMS\landing\index.html`) links to this portal's
login/register.
