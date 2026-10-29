# Changelog

## 1.0.0 — 2026-10-29

Initial runnable Python implementation of the supplied Campus Lost-and-Found Management System proposal.

### Added

- Flask application factory and modular account/report/claim/admin routes.
- Student registration, password changes, local operator recovery and CLI administrator creation.
- Lost and found reports, validated photographs, search, combined filters and pagination.
- Private ownership evidence, clarification conversation, reasoned reviews and one approved reservation per item.
- Separate physical-handover confirmation and confirmed-return statistics.
- Moderation, account access controls, in-app notifications and administrator activity history.
- Responsive teal/slate UI, local illustrations, dark/light themes and keyboard-friendly controls.
- Editable developer/team JSON and a README branding refresh command.
- Alembic migrations, random-password demo seed, explicit data reset, launch helpers and optional Docker files.
- Requirements/design/plan/risk/user/operations documentation and screenshots from the running app.
- Automated workflow/permission tests and GitHub Actions configuration.

### Boundaries

No AI matching, payments, external social publishing, native mobile applications, email service, or university SSO. No public-hosting, Docker-runtime, or load-capacity guarantee; exact verification is recorded in docs/VALIDATION.md.

## 1.1.0 — 2026-10-29

- Added clear Student and Administrator login choices, with separate role-checked routes.
- Administrator sign-in opens the admin console directly; student sign-in opens the student dashboard.
- Added one-time local administrator provisioning for the supplied ZIP, with only a password hash and no plaintext password in source or documentation.
- Preserved existing data when applying administrator setup to an earlier installation.
- Replaced technical About-page paragraphs with reporting, ownership verification and handover guidance.
- Updated the credits to Meazbah Mehedi and Monika, both Developer & Designer.
- Gave both developers equal configurable profile cards; refreshed the footer and README credits.
- Updated instructions, tests and screenshots for both login paths.

## 1.2.0 — 2026-10-29

- Replaced administrator access to student workflows with a dedicated management-only workspace and server-enforced restrictions.
- Added publication review for new/edited reports: pending, corrections requested, approved and rejected.
- Protected unpublished details and photographs; preserved existing published records during schema migration.
- Added private report decision history, student/admin notifications and structured activity entries with actor/state/reason/time.
- Added management dashboard, report queues, handover queue, collection arrangements, student history/access controls, filtered analytics and campus settings.
- Added CSV/PDF exports of filtered report summaries without private claim evidence; guarded CSV against spreadsheet-formula injection.
- Kept closure distinct from confirmed return, and prevented reopening from reactivating previous claims.
- Updated documentation, screenshots, migration coverage and management workflow tests.
- Corrected Windows PowerShell launch examples to `.\start.bat`.
