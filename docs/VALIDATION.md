# Release validation — 1.2.0

## Automated verification

**73 test cases passed** on Python 3.12 with SQLite and real CSRF tokens. Temporary databases isolate the suite from local runtime records.

Coverage includes the previous report/claim/account flows plus management-only administrator restrictions; private pending reports; approval, corrections, resubmission and rejection; re-review after editing; close/reopen behavior without claim reactivation; confirmed-return restrictions; collection arrangements/notifications; student access reasons/history; editable settings and historical labels; duplicate option validation; role-protected filtered CSV/PDF exports; CSV formula neutralization; and migration from the original schema while retaining report, claim and audit records.

The migration test verifies old reports remain approved while newly inserted reports become pending. Existing return timestamps are not fabricated during migration.

## Browser and visual verification

A real Chromium browser connected to the local Waitress application completed:

1. Student sign-in and submission of a report with a validated photograph.
2. Private pending-report tracking.
3. Administrator sign-in, management-only navigation and report publication approval.
4. A different student claiming the approved report.
5. Administrator ownership approval, collection arrangements and physical-return confirmation.
6. Closing/reopening an eligible report.
7. Student-history, accounts, claims, handover, analytics, activity and settings screens.
8. Downloading filtered CSV and PDF summaries.
9. Updating a campus location with an activity reason.
10. Theme switching and mobile navigation.

**72 page/viewport checks** covered 320, 390, 768, 1024, 1440 and 1920 pixel widths, including all eight management sections at multiple widths. There were no detected document-level horizontal overflows, broken visible images, JavaScript page errors or console errors in those checks. Wide tables scroll within their panels.

Screenshots were captured from the running app with fictional records. Counts can differ across screenshots because the workflow creates a report, completes a return and updates settings. The downloaded landscape A4 PDF was rendered for layout review, including repeated table headers and page footers. It is a generated report summary rather than a claim-evidence export.

Python syntax compilation, configured Ruff correctness checks, JavaScript syntax and the README's local links were also checked. A fresh virtual-environment installation completed dependency installation, both migrations, one-time administrator setup and demo seeding. The configured administrator login, student-action restrictions, dashboard filters and PDF export also passed in that clean installation.

## Scope and limits

Linux/Python 3.12/SQLite and Chromium were checked here. Windows execution, Docker runtime, other database engines, load capacity, public institutional deployment and accessibility certification were not tested. PowerShell launch examples use the required `.\start.bat` prefix. GitHub Actions is configured for Python 3.11/3.12 and runs after a push; its hosted result is not claimed as already completed.

WTForms 3.3 emits deprecation notices about tuple choices. The locked working release and the compatible range below the removal boundary are retained.

## Reproduce

```bash
python -m pip install -r requirements-lock.txt -r requirements-dev.txt
python -m pytest -q
python -m compileall -q campusfind scripts
```

## Manual acceptance checklist

| Action | Expected result |
|---|---|
| Administrator opens student submission/edit/claim URLs | Denied; no student mutation performed |
| Administrator opens /dashboard or home | Management dashboard |
| Student submits/edits report | Pending and private until approval |
| Visitor or unrelated student opens a pending report/photo | Not found |
| Administrator requests corrections | Author receives private reason and can resubmit |
| Administrator rejects report | Private closed record retained |
| Administrator approves report | Listing publicly searchable |
| Student submits claim | Private evidence and pending ownership review |
| Administrator approves ownership | Reserved; awaiting physical handover |
| Administrator edits collection details | Student notified; item still not returned |
| Administrator confirms physical handover | Item/claim returned with timestamp |
| Administrator closes report | Active claims rejected; no confirmed return counted |
| Administrator reopens eligible report | Activity restored; prior claims stay decided |
| Administrator restores visibility | Closed lifecycle remains closed until reopened |
| Administrator tries reopening returned item | Rejected |
| Administrator suspends student with reason | Next session request blocked; records retained |
| Administrator edits settings | New forms update; historical labels persist |
| Administrator exports filtered analytics | Matching records only; no ownership evidence |
| Student tries management/export routes | Access denied |
| Upgrade existing database | Existing content preserved; future reports pending |
| Edit developer JSON and restart | Both developer/designer cards and footer update |
