# User guide

## First run

Use the README quick start. The supplied ZIP configures `admin@gmail.com` with your chosen password when you run `setup_project.py`. Choose **Login as Administrator** to open the admin console. Students choose **Login as Student** or register a student account. With `--demo`, setup also prints a separate random password for the fictional student/finder accounts. The ZIP contains no existing database.

## Student walkthrough

1. Open the app and choose **Create an account** from the sign-in page. Enter a name, email you control, and a password of at least 10 characters. This version does not verify email ownership.
2. Use **Report an item**. Select lost/found, a clear title, category, campus location and date. Add a useful description and optional photo. Do not publish card numbers, addresses, or documents with private information.
3. Publish the report. The item page shows its current state and generic history. Open **My dashboard** to find your reports later.
4. To find something, open **Browse items**. Search by name/description, select filters, and click **Apply filters**. Use date/sorting options when useful. All statuses are available by default; choose **Reported** or **Claim pending** for items still accepting claims.
5. If a found item appears to be yours, open its details and enter identifying evidence. Mention contents or markings not visible in the listing. Only you and administrators can read it.
6. Open your claim from the dashboard. If an administrator asks for clarification, respond in the private conversation. In-app notifications announce review updates.
7. When approved, coordinate physical pickup with the campus administrator. The report remains **Awaiting handover** until the administrator confirms the physical return.
8. To withdraw a pending/clarification claim, use **Withdraw claim** and confirm. You cannot submit a second claim on the same report; contact the administrator if you made a mistake.
9. To edit a report, open your own item page and choose **Edit report**. Editing is available for visible reports in **Reported** state without active claims. Your report type cannot change after publication.
10. Close an open report when it no longer needs attention. Active claims require administrator handling. Closing a lost report is separate from recording a verified handover on a found report.

## Administrator walkthrough

1. Select **Login as Administrator** and sign in with `admin@gmail.com` and your configured password. The admin console opens automatically.
2. The overview displays report totals, pending/clarification claims, confirmed returns, recent reporting activity, and category counts.
3. Open **Claim queue**, filter the status, and select **Review**.
4. Read private evidence and the conversation. Request more information when needed. State which details would help without revealing them in public.
5. Approve only when the identifying evidence is sufficient. The item becomes reserved and competing pending claims are rejected. Approval is recorded with your note.
6. Confirm **physical handover** only after the item reaches the verified owner. A review note is required for the record.
7. Use **Reports** to manage duplicate or inappropriate listings. **Hide & close report** removes an unreturned report from browsing and rejects active claims. **Restore visibility** makes it visible again but does not reopen it. Use **Reopen report** separately if appropriate. Returned reports cannot be reopened.
8. Use **Accounts** to disable/re-enable a student. Disabling blocks future requests from existing sessions and prevents sign-in. It does not remove their public reports; moderate those separately if needed.
9. Open **Activity log** for administrator review/moderation/access actions. Public report histories contain generic lifecycle labels; they do not disclose claim evidence.

An administrator cannot review a claim they submitted or a claim on their own report. Create a second administrator through the local CLI for independent review when necessary.

## Other controls

- The top-right theme button switches light/dark mode and saves the preference in this browser.
- On mobile, the menu button opens navigation. Escape or tapping outside closes it.
- Profile settings let you edit your name and change your password.
- The notification page has **Mark all as read**. Reading the page alone does not mark them read.
- Dates of loss/finding are date-only. Activity timestamps are displayed in UTC.

## Common questions

**Can the finder see my ownership proof?** No, unless they are also an administrator. Ordinary report authors cannot read claim evidence.

**Can I message the finder directly?** No. This version uses administrator-mediated verification and handover rather than publishing contact details.

**Why do some pictures say Illustration?** They are local fallback artwork for reports without a photo, never evidence of the actual item.

**Why does the demo include these names/items?** They are fictional examples. The team/developer section comes from the separate configuration file, not from student demo accounts.

**Forgot the password?** A trusted local operator runs `python -m flask --app campusfind:create_app reset-password`. There is no email reset service in this release.
