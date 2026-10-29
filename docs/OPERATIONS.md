# Configuration and operations

## Developer branding

Both developers are stored as equal entries under `team` in `config/developer.json`. Each has their own name, role, biography, photo and optional social links. Restart the server after changing it. Run `python scripts/sync_branding.py` to update README branding. Keep substantive README edits in `docs/README.template.md`, because the sync command regenerates README.md.

Project name changes apply to the sidebar, document titles, About page and footer. Some human-readable product copy and demo command text retain the CampusFind product wording. If fully renaming the product, review those strings as editorial content too. Developer names and social profile links are not hardcoded in application modules.

Logo and avatar paths must be relative to `campusfind/static/`. Optional social URLs must start with HTTP or HTTPS. Blank optional fields hide their links. The GitHub username and URL are editable separately so organizations can use a different display label. The file is not editable from the website.

## Runtime settings

Copy `.env.example` to `.env` to override local defaults. The app creates a private persistent random key in `instance/secret.key` if `SECRET_KEY` is blank. Do not commit the key or `.env`. Keep the same key across restarts to retain sessions. Changing it invalidates existing sessions.

The default database is `instance/campusfind.db`. Uploaded files are in `instance/uploads/`. The application uses one local instance; the upload directory and key must persist with its database. Schema changes require migrations; `init-db` applies existing migrations without dropping records.

The optional `DATABASE_URL` is an SQLAlchemy URI. Other database engines require their drivers and independent validation; only SQLite was checked for this release. Use a single application instance for the shipped setup.

## Account administration

```bash
python -m flask --app campusfind:create_app create-admin
python -m flask --app campusfind:create_app reset-password
```

Both prompt for credentials. Avoid passing real passwords as shell arguments. `seed-demo --password` exists for fictional local demos/test automation only; omit it to generate a random password.

The app applies a rolling limit of eight failed sign-ins per hashed email identity in 15 minutes. It is a local control rather than a complete anti-abuse service. Email addresses are normalized to lowercase. Student accounts do not prove campus affiliation. Administrators must verify ownership evidence independently and organize handover through a real campus process.

## Backup and restore

1. Stop the server.
2. Copy the whole `instance/` directory to a private backup location, preserving the database, uploads and key together.
3. Restart the server.
4. To restore, stop it again, replace the runtime directory with the backup, and start the same release/schema version. Upgrade migrations after restoring only when moving to a newer schema.

The ZIP and Git ignore runtime records intentionally. A release checkout initializes its database rather than containing student data. The ZIP additionally supplies a hashed one-time administrator setup in `instance/admin-bootstrap.json`; `setup_project.py` applies it using `configure-admin`, creates or updates the specified account, and deletes that file. It is ignored by Git, is not included in the Docker image, and is never read by public web routes. Re-running setup after the file has been consumed does not reset a changed administrator password. Screenshots included here show fictional data only.

## Reset and cleanup

`python -m flask --app campusfind:create_app reset-data` asks before deleting all users, reports, claims, messages, events, notifications, activity entries, login attempts, and stored JPG uploads in the configured app. It preserves migrations and developer configuration. `--yes` bypasses the prompt for disposable test environments. This is not a Git cleanup command; do not run it against data you need.

Before a Git push, check `git status --short`. Runtime data, .env, virtual environments, and caches are ignored. Documentation screenshots are intentional repository assets.

## Local server

`python run.py` starts Waitress with four worker threads. It binds to localhost by default. Another machine cannot reach localhost; changing `HOST` to `0.0.0.0` exposes the listener on network interfaces. Review hosting requirements before doing that on an untrusted network. A changed `PORT` must also be reflected in the browser address.

If port 5000 is busy, set `PORT=5050` in `.env`. If a form expires, refresh the page to get a new CSRF token. If the database table is missing, run `init-db` from the project root. If the demo seed refuses to run, the database already contains users; existing data is deliberately protected from silent replacement.

## Public hosting review

The supplied app is ready for local coursework and a repository demonstration. Public institutional operation needs HTTPS/reverse proxy setup, `COOKIE_SECURE=true`, verified university identity or SSO, institutional privacy/retention decisions, backup/monitoring, abuse controls, ownership/handover procedures and capacity testing. Do not enable Flask debug mode on a public host. Docker files are included for convenience; no cloud deployment is performed by this release.

The activity log is an application database record, not tamper-proof evidence against a trusted local operator. Uploaded visible-report photos are public. Administrators should remove inappropriate personal data from public reports through moderation and the institution's retention process. This version hides records rather than offering a full data-erasure/export service.

## Version 1.2.0 management and migrations

Run `python setup_project.py` without `--demo` to upgrade an existing installation. The migration preserves reports/claims/reviews/activity and backfills previously published reports as approved. New reports default to pending. Backup the complete instance directory with the server stopped before upgrading. Do not replace an existing database with a fresh one. In PowerShell use `.\start.bat` to restart.

The management-only administrator cannot submit/edit student reports or submit/reply/withdraw ownership claims. Old administrator-owned records remain preserved, and independent administrators can review eligible legacy claims. Campus categories/locations/collection instructions live in database settings; developer/designer identity remains in JSON. Historical labels and approved collection details are not silently rewritten when options change.

Report publication review and lifecycle are separate. Pending/correction/rejected records and images are restricted to author/admin. Closing/hiding cancels active claims; reopening preserves their prior decisions. Only physical-handover confirmation creates a new return timestamp. No timestamp is invented for older returned claims.

CSV/PDF exports are administrator-only and use the same report filters as the analytics page. They omit private claim evidence. CSV uses UTF-8 with a BOM and neutralizes leading spreadsheet-formula characters. PDF uses the locally bundled DejaVu Sans font; its license is included. Submission-date filters use UTC; event dates in public browsing are separate. Export actions are recorded in the activity log.
