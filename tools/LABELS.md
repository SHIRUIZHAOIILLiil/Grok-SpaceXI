# Dev pseudo-labels — evidence-type combinations

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
and docs/CONTRACT.md §5 says unexplained activity escalates rather than closes. So:

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


## How the labels were built

1. Every dev case is reduced to `(institution, sorted evidence types, alerts)`.
   That is 134 distinct combinations for 4,000 cases.
2. Each evidence type is classified from its text: noise (identity/admin),
   explanatory, suspicious, or dual-use. 54 distinct type names exist across the
   four institutions; 27 in the bank alone.
3. Each alert rule is then matched against the documents that can answer it, per
   the rule table in that institution's `POLICY.md`. A case is CLOSE only when
   *every* alert it raised is answered by a document (docs/CONTRACT.md §5: one
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

## Coverage

| institution | cases | combinations | CLOSE combos (cases) | RFI combos (cases) | ESC combos (cases) | need review |
|---|---|---|---|---|---|---|
| bank | 1000 | 37 | 28 (567) | 3 (123) | 6 (310) | 11 |
| emoney | 1000 | 35 | 24 (584) | 2 (41) | 9 (375) | 13 |
| investment | 1000 | 25 | 18 (445) | 2 (50) | 5 (505) | 7 |
| payments_fx | 1000 | 37 | 32 (698) | 0 (0) | 5 (302) | 7 |
| **total** | 4000 | 134 | 102 (2294) | 7 (214) | 25 (1492) | 38 |

CLOSE covers 57.4% of dev cases, RFI 5.3%, ESCALATE 37.3%.

## bank — 1000 cases, 37 combinations

| # | cases | rules | advice | 2nd | conf | review | core evidence | basis |
|---|---|---|---|---|---|---|---|---|
| 01 | 179 | TM01, TM02, TM04, TM07, TM22 | ESCALATE/ESC_UNEXPLAINED_FUNDS | RFI/RFI_COUNTERPARTY_DETAILS 20% | medium | yes | (noise only) | no document explains the activity and the customer has given no account of it |
| 02 | 87 | TM01, TM02, TM05, TM06 | RFI/RFI_SOURCE_OF_FUNDS | ESCALATE/ESC_UNEXPLAINED_FUNDS 26% | low | yes | CHAT | nothing on file shows where the money came from; the customer has given only an account of it |
| 03 | 59 | TM01, TM02 | CLOSE/OWN_ACCOUNT | — | high |  | STMT | a document shows the other side of the transfer is the customer's own account |
| 04 | 59 | TM01, TM02, TM05, TM06 | ESCALATE/ESC_HIGH_RISK_CORRIDOR | RFI/RFI_SOURCE_OF_FUNDS 29% | medium | yes | CHAT | payments to a higher-risk country are undocumented, or the payer refuses to explain them |
| 05 | 32 | TM01, TM07 | CLOSE/DOCUMENTED_EVENT | — | high |  | INS | a documented one-off event (payout, sale, inheritance, settlement) explains the funds |
| 06 | 27 | TM01, TM07 | CLOSE/OWN_ACCOUNT | CLOSE/RETURNING_CUSTOMER 37% | high |  | STMT+RVF | a document shows the other side of the transfer is the customer's own account |
| 07 | 26 | TM01, TM06 | CLOSE/REFUND_OF_EARLIER_PAYMENT | — | high |  | VENUE | the money is a refund of an earlier payment, documented by the counterparty |
| 08 | 26 | TM01, TM05 | CLOSE/DOCUMENTED_EVENT | — | high |  | INSCH+SALE | a documented one-off event (payout, sale, inheritance, settlement) explains the funds |
| 09 | 24 | TM01, TM02 | RFI/RFI_SOURCE_OF_FUNDS | — | medium | yes | REG+CHAT | nothing on file shows where the money came from; the customer has given only an account of it |
| 10 | 24 | TM01 | CLOSE/DOCUMENTED_EVENT | — | high |  | SOL | a documented one-off event (payout, sale, inheritance, settlement) explains the funds |
| 11 | 23 | TM02, TM04 | CLOSE/COLLECTION_DOCUMENTED | — | high |  | BOOK | a documented collection for named people explains the many payers |
| 12 | 23 | TM22 | CLOSE/LIST_MATCH_DIFFERENT_PARTY | — | high |  | REG+RCT | the register or the identity documents show the counterparty is not the listed party |
| 13 | 23 | TM01, TM02, TM04 | ESCALATE/ESC_MULE_ACTIVITY | — | medium | yes | FRAUD+CHAT | the customer receives other people's money and forwards it, and a sending bank reports a scam payment |
| 14 | 22 | TM03 | CLOSE/BUSINESS_RECORDS_RECONCILE | — | high |  | COLL+PROC+REG | business records (takings, collection reports, management accounts) reconcile to the money that moved |
| 15 | 22 | TM01, TM03 | ESCALATE/ESC_STRUCTURING | — | medium | yes | REG+MGT+NOTE | a branch or staff note records the customer asking how to keep transactions below the reporting threshold |
| 16 | 22 | TM06 | CLOSE/DOCUMENTED_EVENT | — | high |  | HOSP+CHAT | a documented one-off event (payout, sale, inheritance, settlement) explains the funds |
| 17 | 20 | TM03 | CLOSE/BUSINESS_RECORDS_RECONCILE | — | high |  | RECON+REG+TKT | business records (takings, collection reports, management accounts) reconcile to the money that moved |
| 18 | 20 | TM01, TM02 | CLOSE/INVOICE_MATCHES | — | high |  | REG+CONS | an invoice or contract names the payee, the amount and the date of the payment |
| 19 | 20 | TM01, TM02 | CLOSE/INVOICE_MATCHES | — | high |  | DEALER+LOAN | an invoice or contract names the payee, the amount and the date of the payment |
| 20 | 18 | TM03 | CLOSE/BUSINESS_RECORDS_RECONCILE | — | high |  | RECON+REG+TKT | business records (takings, collection reports, management accounts) reconcile to the money that moved |
| 21 | 18 | TM22 | CLOSE/LIST_MATCH_DIFFERENT_PARTY | — | medium | yes | REG+INV+PSC | the register or the identity documents show the counterparty is not the listed party |
| 22 | 18 | TM01, TM02 | CLOSE/INVOICE_MATCHES | — | high |  | DEALER+LOAN | an invoice or contract names the payee, the amount and the date of the payment |
| 23 | 17 | TM03 | CLOSE/BUSINESS_RECORDS_RECONCILE | — | high |  | COLL+PROC+REG | business records (takings, collection reports, management accounts) reconcile to the money that moved |
| 24 | 17 | TM22 | CLOSE/LIST_MATCH_DIFFERENT_PARTY | — | medium | yes | REG+INV+PSC | the register or the identity documents show the counterparty is not the listed party |
| 25 | 16 | TM02, TM04 | CLOSE/COLLECTION_DOCUMENTED | — | high |  | BOOK | a documented collection for named people explains the many payers |
| 26 | 16 | TM01, TM02 | CLOSE/INVOICE_MATCHES | — | high |  | REG+CONS | an invoice or contract names the payee, the amount and the date of the payment |
| 27 | 16 | TM06 | CLOSE/DOCUMENTED_EVENT | — | high |  | HOSP+CHAT | a documented one-off event (payout, sale, inheritance, settlement) explains the funds |
| 28 | 15 | TM22 | CLOSE/LIST_MATCH_DIFFERENT_PARTY | — | high |  | REG+RCT | the register or the identity documents show the counterparty is not the listed party |
| 29 | 15 | TM01 | CLOSE/DOCUMENTED_EVENT | — | high |  | SOL | a documented one-off event (payout, sale, inheritance, settlement) explains the funds |
| 30 | 14 | TM01, TM02 | CLOSE/OWN_ACCOUNT | — | high |  | STMT | a document shows the other side of the transfer is the customer's own account |
| 31 | 14 | TM01, TM03 | ESCALATE/ESC_STRUCTURING | — | medium | yes | REG+MGT+NOTE | a branch or staff note records the customer asking how to keep transactions below the reporting threshold |
| 32 | 13 | TM01, TM05 | CLOSE/DOCUMENTED_EVENT | — | high |  | INSCH+SALE | a documented one-off event (payout, sale, inheritance, settlement) explains the funds |
| 33 | 13 | TM01, TM02, TM04 | ESCALATE/ESC_MULE_ACTIVITY | — | medium | yes | FRAUD+CHAT | the customer receives other people's money and forwards it, and a sending bank reports a scam payment |
| 34 | 12 | TM01, TM02 | RFI/RFI_SOURCE_OF_FUNDS | — | medium | yes | REG+CHAT | nothing on file shows where the money came from; the customer has given only an account of it |
| 35 | 12 | TM01, TM06 | CLOSE/REFUND_OF_EARLIER_PAYMENT | — | high |  | VENUE | the money is a refund of an earlier payment, documented by the counterparty |
| 36 | 11 | TM01, TM07 | CLOSE/OWN_ACCOUNT | CLOSE/RETURNING_CUSTOMER 27% | high |  | STMT+RVF | a document shows the other side of the transfer is the customer's own account |
| 37 | 7 | TM01, TM07 | CLOSE/DOCUMENTED_EVENT | — | high |  | INS | a documented one-off event (payout, sale, inheritance, settlement) explains the funds |

## emoney — 1000 cases, 35 combinations

| # | cases | rules | advice | 2nd | conf | review | core evidence | basis |
|---|---|---|---|---|---|---|---|---|
| 01 | 208 | TM01, TM02, TM04, TM07, TM22 | ESCALATE/ESC_UNEXPLAINED_FUNDS | RFI/RFI_COUNTERPARTY_DETAILS 20% | medium | yes | (noise only) | no document explains the activity and the customer has given no account of it |
| 02 | 70 | TM01, TM02 | CLOSE/OWN_ACCOUNT | — | high |  | STMT | a document shows the other side of the transfer is the customer's own account |
| 03 | 34 | TM02 | CLOSE/REFUND_OF_EARLIER_PAYMENT | — | high |  | DEPRET+DEPREC | the money is a refund of an earlier payment, documented by the counterparty |
| 04 | 31 | TM01, TM07 | CLOSE/OWN_ACCOUNT | CLOSE/RETURNING_CUSTOMER 23% | high |  | STMT+RVF | a document shows the other side of the transfer is the customer's own account |
| 05 | 30 | TM01 | CLOSE/DOCUMENTED_EVENT | — | high |  | SETTLE | a documented one-off event (payout, sale, inheritance, settlement) explains the funds |
| 06 | 28 | TM22 | CLOSE/LIST_MATCH_DIFFERENT_PARTY | — | high |  | REG+RCT | the register or the identity documents show the counterparty is not the listed party |
| 07 | 28 | TM01, TM07 | CLOSE/DOCUMENTED_EVENT | — | high |  | INS | a documented one-off event (payout, sale, inheritance, settlement) explains the funds |
| 08 | 28 | TM01, TM02, TM04 | ESCALATE/ESC_MULE_ACTIVITY | — | medium | yes | DEV+FRAUD+CHAT | the customer receives other people's money and forwards it, and a sending bank reports a scam payment |
| 09 | 27 | TM03 | CLOSE/BUSINESS_RECORDS_RECONCILE | — | high |  | TAKINGS | business records (takings, collection reports, management accounts) reconcile to the money that moved |
| 10 | 27 | TM01, TM02 | ESCALATE/ESC_ACCOUNT_MISUSE | — | medium | yes | DEV | one device is used to operate several different customer accounts |
| 11 | 26 | TM05 | CLOSE/DOCUMENTED_EVENT | — | high |  | AD+SRCT | a documented one-off event (payout, sale, inheritance, settlement) explains the funds |
| 12 | 26 | TM06 | CLOSE/DOCUMENTED_EVENT | — | high |  | HOSP+CHAT | a documented one-off event (payout, sale, inheritance, settlement) explains the funds |
| 13 | 26 | TM01, TM06 | CLOSE/REFUND_OF_EARLIER_PAYMENT | — | high |  | VENUE | the money is a refund of an earlier payment, documented by the counterparty |
| 14 | 25 | TM22 | CLOSE/LIST_MATCH_DIFFERENT_PARTY | — | medium | yes | REG+INV+PSC | the register or the identity documents show the counterparty is not the listed party |
| 15 | 24 | TM02, TM04 | CLOSE/COLLECTION_DOCUMENTED | — | high |  | BOOK | a documented collection for named people explains the many payers |
| 16 | 23 | TM01, TM02 | RFI/RFI_SOURCE_OF_FUNDS | — | medium | yes | REG+CHAT | nothing on file shows where the money came from; the customer has given only an account of it |
| 17 | 23 | TM01, TM02, TM03 | ESCALATE/ESC_STRUCTURING | — | medium | yes | NOTE | a branch or staff note records the customer asking how to keep transactions below the reporting threshold |
| 18 | 23 | TM01, TM02, TM04, TM06 | ESCALATE/ESC_HIGH_RISK_CORRIDOR | — | medium | yes | CHAT | payments to a higher-risk country are undocumented, or the payer refuses to explain them |
| 19 | 21 | TM02, TM04 | CLOSE/COLLECTION_DOCUMENTED | — | high |  | BOOK | a documented collection for named people explains the many payers |
| 20 | 20 | TM05 | CLOSE/DOCUMENTED_EVENT | — | high |  | AD+SRCT | a documented one-off event (payout, sale, inheritance, settlement) explains the funds |
| 21 | 19 | TM01, TM02, TM04, TM06 | ESCALATE/ESC_HIGH_RISK_CORRIDOR | — | medium | yes | CHAT | payments to a higher-risk country are undocumented, or the payer refuses to explain them |
| 22 | 19 | TM06 | CLOSE/DOCUMENTED_EVENT | — | high |  | HOSP+CHAT | a documented one-off event (payout, sale, inheritance, settlement) explains the funds |
| 23 | 19 | TM03 | CLOSE/BUSINESS_RECORDS_RECONCILE | — | high |  | TAKINGS | business records (takings, collection reports, management accounts) reconcile to the money that moved |
| 24 | 19 | TM01, TM06 | CLOSE/REFUND_OF_EARLIER_PAYMENT | — | high |  | VENUE | the money is a refund of an earlier payment, documented by the counterparty |
| 25 | 18 | TM02 | CLOSE/OWN_ACCOUNT | — | high |  | STMT | a document shows the other side of the transfer is the customer's own account |
| 26 | 18 | TM01, TM02 | RFI/RFI_SOURCE_OF_FUNDS | — | medium | yes | REG+CHAT | nothing on file shows where the money came from; the customer has given only an account of it |
| 27 | 18 | TM01, TM07 | CLOSE/DOCUMENTED_EVENT | — | high |  | INS | a documented one-off event (payout, sale, inheritance, settlement) explains the funds |
| 28 | 18 | TM01, TM02, TM03 | ESCALATE/ESC_STRUCTURING | — | medium | yes | NOTE | a branch or staff note records the customer asking how to keep transactions below the reporting threshold |
| 29 | 17 | TM22 | CLOSE/LIST_MATCH_DIFFERENT_PARTY | — | medium | yes | REG+INV+PSC | the register or the identity documents show the counterparty is not the listed party |
| 30 | 17 | TM22 | CLOSE/LIST_MATCH_DIFFERENT_PARTY | — | high |  | REG+RCT | the register or the identity documents show the counterparty is not the listed party |
| 31 | 15 | TM01, TM07 | CLOSE/OWN_ACCOUNT | CLOSE/RETURNING_CUSTOMER 33% | high |  | STMT+RVF | a document shows the other side of the transfer is the customer's own account |
| 32 | 15 | TM01, TM02 | ESCALATE/ESC_ACCOUNT_MISUSE | — | medium | yes | DEV | one device is used to operate several different customer accounts |
| 33 | 15 | TM01 | CLOSE/DOCUMENTED_EVENT | — | high |  | SETTLE | a documented one-off event (payout, sale, inheritance, settlement) explains the funds |
| 34 | 14 | TM01, TM02, TM04 | ESCALATE/ESC_MULE_ACTIVITY | — | medium | yes | DEV+FRAUD+CHAT | the customer receives other people's money and forwards it, and a sending bank reports a scam payment |
| 35 | 11 | TM02 | CLOSE/REFUND_OF_EARLIER_PAYMENT | — | high |  | DEPRET+DEPREC | the money is a refund of an earlier payment, documented by the counterparty |

## investment — 1000 cases, 25 combinations

| # | cases | rules | advice | 2nd | conf | review | core evidence | basis |
|---|---|---|---|---|---|---|---|---|
| 01 | 215 | TM01, TM02, TM07, TM08, TM10, TM22 | ESCALATE/ESC_UNEXPLAINED_FUNDS | ESCALATE/ESC_EARLY_REDEMPTION 17% | medium | yes | (noise only) | no document explains the activity and the customer has given no account of it |
| 02 | 104 | TM01, TM02, TM06, TM08, TM10 | ESCALATE/ESC_PASS_THROUGH | — | medium | yes | CHAT | the customer collects money from friends and relatives and sends it on with no purpose of their own |
| 03 | 78 | TM01, TM08, TM22 | ESCALATE/ESC_LISTED_PARTY | CLOSE/THIRD_PARTY_DOCUMENTED 28% | medium | yes | GIFT | a signed document gives the listed party's own date of birth, so the counterparty is the listed party |
| 04 | 66 | TM01, TM08 | CLOSE/OWN_ACCOUNT | — | high |  | STMT | a document shows the other side of the transfer is the customer's own account |
| 05 | 62 | TM01, TM08, TM22 | ESCALATE/ESC_LISTED_PARTY | CLOSE/THIRD_PARTY_DOCUMENTED 37% | low | yes | GIFT | a signed document gives the listed party's own date of birth, so the counterparty is the listed party |
| 06 | 46 | TM01, TM02, TM06, TM08, TM10 | ESCALATE/ESC_PASS_THROUGH | — | medium | yes | CHAT | the customer collects money from friends and relatives and sends it on with no purpose of their own |
| 07 | 32 | TM01, TM07 | CLOSE/OWN_ACCOUNT | — | high |  | STMT+RVF | a document shows the other side of the transfer is the customer's own account |
| 08 | 31 | TM06 | CLOSE/OWN_ACCOUNT | — | high |  | STMT+LETTER | a document shows the other side of the transfer is the customer's own account |
| 09 | 30 | TM01, TM02 | CLOSE/REFUND_OF_EARLIER_PAYMENT | — | high |  | CANCEL | the money is a refund of an earlier payment, documented by the counterparty |
| 10 | 30 | TM10 | CLOSE/DOCUMENTED_EVENT | — | high |  | EMAIL+REDUN | a documented one-off event (payout, sale, inheritance, settlement) explains the funds |
| 11 | 29 | TM01, TM02 | CLOSE/OWN_ACCOUNT | — | high |  | STMT+EMAIL | a document shows the other side of the transfer is the customer's own account |
| 12 | 29 | TM01, TM02, TM08 | RFI/RFI_SOURCE_OF_FUNDS | — | medium | yes | REG+CHAT | nothing on file shows where the money came from; the customer has given only an account of it |
| 13 | 28 | TM01, TM08 | CLOSE/DOCUMENTED_EVENT | — | high |  | COMPL | a documented one-off event (payout, sale, inheritance, settlement) explains the funds |
| 14 | 28 | TM01, TM07, TM08 | CLOSE/DOCUMENTED_EVENT | — | high |  | INS | a documented one-off event (payout, sale, inheritance, settlement) explains the funds |
| 15 | 27 | TM01, TM06 | CLOSE/WITHIN_PROFILE | — | high |  | STMT+EMP | the documents match the customer's declared profile or employment |
| 16 | 21 | TM01, TM02, TM08 | RFI/RFI_SOURCE_OF_FUNDS | — | medium | yes | REG+CHAT | nothing on file shows where the money came from; the customer has given only an account of it |
| 17 | 18 | TM01, TM06 | CLOSE/WITHIN_PROFILE | — | high |  | STMT+EMP | the documents match the customer's declared profile or employment |
| 18 | 18 | TM01, TM08 | CLOSE/DOCUMENTED_EVENT | — | high |  | COMPL | a documented one-off event (payout, sale, inheritance, settlement) explains the funds |
| 19 | 18 | TM01, TM07, TM08 | CLOSE/DOCUMENTED_EVENT | — | high |  | INS | a documented one-off event (payout, sale, inheritance, settlement) explains the funds |
| 20 | 16 | TM01, TM02 | CLOSE/OWN_ACCOUNT | — | high |  | STMT+EMAIL | a document shows the other side of the transfer is the customer's own account |
| 21 | 16 | TM10 | CLOSE/DOCUMENTED_EVENT | — | high |  | EMAIL+REDUN | a documented one-off event (payout, sale, inheritance, settlement) explains the funds |
| 22 | 15 | TM06 | CLOSE/OWN_ACCOUNT | — | high |  | STMT+LETTER | a document shows the other side of the transfer is the customer's own account |
| 23 | 15 | TM01, TM02 | CLOSE/REFUND_OF_EARLIER_PAYMENT | — | high |  | CANCEL | the money is a refund of an earlier payment, documented by the counterparty |
| 24 | 14 | TM01, TM08 | CLOSE/OWN_ACCOUNT | — | high |  | STMT | a document shows the other side of the transfer is the customer's own account |
| 25 | 14 | TM01, TM07 | CLOSE/OWN_ACCOUNT | CLOSE/RETURNING_CUSTOMER 36% | high |  | STMT+RVF | a document shows the other side of the transfer is the customer's own account |

## payments_fx — 1000 cases, 37 combinations

| # | cases | rules | advice | 2nd | conf | review | core evidence | basis |
|---|---|---|---|---|---|---|---|---|
| 01 | 218 | TM01, TM02, TM03, TM04, TM07, TM08, TM22 | ESCALATE/ESC_UNEXPLAINED_FUNDS | — | medium | yes | REG | no document explains the activity and the customer has given no account of it |
| 02 | 144 | TM01 | CLOSE/OWN_ACCOUNT | — | high |  | STMT+REG | a document shows the other side of the transfer is the customer's own account |
| 03 | 66 | TM01 | CLOSE/OWN_ACCOUNT | — | high |  | STMT+REG | a document shows the other side of the transfer is the customer's own account |
| 04 | 33 | TM02, TM04, TM08 | CLOSE/INVOICE_MATCHES | — | high |  | REG+PAYF | an invoice or contract names the payee, the amount and the date of the payment |
| 05 | 31 | TM01 | CLOSE/INVOICE_MATCHES | — | high |  | REG+SINVS | an invoice or contract names the payee, the amount and the date of the payment |
| 06 | 30 | TM02, TM04, TM08 | CLOSE/INVOICE_MATCHES | — | high |  | REG+PAYF | an invoice or contract names the payee, the amount and the date of the payment |
| 07 | 29 | TM06 | ESCALATE/ESC_HIGH_RISK_CORRIDOR | CLOSE/INVOICE_MATCHES 24% | medium | yes | REG+NOTE+SINVS | payments to a higher-risk country are undocumented, or the payer refuses to explain them |
| 08 | 27 | TM02, TM06, TM08 | CLOSE/REFUND_OF_EARLIER_PAYMENT | — | high |  | REG+CNOTE | the money is a refund of an earlier payment, documented by the counterparty |
| 09 | 26 | TM22 | CLOSE/LIST_MATCH_DIFFERENT_PARTY | — | medium | yes | REG+INV+PSC | the register or the identity documents show the counterparty is not the listed party |
| 10 | 25 | TM02, TM08 | CLOSE/INVOICE_MATCHES | — | high |  | REG+CONS | an invoice or contract names the payee, the amount and the date of the payment |
| 11 | 24 | TM03 | ESCALATE/ESC_STRUCTURING | — | medium | yes | REG+INV+NOTE | a branch or staff note records the customer asking how to keep transactions below the reporting threshold |
| 12 | 22 | TM01 | CLOSE/INVOICE_MATCHES | — | high |  | REG+PO+SINV | an invoice or contract names the payee, the amount and the date of the payment |
| 13 | 18 | TM03 | CLOSE/INVOICE_MATCHES | — | high |  | REG+SCHED | an invoice or contract names the payee, the amount and the date of the payment |
| 14 | 18 | TM03 | ESCALATE/ESC_STRUCTURING | — | medium | yes | REG+INV+NOTE | a branch or staff note records the customer asking how to keep transactions below the reporting threshold |
| 15 | 18 | TM06 | CLOSE/INVOICE_MATCHES | — | high |  | REG+SINV+SCON | an invoice or contract names the payee, the amount and the date of the payment |
| 16 | 18 | TM02, TM06, TM08 | CLOSE/REFUND_OF_EARLIER_PAYMENT | — | high |  | REG+CNOTE | the money is a refund of an earlier payment, documented by the counterparty |
| 17 | 16 | TM02, TM08 | CLOSE/INVOICE_MATCHES | — | high |  | REG+CONS | an invoice or contract names the payee, the amount and the date of the payment |
| 18 | 16 | TM02, TM08 | CLOSE/GROUP_COMPANY | — | high |  | REG+GROUP | the counterparty is a verified company in the same group |
| 19 | 16 | TM22 | CLOSE/LIST_MATCH_DIFFERENT_PARTY | — | medium | yes | REG+INV+PSC | the register or the identity documents show the counterparty is not the listed party |
| 20 | 16 | TM03 | CLOSE/INVOICE_MATCHES | — | high |  | REG+SCHED | an invoice or contract names the payee, the amount and the date of the payment |
| 21 | 16 | TM06 | CLOSE/INVOICE_MATCHES | — | high |  | REG+SINV+SCON | an invoice or contract names the payee, the amount and the date of the payment |
| 22 | 14 | TM02, TM08 | CLOSE/INVOICE_MATCHES | — | high |  | CARR+REG+FREIGHT | an invoice or contract names the payee, the amount and the date of the payment |
| 23 | 14 | TM02, TM08 | CLOSE/GROUP_COMPANY | — | high |  | REG+EMAIL_DOC+GROUP+SINV | the counterparty is a verified company in the same group |
| 24 | 13 | TM01, TM08 | CLOSE/BUSINESS_RECORDS_RECONCILE | — | high |  | REG+FACT+REM | business records (takings, collection reports, management accounts) reconcile to the money that moved |
| 25 | 13 | TM07 | CLOSE/RETURNING_CUSTOMER | — | high |  | REG+RVF+SINV | a re-verification record shows the customer returned to a dormant account |
| 26 | 13 | TM06 | ESCALATE/ESC_HIGH_RISK_CORRIDOR | CLOSE/INVOICE_MATCHES 23% | medium | yes | REG+NOTE+SINVS | payments to a higher-risk country are undocumented, or the payer refuses to explain them |
| 27 | 13 | TM07, TM08 | CLOSE/DOCUMENTED_EVENT | — | high |  | REG+INS | a documented one-off event (payout, sale, inheritance, settlement) explains the funds |
| 28 | 12 | TM22 | CLOSE/LIST_MATCH_DIFFERENT_PARTY | — | high |  | REG+RCT | the register or the identity documents show the counterparty is not the listed party |
| 29 | 11 | TM01 | CLOSE/INVOICE_MATCHES | — | high |  | REG+SINVS | an invoice or contract names the payee, the amount and the date of the payment |
| 30 | 11 | TM01 | CLOSE/INVOICE_MATCHES | — | high |  | REG+PO+SINV | an invoice or contract names the payee, the amount and the date of the payment |
| 31 | 10 | TM22 | CLOSE/LIST_MATCH_DIFFERENT_PARTY | — | high |  | REG+RCT | the register or the identity documents show the counterparty is not the listed party |
| 32 | 9 | TM07, TM08 | CLOSE/DOCUMENTED_EVENT | — | high |  | REG+INS | a documented one-off event (payout, sale, inheritance, settlement) explains the funds |
| 33 | 9 | TM02, TM08 | CLOSE/BUSINESS_RECORDS_RECONCILE | — | high |  | REG+FACT+REM | business records (takings, collection reports, management accounts) reconcile to the money that moved |
| 34 | 9 | TM07 | CLOSE/RETURNING_CUSTOMER | — | high |  | REG+RVF+SINV | a re-verification record shows the customer returned to a dormant account |
| 35 | 8 | TM02, TM08 | CLOSE/INVOICE_MATCHES | — | high |  | CARR+REG+FREIGHT | an invoice or contract names the payee, the amount and the date of the payment |
| 36 | 8 | TM02, TM08 | CLOSE/GROUP_COMPANY | — | high |  | REG+EMAIL_DOC+GROUP+SINV | the counterparty is a verified company in the same group |
| 37 | 6 | TM02, TM08 | CLOSE/GROUP_COMPANY | — | high |  | REG+GROUP | the counterparty is a verified company in the same group |

## Needs a human decision

These combinations are flagged because the policy does not settle them from the files alone. Each line is the question a reviewer has to answer.

**bank**

| cases | advice | core evidence | question |
|---|---|---|---|
| 179 | ESCALATE/ESC_UNEXPLAINED_FUNDS | (noise only) | policy fallback: unproven activity escalates, it is never closed the alert turns on a single identity detail that no document settles: policy answers this with an RFI, not a close |
| 87 | RFI/RFI_SOURCE_OF_FUNDS | CHAT | an alert stays unexplained after the documents on file: policy escalates no document yet: the policy answer is an RFI, the fallback is ESC_UNEXPLAINED_FUNDS if the account in chat does not hold up policy fallback: unpro… |
| 59 | ESCALATE/ESC_HIGH_RISK_CORRIDOR | CHAT | an alert stays unexplained after the documents on file: policy escalates no document yet: the policy answer is an RFI, the fallback is ESC_UNEXPLAINED_FUNDS if the account in chat does not hold up policy fallback: unpro… |
| 24 | RFI/RFI_SOURCE_OF_FUNDS | REG+CHAT | no document yet: the policy answer is an RFI, the fallback is ESC_UNEXPLAINED_FUNDS if the account in chat does not hold up policy fallback: unproven activity escalates, it is never closed |
| 23 | ESCALATE/ESC_MULE_ACTIVITY | FRAUD+CHAT | fraud report on file: escalation is the policy answer, the code is a judgement |
| 22 | ESCALATE/ESC_STRUCTURING | REG+MGT+NOTE | the note is the strongest single signal in the dev set; do not close on it |
| 18 | CLOSE/LIST_MATCH_DIFFERENT_PARTY | REG+INV+PSC | TM22: closing turns on the resignation date being effective before the payment |
| 17 | CLOSE/LIST_MATCH_DIFFERENT_PARTY | REG+INV+PSC | TM22: closing turns on the resignation date being effective before the payment |
| 14 | ESCALATE/ESC_STRUCTURING | REG+MGT+NOTE | the note is the strongest single signal in the dev set; do not close on it |
| 13 | ESCALATE/ESC_MULE_ACTIVITY | FRAUD+CHAT | fraud report on file: escalation is the policy answer, the code is a judgement |
| 12 | RFI/RFI_SOURCE_OF_FUNDS | REG+CHAT | no document yet: the policy answer is an RFI, the fallback is ESC_UNEXPLAINED_FUNDS if the account in chat does not hold up |

**emoney**

| cases | advice | core evidence | question |
|---|---|---|---|
| 208 | ESCALATE/ESC_UNEXPLAINED_FUNDS | (noise only) | policy fallback: unproven activity escalates, it is never closed the alert turns on a single identity detail that no document settles: policy answers this with an RFI, not a close |
| 28 | ESCALATE/ESC_MULE_ACTIVITY | DEV+FRAUD+CHAT | fraud report on file: escalation is the policy answer, the code is a judgement |
| 27 | ESCALATE/ESC_ACCOUNT_MISUSE | DEV | shared device alone is context; several customers on one device is not |
| 25 | CLOSE/LIST_MATCH_DIFFERENT_PARTY | REG+INV+PSC | TM22: closing turns on the resignation date being effective before the payment |
| 23 | RFI/RFI_SOURCE_OF_FUNDS | REG+CHAT | no document yet: the policy answer is an RFI, the fallback is ESC_UNEXPLAINED_FUNDS if the account in chat does not hold up policy fallback: unproven activity escalates, it is never closed |
| 23 | ESCALATE/ESC_STRUCTURING | NOTE | the note is the strongest single signal in the dev set; do not close on it |
| 23 | ESCALATE/ESC_HIGH_RISK_CORRIDOR | CHAT | an alert stays unexplained after the documents on file: policy escalates |
| 19 | ESCALATE/ESC_HIGH_RISK_CORRIDOR | CHAT | an alert stays unexplained after the documents on file: policy escalates |
| 18 | RFI/RFI_SOURCE_OF_FUNDS | REG+CHAT | no document yet: the policy answer is an RFI, the fallback is ESC_UNEXPLAINED_FUNDS if the account in chat does not hold up policy fallback: unproven activity escalates, it is never closed |
| 18 | ESCALATE/ESC_STRUCTURING | NOTE | the note is the strongest single signal in the dev set; do not close on it |
| 17 | CLOSE/LIST_MATCH_DIFFERENT_PARTY | REG+INV+PSC | TM22: closing turns on the resignation date being effective before the payment |
| 15 | ESCALATE/ESC_ACCOUNT_MISUSE | DEV | shared device alone is context; several customers on one device is not |
| 14 | ESCALATE/ESC_MULE_ACTIVITY | DEV+FRAUD+CHAT | fraud report on file: escalation is the policy answer, the code is a judgement |

**investment**

| cases | advice | core evidence | question |
|---|---|---|---|
| 215 | ESCALATE/ESC_UNEXPLAINED_FUNDS | (noise only) | an alert stays unexplained after the documents on file: policy escalates partly explained combination: the unexplained alert keeps it open policy fallback: unproven activity escalates, it is never closed |
| 104 | ESCALATE/ESC_PASS_THROUGH | CHAT | mule vs pass-through is a code choice; the verdict is escalate |
| 78 | ESCALATE/ESC_LISTED_PARTY | GIFT | TM22: listed party proved by gift letter; ESC_LISTED_PARTY is the policy answer |
| 62 | ESCALATE/ESC_LISTED_PARTY | GIFT | TM22: listed party proved by gift letter; ESC_LISTED_PARTY is the policy answer |
| 46 | ESCALATE/ESC_PASS_THROUGH | CHAT | mule vs pass-through is a code choice; the verdict is escalate |
| 29 | RFI/RFI_SOURCE_OF_FUNDS | REG+CHAT | no document yet: the policy answer is an RFI, the fallback is ESC_UNEXPLAINED_FUNDS if the account in chat does not hold up |
| 21 | RFI/RFI_SOURCE_OF_FUNDS | REG+CHAT | no document yet: the policy answer is an RFI, the fallback is ESC_UNEXPLAINED_FUNDS if the account in chat does not hold up policy fallback: unproven activity escalates, it is never closed |

**payments_fx**

| cases | advice | core evidence | question |
|---|---|---|---|
| 218 | ESCALATE/ESC_UNEXPLAINED_FUNDS | REG | policy fallback: unproven activity escalates, it is never closed the alert turns on a single identity detail that no document settles: policy answers this with an RFI, not a close |
| 29 | ESCALATE/ESC_HIGH_RISK_CORRIDOR | REG+NOTE+SINVS | refusal to explain: policy says escalate rather than ask |
| 26 | CLOSE/LIST_MATCH_DIFFERENT_PARTY | REG+INV+PSC | TM22: closing turns on the resignation date being effective before the payment |
| 24 | ESCALATE/ESC_STRUCTURING | REG+INV+NOTE | the note is the strongest single signal in the dev set; do not close on it |
| 18 | ESCALATE/ESC_STRUCTURING | REG+INV+NOTE | the note is the strongest single signal in the dev set; do not close on it |
| 16 | CLOSE/LIST_MATCH_DIFFERENT_PARTY | REG+INV+PSC | TM22: closing turns on the resignation date being effective before the payment |
| 13 | ESCALATE/ESC_HIGH_RISK_CORRIDOR | REG+NOTE+SINVS | refusal to explain: policy says escalate rather than ask |

## Known soft spots in this baseline

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

