# Release validation and manual acceptance

## Verified for 1.1.0

- **44 automated test cases passed** on Python 3.12 with SQLite, using temporary databases and real CSRF tokens.
- New release checks cover visible login choices, correct-role sign-in, rejection of students at administrator login, rejection of administrators at student login, tampered role fields, administrator CSRF/redirect protection, the revised About credits, and one-time local administrator setup without data loss.
- The suite exercises public and protected pages, registration role boundaries, duplicate email handling, student/admin permissions, the full claim→clarification→approval→handover flow, duplicate/self claims, private evidence, competing claims, invalid returns, withdrawal, moderation, hidden images, account disablement, failed-login throttling, safe login redirects, uploads, future dates, filters, notifications, migrations, demo seeding and explicit data reset.
- Browser checks ran against a local Waitress instance using Chromium 153. The actual interface was used to sign in/out, search, publish a report, cancel/confirm closing, mark notifications read, approve a claim and confirm physical return.
- The theme was switched and retained after a reload. Mobile navigation opened and closed with keyboard Escape.
- Forty-one page/viewport checks covered widths **320, 390, 768, 1024, 1440 and 1920 pixels**, with no detected document-level horizontal overflow or broken visible images in those checks. Mobile checks included overview, browse, about, sign-in, registration and item details. Administrative and claim pages were checked at desktop size.
- Browser checks reported **no JavaScript page errors or console errors**.
- Screenshots were captured from the running application with fictional demo records and visually inspected for overview, dark theme, dashboard, admin, reporting, both login screens, the revised About page, and mobile login layout.
- A clean source copy was bootstrapped into a new virtual environment using `setup_project.py --demo`: exact dependencies installed, migrations applied, and fictional accounts/reports were created successfully.
- Python syntax compilation and Ruff's configured correctness checks passed. JavaScript syntax was checked with Node.

The screenshots can show slightly different counts because a report and a return were created during the browser workflow. They are real application states rather than manually edited mockups.

## Scope of verification

The implementation and tests were checked in this Linux environment. Windows launch instructions and Docker files are provided; Windows execution, Docker builds, public deployment, cross-browser/device certification, institutional security review and load testing were not performed here. GitHub Actions is configured for Python 3.11 and 3.12; its hosted run will occur when the repository is pushed, and is not claimed as already completed.

WTForms 3.3 emits a deprecation notice about tuple-based choice definitions; the locked release uses the working API. The compatible range caps WTForms below the announced removal boundary. This does not affect the passing tests.

## Reproduce automated checks

```bash
python -m pip install -r requirements-lock.txt -r requirements-dev.txt
python -m pytest -q
python -m compileall -q campusfind scripts
```

Tests do not use the operator's runtime database. Do not point test configuration at a database containing real records.

## Manual acceptance checklist

| Check | Expected result |
|---|---|
| Start from a fresh extracted folder | Database initialized, server opens on localhost |
| Run setup on the supplied ZIP | Configured administrator created; one-time setup consumed |
| Choose Login as Administrator | Administrator account opens admin console directly |
| Choose Login as Student | Student account opens personal dashboard |
| Try the wrong login option | No session created; correct option explained |
| Create another administrator using CLI | Account can enter admin console |
| Register a student | Student cannot enter admin routes |
| Submit a lost report | Details appear with Reported state |
| Submit a found report and valid photograph | Image renders; metadata is stripped in stored JPEG |
| Upload a fake PNG, oversized image, or unsupported file | Validation feedback; no report published with that file |
| Select a future event date | Field error shown |
| Combine query, category, location, status, dates | Only matching visible reports appear |
| Open a no-match search | Helpful empty state and reset action |
| Claim a found report | Private evidence saved; report becomes Claim pending |
| Open another user's claim as a student | Access denied |
| Submit an own/duplicate/inactive-item claim | Request rejected |
| Administrator requests clarification | Claimant receives a message and can reply |
| Administrator approves | Item reserved; awaiting handover, not returned |
| Confirm physical handover | Item/claim Returned; return statistics update |
| Try to confirm a pending claim as returned | Action rejected |
| Withdraw a pending claim | Claim withdrawn; report refreshed appropriately |
| Hide an open report with claims | Report closed/hidden; active claims rejected |
| Fetch hidden-report image as a visitor | Not found |
| Restore hidden report | Visible, still Closed until explicitly reopened |
| Disable a student | Their next authenticated request loses access |
| Edit developer JSON and restart | About/footer/sidebar branding refreshes |
| Run branding sync | README developer/team details refresh |
| Toggle theme and reload | Theme preference retained |
| Use 390 px mobile navigation | Navigation opens; Escape/outside click closes it |
| Stop/restart server | Existing records remain available |

## Demonstration script

1. Run the empty-database demo seed and save the printed password.
2. Show the overview and filters as a visitor.
3. Sign in as the student and show their reports and private claims.
4. Use the found-item report to explain evidence verification.
5. Sign in as the administrator, inspect the claim queue, and request clarification or approve.
6. Explain the distinction between approval and physical return; confirm handover only in the fictional demonstration.
7. Show the updated item history, notifications and activity log.
8. Show `config/developer.json` and explain how it controls branding separately from program logic.
