#!/usr/bin/env python3
"""Render tools/LABELS.md from tools/labels.json.

Split out of build_labels.py so the prose can be edited without re-running the
classifier. Usage: python3 tools/render_labels_md.py [--labels tools/labels.json]
"""

import json
import os
import sys

PREAMBLE = """# Dev pseudo-labels — evidence-type combinations

**What this is.** The development set has no answers. This file is the only
self-assessment baseline we have: it groups all 4,000 dev cases by the
*combination of evidence types on file* (134 combinations in total, 25-37 per
institution), then records, for each combination, what the institution's
`POLICY.md` supports and how many cases sit there.

**How to read an entry**

| field | meaning |
|---|---|
| `signature` | the exact set of evidence types on file for the case |
| `core_signature` | the same set with the three noise types removed (see below) |
| `advice` | suggested verdict and reason_code for the combination |
| `rule_advice` | the same, split by which alerts the cases in that combination raised |
| `basis` | one sentence: the ground the advice rests on |
| `heuristic_mix` | how the content-aware classifier scored the combination's cases; calibration only, never ground truth |
| `alt` | the runner-up reading, shown when it covers at least 15% of the combination |
| `confidence` / `needs_review` | how settled the reading is, and whether a human should look |
| `review_flags` | the specific question a reviewer has to answer |

**Three types carry no meaning on their own.** `due_diligence_summary`,
`proof_of_address` and `contact_note` appear in almost every case: the first two
only prove identity, and all 785+824+835+900 contact notes are one of six
routine admin skeletons (mobile number change, address check, standing order
help, charges query, lost card, paper statements). Combinations that differ only
by those types are the same shape. Judge a case on its core signature.

**Why the same documents can give different verdicts.** `support_chat`,
`staff_note`, `device_export`, `customer_email`, `bank_statement`, `email` and
`receipt` are dual-use. A support chat can be a mother's hospital bill or
"clients pay into my account and I send it on". A branch note can be a routine
deposit or a customer asking whether deposits under the threshold are
aggregated. A device export with one customer is context; with four customers on
one device it is account misuse. Read the text, not the type.

**Stance.** The labels are deliberately conservative, because the costs are
asymmetric: a wrong CLOSE costs 10, a needless RFI 3, a needless escalation 2-3,
and CONTRACT.md §5 says unexplained activity escalates rather than closes. So:

- a combination with no document that answers the alert and no account from the
  customer is labelled `ESCALATE / ESC_UNEXPLAINED_FUNDS`, even where an RFI
  might score slightly better if the customer turns out to have the paperwork;
- a combination where the customer has given an account in chat but no document
  is labelled `RFI`, because that is the policy's "no suspicion yet, one
  document would settle it" case;
- a list match on one detail alone, with nothing on file either way, is an RFI
  (POLICY.md says so explicitly), never a CLOSE.

**What is *not* evidence.** `previous_reviews.jsonl` is all CLOSE and is a
distractor: an earlier review covers only what it describes, so it never
explains new or larger activity and no label here rests on it.
"""

METHOD = """
## How the labels were built

1. Every dev case is reduced to `(institution, sorted evidence types, alerts)`.
   That is 134 distinct combinations for 4,000 cases.
2. Each evidence type is classified from its text: noise (identity/admin),
   explanatory, suspicious, or dual-use. 54 distinct type names exist across the
   four institutions; 27 in the bank alone.
3. Each alert rule is then matched against the documents that can answer it, per
   the rule table in that institution's `POLICY.md`. A case is CLOSE only when
   *every* alert it raised is answered by a document (CONTRACT.md §5: one
   unexplained alert keeps the case open).
4. Where a document's meaning depends on its wording, the wording decides, with
   explicit patterns: `send it on` / `payments assistant` / `invest for them`
   (mule or pass-through), `aggregat` / `below the £` / `instalments` (structuring
   intent), `unwilling` / `refused` (non-cooperation), a device export naming more
   than one customer (account misuse), and a gift letter whose giver's date of
   birth equals the internal-list entry's (the listed party itself).
5. `tools/case_labels.jsonl` holds the resulting per-case label, its ground
   sentence, its confidence and its review flags. `tools/labels.json` is the
   same information aggregated by combination; this file is its readable view.

Coverage: 4,000/4,000 cases and 134/134 combinations. Regenerate with
`python3 tools/build_labels.py && python3 tools/render_labels_md.py`.
"""


def cell(text, width):
    text = str(text)
    return text if len(text) <= width else text[:width - 1] + "…"


