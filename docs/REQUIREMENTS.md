# Requirements and proposal traceability — 1.2.0

The project implements the proposal's lost reporting, found reporting, item search and claim/status management. Version 1.2.0 refines the administrator into a management-only role and introduces publication review before public listing.

## Roles and boundaries

| Role | Allowed functions | Restricted functions |
|---|---|---|
| Visitor | Browse approved visible listings, view public details | Private records, submission, claims and management |
| Student | Submit/edit reports, respond to corrections, search, claim eligible found items, answer clarification, track notifications | Publication approval, management settings, other students' private evidence |
| Administrator | Publication review, claim decisions, handovers, report lifecycle, student access/history, analytics, exports, settings, activity review | Student report creation/edit/closure routes, submitting/withdrawing claims, claimant replies |
| Local operator | Initialize/migrate database, configure/reset administrator credentials, back up/reset local data | This trusted filesystem role is outside web account permissions |

## Functional requirements

| ID | Requirement | Implementation |
|---|---|---|
| FR-01 | Students submit lost/found reports with structured details and optional photo | Student report form |
| FR-02 | New reports remain private pending administrator publication approval | Item.review_status, visibility checks, review queue |
| FR-03 | Administrators request corrections, approve or reject with a reason | Report moderation service and private ReportReview history |
| FR-04 | Editing an eligible report requires renewed approval | Student edit/resubmit workflow |
| FR-05 | Public search combines keyword/type/category/location/lifecycle/event dates | Approved-visible query with filters and pagination |
| FR-06 | Students submit private ownership evidence for active approved found reports | Claim form and access checks |
| FR-07 | Administrators request claim clarification, approve/reject with notes | Private claim conversation and decision service |
| FR-08 | Approval reserves the item; handover separately records physical return | Reserved claim and returned_at timestamp |
| FR-09 | Administrator assigns collection point/instructions and notifies student | Handover management |
| FR-10 | Close/hide/restore/reopen eligible reports while preserving history | Publication/lifecycle moderation |
| FR-11 | Search student accounts, inspect history, suspend/reactivate with reason | Student management screens |
| FR-12 | Notify students of decisions and administrators of submissions/clarifications | User-scoped in-app notifications with record links |
| FR-13 | Display actionable management totals, queues, trends and recent decisions | Management dashboard |
| FR-14 | Filter report analytics and download matching CSV/PDF summaries | Admin-only analytics/export routes |
| FR-15 | Record actor, record type/ID, previous/next state, reason and UTC time | Structured Audit entries |
| FR-16 | Edit categories, locations, collection points and default instructions | CampusSetting records and validated settings form |
| FR-17 | Keep developer/designer identities editable independently of application logic | config/developer.json and README sync |

## Key rules

1. Public registration always creates a student. Login selection does not assign or elevate a role.
2. Only approved, non-hidden reports/photos are public. Pending/correction/rejected records are visible only to their author and administrators. A claimant can still read their own private claim history after the report closes or is hidden.
3. Publication and ownership approvals are separate. A published listing is not proof of a claimant's ownership.
4. Only one claim may reserve an item. Conditional database reservation protects competing approvals; other undecided claims are rejected with a reason. A unique item/claimant constraint prevents repeat claims, including after rejection/withdrawal.
5. Only the approved reserved claim can be marked physically returned. Closing alone never increases confirmed-return counts.
6. Closing a report rejects its active claims. Reopening retains previous claim decisions. Restoring visibility does not reopen a report. Returned reports cannot be reopened or changed to closed through normal management.
7. Requesting corrections on a published report is allowed only before active claim review. Editing is limited to an author's visible, Reported report without active claims.
8. Rejection closes an unpublished report. An administrator must reopen it before further student editing. A rejected report returns to pending publication when reopened; an already approved report retains approval when reopened.
9. Administrators may view legacy reports/claims involving their accounts but cannot use student actions on them. An independent administrator must decide legacy claims involving the reviewer.
10. Student suspension blocks sign-in and existing sessions on their next request. It preserves records and does not automatically hide their public listings.
11. Saved category/location labels remain on historical reports even after administrator options change. Existing values remain available when editing those records.
12. Exports include filtered report summaries and no private claim evidence. Analytics submission-date filters use UTC; public browse date filters use the date lost/found.

## Non-functional requirements

Responsive layouts and two themes; CSRF protection; password hashing; per-route role/access checks; safe parameterized queries and HTML escaping; validated image re-encoding; local assets; migration-based upgrades; repeatable setup and tests; descriptive feedback; accessible labels/keyboard controls/reduced motion. No accessibility certification or high-load performance claim is made.

## Scope and acceptance

No AI recognition, payments, social publishing, native mobile app, university SSO or email delivery. Notifications are in-app. Default deployment is one local SQLite-backed instance. Acceptance requires the full report review → claim verification → handover sequence and effective permission/privacy checks, plus safe closure/reopening and preserved records on upgrade. See VALIDATION.md.
