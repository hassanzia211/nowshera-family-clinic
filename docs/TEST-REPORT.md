# Verification report

## Automated backend results

Command: `python -m pytest -q`

**16 tests passed in 21.13 seconds** in the build environment (Python 3.12, Linux). Tests cover the ten assignment scenarios at the API/domain level plus extra race, security, and failure-path checks. Temporary databases and a controlled clinic clock are used for repeatability.

| Assignment case | Verified coverage | Outcome |
| --- | --- | --- |
| 1. Book and confirm | Pending creation, doctor confirmation, correct recipient and local email output | Passed locally; real inbox delivery needs SMTP |
| 2. Add doctor/dashboard | Invitation, one-use password setting, sign-in, Monday 09:00–11:00 produces four slots, persistent per-doctor Pending total | Passed locally; real invitation email needs SMTP |
| 3. Double booking | Same doctor slot, patient simultaneous doctors, two concurrent competing requests | Passed |
| 4. Outside hours/full day | Direct API invalid hours, off-grid minutes, fully booked day shows zero slots | Passed |
| 5. Past/inactive/early completion/leave | All blocked correctly; leave cancels confirmed appointment and queues email | Passed locally |
| 6. Cancel/reschedule | Released slot rebooked, rescheduled status Pending, original retained on conflict, exact 2-hour boundary | Passed |
| 7. Invalid hours/leave | Reversed/overlapping/off-grid hours and past leave denied; adjacent hours accepted | Passed |
| 8. Wrong role | Patient cannot add doctor/confirm; doctor cannot confirm another doctor's appointment | Passed |
| 9. Privacy | Other patient/doctor denied; admin denied note and no note text leaked in generic APIs; owners can read | Passed |
| 10. Automations/persistence | Tomorrow reminder once, expired Pending cancellation once, repeated runs and refresh retain state | Passed locally; mobile and inbox checks recorded separately |

Extra coverage: CSRF, anonymous access, session logout, inactive-doctor sessions, registration role escalation, expired/reused invitations, failed-reschedule rollback, and SMTP adapter invocation with a fake provider.

## What these results do not claim

- No external SMTP account was provided, so actual email inbox receipt is not certified. Local `.eml` output and an in-process fake SMTP transport were verified.
- Windows launch instructions are supplied; the runtime tests were executed on Linux, not the user's laptop.
- This is coursework verification, not a production security audit or healthcare compliance certification.

## Reproduce and finish the real-email checks

Run the Windows launcher, configure `.env` for SMTP, restart, then repeat cases 1, 2, 5, 6 and 10 with real addresses. Keep the server open for the background worker. Check the recipient inbox and spam folder. Run `manage.py automations` twice to demonstrate idempotent normal operation.

For a reminder, confirm an appointment dated tomorrow in Pakistan time. For expiry/completion cutoffs, use the automated test suite or wait for the actual appointment time; the application intentionally has no rule-bypass endpoint.

## Browser verification

A real headless Chromium browser verified the desktop interface at 1440 × 1000 and mobile interface at 390 × 844:

- Patient sign-in → doctor selection → free slot → Pending request.
- Page refresh → the upcoming appointment remains present.
- Doctor sign-in → appointment details → Confirmed.
- Doctor working-hours screen renders.
- Admin overview renders with the confirmed total.
- Mobile menu → doctor management → create/invite a doctor.
- No JavaScript page errors; no horizontal document overflow at mobile size. Wide tables scroll inside their cards.

Recorded result: **PASS**. Screenshots are included in the downloadable project ZIP. Real SMTP inbox delivery remains the outstanding environment-dependent acceptance step.
