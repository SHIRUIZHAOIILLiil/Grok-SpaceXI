# system/ — how this decides

Entry point: `system/run <institution folder> <output file>`. It reads only that folder and writes
only that file. Python 3 standard library; nothing to install.

## How it decides

`main.py` loads `cases.jsonl` and `alerts.jsonl`, sorts cases by id, builds a feature dict per case
(`features.py`) and hands it to `decide.decide` (`decide.py`). The order is fixed:

1. **Suspicion first** — eight checks: structuring, mule recruitment, device sharing, dissolved
   counterparty, list match (TM22), invoice/goods mismatch, linked payouts, payment-file risk. A hit
   returns immediately: once there is suspicion the policy says escalate, and never ask the customer.
2. **Close grounds** — eleven grounds, each requiring a document whose amount sits inside 72–112% of
   what the alerts measured, and each ground must answer **every** rule that fired in the case.
3. **Fallback** — a specific escalation code when the clues point at one; RFI when the case is
   otherwise unremarkable and one named document would settle it; otherwise
   `ESCALATE / ESC_UNEXPLAINED_FUNDS`. The system never guesses a close.

Every threshold lives in `policy/<institution>.json` with the `POLICY.md` sentence it came from —
the four institutions differ (a £9,000–9,999 split band at the bank is £800–999 at the e-money firm).
Documents are matched by a template fingerprint (`evidence.py`): amounts, dates, numbers and names
are replaced by placeholders, so the same sentence pattern matches unseen cases from the same
generator. Unknown patterns fall through to escalation.

Output is one JSON line per case: `case_id`, `alert_ids`, `verdict`, `reason_code`, `reason`,
`evidence`. The reason names an amount, a date and the document IDs it relied on.

## Which model it uses

**None, by default.** The verdict is a deterministic function of the case, which is what makes five
runs byte-identical.

A model is used only for one parsing gap, when `OPENROUTER_API_KEY` is set: 46 of 140 gift letters
state a birth date in a sentence rather than a field, so the model is asked for a **verbatim quote**,
the quote is checked character for character against the document, and the local parser reads it. A
quote that is not in the document changes nothing. An optional second read of escalations
(`second_opinion.py`) requires `HACKATHON_LLM_PROMOTE=1`; measured on 4,000 cases it promoted 0 of
236 fallback cases, so it is off.

Without a key no call is made and the output is byte-identical to a run that never imports the
module.

## How long a run of 200 cases takes

Measured on this container (Linux, Python 3.14), 1,000 cases per institution:

| Institution | 1,000 cases | 200 cases (proportional) |
|---|---|---|
| bank | 1.9 s | ≈ 0.4 s |
| payments_fx | 1.5 s | ≈ 0.3 s |
| emoney | 1.2 s | ≈ 0.2 s |
| investment | 0.8 s | ≈ 0.2 s |

Cost: **$0** — no network, no API calls in the decision path. Peak memory is the size of one
institution folder.
