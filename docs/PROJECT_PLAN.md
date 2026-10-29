# Project plan and risk register

This is a suggested planning baseline aligned with the semester proposal, not a claim about time already spent by individual team members. Replace relative weeks with the instructor's actual dates.

## Work breakdown structure

| WBS | Work package | Main output | Proposed role |
|---|---|---|---|
| 1.1 | Confirm users and scope | Proposal baseline and exclusions | Project Coordinator |
| 1.2 | Gather reporting/claim needs | Requirements and acceptance rules | Requirements Lead |
| 1.3 | Review privacy and verification needs | Evidence access policy | Requirements Lead |
| 2.1 | Define application and database structure | Architecture and ER model | System Design Lead |
| 2.2 | Model report/claim workflows | State and workflow diagrams | System Design Lead |
| 2.3 | Design responsive pages | UI layouts and navigation | System Design Lead |
| 3.1 | Implement authentication and configuration | Accounts, developer JSON, factory | Shared implementation |
| 3.2 | Implement reports/search/uploads | Reporting and browsing module | Shared implementation |
| 3.3 | Implement claims/returns | Review and handover workflow | Shared implementation |
| 3.4 | Implement moderation/dashboard | Admin console and notifications | Shared implementation |
| 4.1 | Validate permissions and transitions | Automated workflow tests | Whole team |
| 4.2 | Review UI and usability | Desktop/mobile screenshots | Whole team |
| 4.3 | Prepare README and user instructions | Repository documentation | Documentation and Scheduling Lead |
| 4.4 | Review schedule and risks | Updated risk/progress records | Project Coordinator and Documentation Lead |
| 5.1 | Demonstrate application | Student/admin walkthrough | Whole team |
| 5.2 | Prepare submission and presentation | Final report/slides per teacher instructions | Whole team |

## Suggested six-week schedule

| Week | Activities | Dependency | Completion check |
|---|---|---|---|
| 1 | Scope, users, requirements, acceptance rules | Proposal | Team agrees on FR/NFR baseline |
| 2 | Data model, state workflow, UI design | Requirements | Design matches all four core features |
| 3 | Accounts, reports, search and image processing | Design | Student can publish and find reports |
| 4 | Private claims, reviews, moderation, notifications | Core records | Full verified return succeeds |
| 5 | Tests, responsive review, documentation | Complete workflows | Permission and transition checks pass |
| 6 | User acceptance, packaging, rehearsal | Validation | Team can demonstrate from a clean setup |

The implementation is supplied in this release. The team should still study, review, adapt and document it according to the course's submission rules. The schedule can be used for review and learning rather than claiming all development remains outstanding.

## Risk register

| ID | Risk | Likelihood / impact | Mitigation | Owner |
|---|---|---|---|---|
| R1 | Requirements change repeatedly | Medium / Medium | Maintain baseline, review changes against exclusions | Requirements Lead |
| R2 | Unequal task distribution | Medium / Medium | Assign small named tasks and review progress weekly | Coordinator |
| R3 | Missed deadlines | Medium / High | Set milestones and reserve final validation time | Documentation Lead |
| R4 | Incorrect person receives item | Medium / High | Private proof, independent admin review, separate handover | Requirements Lead |
| R5 | Sensitive details leaked in reports | Medium / High | Public-photo guidance, evidence access checks, moderation | Design Lead |
| R6 | Duplicate claims or conflicting approvals | Medium / High | Unique claim constraint, conditional item reservation, tests | Implementation team |
| R7 | Invalid/oversized photo upload | Medium / Medium | Decode, cap size/pixels, re-encode with safe filename | Implementation team |
| R8 | Local data lost | Medium / High | Stop server and back up complete instance directory | Local operator |
| R9 | Repository contains secrets or demo accounts | Medium / High | Exclude runtime directory and .env; seed only on request | Documentation Lead |
| R10 | Scope expands to AI/mobile/payments | Medium / High | Keep proposal exclusions and record future ideas separately | Coordinator |
| R11 | Public deployment exceeds prototype controls | Medium / High | Deployment review, HTTPS, verified identity, capacity tests | Local operator |
| R12 | Team cannot explain generated implementation | Medium / High | Walk through modules and workflows; run tests together | Whole team |

## Progress-report template

Record date, participants, completed WBS tasks, evidence (commit/test/screenshot), blockers, decisions, next tasks and owner. Do not invent completed work or contributions. Each milestone review should confirm scope, risks, acceptance results, and outstanding changes.

## Suggested final presentation

Problem and users → proposal scope → report/search demo → private claim and verification demo → handover distinction → architecture and database → test evidence → risks and limitations → learning and future improvements. This file supplies planning material; it is not a separate presentation deck or a completed academic final report.