def main(argv):
    path = "tools/labels.json"
    args = list(argv[1:])
    i = 0
    while i < len(args):
        if args[i] == "--labels":
            i += 1
            path = args[i]
        else:
            sys.stderr.write("render_labels_md: unknown argument %s\n" % args[i])
            return 2
        i += 1

    with open(path, "r", encoding="utf-8") as fh:
        labels = json.load(fh)

    out = [PREAMBLE, METHOD]

    totals = labels["totals"]
    out.append("## Coverage\n")
    out.append("| institution | cases | combinations | CLOSE combos (cases) | RFI combos (cases) "
               "| ESC combos (cases) | need review |")
    out.append("|---|---|---|---|---|---|---|")
    grand = {"cases": 0, "signatures": 0, "close_entries": 0, "rfi_entries": 0,
             "esc_entries": 0, "close_cases": 0, "rfi_cases": 0, "esc_cases": 0,
             "review_entries": 0}
    for name in sorted(totals):
        t = totals[name]
        for key in grand:
            grand[key] += t[key]
        out.append("| %s | %d | %d | %d (%d) | %d (%d) | %d (%d) | %d |" % (
            name, t["cases"], t["signatures"], t["close_entries"], t["close_cases"],
            t["rfi_entries"], t["rfi_cases"], t["esc_entries"], t["esc_cases"],
            t["review_entries"]))
    out.append("| **total** | %d | %d | %d (%d) | %d (%d) | %d (%d) | %d |" % (
        grand["cases"], grand["signatures"], grand["close_entries"], grand["close_cases"],
        grand["rfi_entries"], grand["rfi_cases"], grand["esc_entries"], grand["esc_cases"],
        grand["review_entries"]))
    out.append("")
    share = 100.0 * grand["close_cases"] / grand["cases"]
    out.append("CLOSE covers %.1f%% of dev cases, RFI %.1f%%, ESCALATE %.1f%%."
               % (share, 100.0 * grand["rfi_cases"] / grand["cases"],
                  100.0 * grand["esc_cases"] / grand["cases"]))
    out.append("")

    for name in sorted(labels["institutions"]):
        block = labels["institutions"][name]
        alias = block["type_aliases"]
        out.append("## %s — %d cases, %d combinations\n" % (name, block["cases"],
                                                            block["signatures"]))
        out.append("| # | cases | rules | advice | 2nd | conf | review | core evidence | basis |")
        out.append("|---|---|---|---|---|---|---|---|---|")
        for entry in block["entries"]:
            rules = ", ".join(sorted(entry["rules"]))
            core = "+".join(alias.get(t, t) for t in entry["core_signature"]) or "(noise only)"
            alt = entry.get("alt")
            alt_text = ("%s/%s %d%%" % (alt["verdict"], alt["reason_code"],
                                        round(alt["share"] * 100)) if alt else "—")
            review = "yes" if entry["needs_review"] else ""
            out.append("| %s | %d | %s | %s/%s | %s | %s | %s | %s | %s |" % (
                entry["id"].split("#")[1], entry["cases"], rules,
                entry["advice"]["verdict"], entry["advice"]["reason_code"], alt_text,
                entry["confidence"], review, core, cell(entry["basis"], 110)))
        out.append("")

    out.append("## Needs a human decision\n")
    out.append("These combinations are flagged because the policy does not settle "
               "them from the files alone. Each line is the question a reviewer has "
               "to answer.\n")
    for name in sorted(labels["institutions"]):
        block = labels["institutions"][name]
        flagged = [e for e in block["entries"] if e["needs_review"]]
        if not flagged:
            continue
        out.append("**%s**\n" % name)
        out.append("| cases | advice | core evidence | question |")
        out.append("|---|---|---|---|")
        for entry in flagged:
            core = "+".join(block["type_aliases"].get(t, t)
                            for t in entry["core_signature"]) or "(noise only)"
            question = " ".join(entry["review_flags"]) or (
                "the combination splits %.0f%% / %.0f%% between readings"
                % (100 * entry["share_on_advice"],
                   100 * (1 - entry["share_on_advice"])))
            out.append("| %d | %s/%s | %s | %s |" % (
                entry["cases"], entry["advice"]["verdict"],
                entry["advice"]["reason_code"], core, cell(question, 220)))
        out.append("")

    out.append("""## Known soft spots in this baseline

1. **List matches where the listed officer resigned.** In 119 cases the register
   shows the listed director resigning one day before the payment, with a new
   controller appointed. The labels close these as `LIST_MATCH_DIFFERENT_PARTY`
   because at the payment date the payee was no longer controlled by the listed
   party. If the intended reading is "the listed party was the controller until
   yesterday", these are `ESC_LISTED_PARTY` instead. Watch this family first.
2. **Higher-risk corridor with business documents.** Where a supplier invoice
   covers a payment to a higher-risk country, the labels close it as
   `INVOICE_MATCHES`. If the test set treats an undeclared corridor as
   suspicious regardless of the invoice, these should escalate.
3. **Mule vs pass-through.** The verdict (ESCALATE) is solid where the chat says
   the customer forwards other people's money; the code choice
   (`ESC_MULE_ACTIVITY` for bank and e-money, `ESC_PASS_THROUGH` for investment)
   is a judgement.
4. **Zero-document combinations** (179 bank, 208 e-money, 215 investment, 218
   payments/FX cases). Nothing explains the alert. `ESC_UNEXPLAINED_FUNDS` is the
   contract's fallback (§5), but if the hidden set expects an RFI for these, the
   cost is 2-3 per case rather than 10. This is the largest single block of dev
   cases and the largest single risk in either direction.
5. **`previous_reviews` is ignored everywhere.** It is all CLOSE and covers only
   what it describes; using it as an explanation is the trap the policy warns
   about.
""")

    target = os.path.join(os.path.dirname(path), "LABELS.md")
    with open(target, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print("wrote %s" % target)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
