# User guide — 1.2.0

## Start and sign in

Follow README setup. In PowerShell, start with `.\start.bat`, or run `python run.py` with the environment active. The supplied ZIP initializes the configured administrator during setup. Use **Login as Student** for student accounts or **Login as Administrator** for management. Administrators land directly on their management dashboard.

## Student workflow

1. Register a student account or use the optional fictional demo student credentials printed by setup.
2. Choose **Report an item**. Select lost/found, title, category, campus location, date and description. A photograph is optional. Do not publish ID numbers, addresses or private documents.
3. Choose **Submit for review**. The report is private until approved. Open it through **My dashboard** or its notification to follow publication progress.
4. If corrections are requested, read the private review reason, choose **Make corrections**, edit and resubmit. Editing a published report also requires approval again. Reports with active claims cannot be edited.
5. Browse approved listings using keyword, category, location, type, status and event-date filters. No-photo artwork is labeled as an illustration.
6. If an active found report appears to be yours, submit unique identifying evidence. Only you and administrators can read that evidence; ordinary report authors cannot inspect someone else's claim.
7. Track the claim from your dashboard. Respond when an administrator requests clarification. A pending claim can be withdrawn, but you cannot create a second claim for that report afterward.
8. After approval, read the collection point and instructions on the claim page. Arrange pickup and bring appropriate identifying information. Approval reserves the item; it does not mean the physical return is complete.
9. The administrator confirms the actual handover, after which the item and claim show **Returned**.
10. You may close an eligible report without active claims. A closed/rejected report requires administrator assistance to reopen. Closing a lost listing is separate from recording a verified return through a found-item claim.

Notifications update on page requests. **Mark all as read** changes their read state; viewing the page alone does not. Use profile settings for display-name/password changes. For account recovery, contact the trusted local operator; this version has no email-reset service.

## Administrator workflow

### Dashboard and report approval

The sidebar contains **Dashboard, Item reports, Ownership claims, Handovers, Students, Analytics & exports, Activity log, Campus settings**, notifications and account settings. It does not contain student report/claim creation. Opening the student dashboard redirects administrators to management.

1. Open **Item reports**, select **Pending review**, and inspect a report.
2. Check description, category, location, date and photograph. Publication and lifecycle are shown separately.
3. Select **Approve report for publication**, **Request corrections from student**, or **Reject report**. Give a specific reason and confirm.
4. Approval publishes the report. Corrections keep it private until resubmitted and approved. Rejection retains a closed private record.
5. Read prior decisions in **Private review history**. Only the author and administrators can see those reasons.

### Claim verification and collection

1. Open **Ownership claims** and inspect the student's private evidence/conversation.
2. Request clarification, approve ownership or reject with a reason. Independent review is required for any legacy claim involving the administrator's own account.
3. Approval reserves the item and rejects competing undecided claims with an explanation.
4. Open **Handovers** to find approved claims awaiting collection. Choose a claim, then **Arrange handover** to set the collection point and instructions. Saving sends the student an update.
5. Only after physical collection, choose **Confirm physical handover** on the claim page and record a note. Completed handovers appear in **Confirmed returns** with a timestamp.

### Close, hide, restore and reopen

**Close** stops activity and rejects active claims. **Hide** removes public access, closing an active unreturned report. **Restore visibility** does not reopen a closed report. **Reopen** reactivates eligible closed records without restoring rejected/withdrawn claims. Rejected reports go back to pending publication; previously approved reports keep approval. A physically returned report cannot be reopened or changed to closed; it can be hidden while retaining the return record.

### Students

Search students by name/email/access. Open **Manage** to inspect their reporting and claim history. To suspend or reactivate, write a reason and confirm. Records remain intact. Suspension blocks their next authenticated request but does not automatically hide previous reports. Administrator accounts are not managed as students.

### Analytics and exports

Filter reports by keyword, publication state, lifecycle, type, visibility, category/location and submission dates. Submission dates are UTC. The summary counts and category/location charts describe the filtered records. **CSV** and **PDF** download those records; ownership evidence is excluded. Export activity is logged. CSV preserves UTF-8; PDF uses an embedded font and repeated table headings.

### Campus settings and activity

Enter categories, locations and collection points one per line, and set default collection guidance. Give a reason before saving. Existing reports retain historical labels; approved claims keep their assigned instructions until explicitly edited. The activity log shows administrator, action, record, state change, reason and UTC time.

## Editable people and branding

Both Meazbah Mehedi and Monika are listed as Developer & Designer. Edit their names, roles, biographies, photographs and social links in `config/developer.json`; run `python scripts/sync_branding.py` and restart. This configuration is independent of the admin campus-settings page.
