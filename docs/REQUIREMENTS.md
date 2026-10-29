# Requirements and proposal traceability

Version: 1.1.0. Scope baseline: the supplied Campus Lost-and-Found Management System semester proposal. This release implements the proposed application in addition to its planning deliverables. Requirements below distinguish proposal features from supporting additions.

## Users

**Visitor:** searches visible reports and reads item details. **Student:** registers, reports items, submits private ownership claims, tracks progress, and manages their own account. **Administrator:** reviews evidence, moderates reports, manages student access, and records returns. A trusted local operator creates administrator accounts and performs database maintenance.

## Functional requirements

| ID | Requirement | Proposal mapping | Implementation |
|---|---|---|---|
| FR-01 | Submit a lost report with title, description, location, date, category and optional photo | Feature 1 | Report form and item records |
| FR-02 | Submit a found report with the same structured details | Feature 2 | Report form and item records |
| FR-03 | Search name/description and combine category, location and date filters | Feature 3 | Browse page with sorting and pagination |
| FR-04 | Submit ownership evidence for a found item | Feature 4 | Private claim form |
| FR-05 | Administrator reviews, requests clarification, approves or rejects with a reason | Feature 4 | Claim conversation and review actions |
| FR-06 | Track item and claim status | Feature 4 | Dashboard, badges, report history and notifications |
| FR-07 | Confirm physical return after approval | Administrator requirements | Separate handover action |
| FR-08 | Hide duplicate/inappropriate/invalid listings | Administrator requirements | Hide-and-close moderation, preserving history |
| FR-09 | Register, log in, log out, edit profile and change password | Supporting addition | Student accounts and roles |
| FR-10 | Notify students of claim and moderation changes | Supporting addition | Per-user in-app notification records |
| FR-11 | Display administrative statistics and action history | Supporting addition | Charts and audit records |
| FR-12 | Keep developer/team branding editable in one file | User request | config/developer.json and README sync command |

## Business rules

1. Public registration always creates a student. Posted role fields have no effect.
2. A claim belongs to one student and one found-item report. Each student can submit one claim per report, including after rejection/withdrawal; this preserves the review history and prevents repeat spam. A mistaken claim requires administrator assistance or a new report when appropriate.
3. Students cannot claim their own reports, or claims on lost/hidden/closed/returned/reserved items.
4. Private evidence and claim messages are accessible only to the claimant and administrators, including when the public report is hidden. Report authors cannot inspect someone else's evidence.
5. Only one claim can reserve an item. Approval rejects competing pending/clarification claims. A conditional database update guards reservation.
6. Approval means awaiting handover, never an automatic physical return.
7. Handover can be confirmed only for the approved claim assigned to that item.
8. An administrator cannot review a claim that they submitted or a claim attached to their own report.
9. Students may edit/close only their own visible open reports without active claims. Type cannot change after publication.
10. Hiding an unreturned report closes it and rejects active claims. Restoring visibility does not automatically reopen a closed report. Returned items retain their returned state even if hidden.
11. Administrator accounts cannot be disabled from the web screen. Disabled student sessions lose access on their next request. Existing reports remain for continuity until moderated separately.
12. Optional photos are decoded, resized and re-encoded as JPEG, with metadata stripped. Photos on visible reports are public; users must avoid personal documents/numbers in them.

## Non-functional requirements

| ID | Requirement | Acceptance approach |
|---|---|---|
| NFR-01 | Python 3.11+ and a reproducible local setup | Dependency lock, migration and CLI checks |
| NFR-02 | Responsive desktop/mobile layout | Screenshot and overflow checks at desktop/mobile sizes |
| NFR-03 | Light/dark themes with preference persistence | Browser theme toggle and reload check |
| NFR-04 | Permission checks on every protected route | Unauthorized request tests |
| NFR-05 | CSRF on all state-changing web requests | Missing-token rejection tests |
| NFR-06 | Durable records across restarts | SQLite storage; operator backup procedure |
| NFR-07 | Modular maintainable source | Blueprints, service functions, models, readable templates |
| NFR-08 | No paid API or external assets needed at runtime | Local CSS, JavaScript and SVG assets |
| NFR-09 | Meaningful failure feedback | Invalid form, upload, permission and not-found cases |
| NFR-10 | Basic accessibility | Form labels, skip link, keyboard controls and reduced motion |

Performance is suitable for local teaching/demo use; no latency or concurrent-user capacity is asserted without measurements. An accessibility certification is not claimed.

## Exclusions and assumptions

The proposal excludes AI matching/image recognition, rewards/payments, automatic social publishing, and dedicated mobile applications. This release also omits SSO, verified campus membership, email verification, password-reset email delivery, location maps, and real-time messaging. Students coordinate handover through the administrator rather than public contact details.

Campus locations are generic labels. Edit `LOCATIONS` in `campusfind/__init__.py` to suit a real campus. Developer identity is configurable independently in JSON. The app does not imply official university endorsement or ownership of its hosting infrastructure.

## Acceptance

A release is acceptable when a student can report/search an item, submit a private claim, respond to clarification, and receive an administrator-confirmed return; access restrictions and moderation remain effective throughout. See VALIDATION.md for test evidence and the manual checklist.
