# Architecture

The submitted artefact is a command, not a service:

```
system/run <institution folder> <output file>
```

The grader calls it once per institution, from inside `system/`, with absolute paths, five times,
on a machine we do not control. Everything below is shaped by that.

## Layers

```
cases.jsonl ─┐
alerts.jsonl ├─▶ main.py ─▶ features.build_case ─▶ decide.decide ─▶ emit.to_line ─▶ out.jsonl
evidence/    │                  │                        ▲
customers    │                  ▼                        │
transactions ├──────────▶ evidence.Index                 │
internal list┘            (documents, tags, lookups) ────┘
```

| File | Lines | Job |
|---|---|---|
| `system/run` | 6 | POSIX shim: resolves its own directory, execs `main.py` |
| `system/main.py` | 67 | Reads one folder, sorts cases by id, decides, writes the file |
| `system/features.py` | 589 | Assembles the feature dict; resolves TM22 list matches |
| `system/evidence.py` | 593 | Document index, template fingerprints, 35 semantic tags, parsers |
| `system/decide.py` | ~1,430 | The decision table: 8 suspicion checks, 11 close grounds, fallback |
| `system/emit.py` | 22 | Fixed field order, single-line reasons, de-duplicated IDs |
| `system/policy/*.json` | 4 files | Every threshold, with the `POLICY.md` sentence it came from |
| `system/extract.py` | 145 | Optional model reader for prose dates (off without a key) |
| `system/second_opinion.py` | 115 | Optional re-read of escalations (off unless `HACKATHON_LLM_PROMOTE=1`) |

## One case, end to end

1. **Load.** `main.py` reads `cases.jsonl` and `alerts.jsonl`, groups alerts by case and sorts cases
   by `case_id`, so the output order never depends on the filesystem.
2. **Build.** `features.build_case` picks the customer row, the transactions inside the review
   window, and every document on file for that customer. `evidence.Index` parses each document once:
   amounts, dates, name tokens, addresses, and a *template fingerprint* — the text with amounts,
   dates, numbers and capitalised names replaced by placeholders. Documents are then tagged
   (35 tags, e.g. `invoice_matches_payment`, `inheritance`, `mule_recruitment_chat`), and the tag
   declares which verdict and reason code it can support.
3. **Decide.** `decide.Case` derives the numbers the table needs (focus amount, declared baseline,
   multiple, paid-out share, country, held payment). Then, in this order:
   - eight **suspicion checks** — structuring, mule recruitment, device sharing, dissolved
     counterparty, list match, invoice/goods mismatch, linked payouts, payment-file risk;
   - eleven **close grounds** — business records, collection, refund, group company, third party,
     returning customer, own account, invoice, documented event, within profile;
   - **fallback** — a specific escalation code if the clues point at one, else RFI when a single
     document would settle it, else `ESC_UNEXPLAINED_FUNDS`.
4. **Emit.** One JSON line per case: `case_id`, `alert_ids`, `verdict`, `reason_code`, `reason`,
   `evidence`. The reason names an amount, a date and the document IDs it rests on.

## Why suspicion comes first

A close ground only fires if nothing above it fired. This is not cosmetic: several cases contain a
real invoice *and* a fraud report from the sending bank. If the close grounds ran first, a fake
invoice would close a mule account. The order encodes the policy sentence "once there is suspicion,
escalate rather than ask the customer".

## Determinism

Reproducibility is 20% of the score, so it is enforced structurally rather than by testing alone:

- every collection that affects output is `sorted()` or comes from a file in file order;
- no `random`, no `time.time()`, no `datetime.now()`, no threads, no network in the decision path;
- the model layer is off unless a key is present *and* a flag asks for it; without both, output is
  byte-identical to a run that never imports it;
- `tools/repro.sh` runs five times across four institutions and compares bytes.

## Failure behaviour

| Situation | What happens |
|---|---|
| Unknown document template | `tag = unknown`, no close ground claims it, case escalates |
| Missing document body | Index returns empty text; the case cannot close on it |
| List entry has no date of birth | Match stays `unresolved` → RFI, never a close |
| Model call fails | First transport error disables the model for the run |
| Model not configured | Zero calls, byte-identical output |
| Case missing from output | Cannot happen: one line per row in `cases.jsonl`, written in order |
