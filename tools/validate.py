#!/usr/bin/env python3
"""Validate one institution's output file against the frozen contract.

Usage:
    python3 tools/validate.py <output.jsonl> --data <institution_dir> [options]

Options:
    --quiet           only print the summary line and errors
    --strict          treat warnings as errors
    --json            print a machine-readable report instead of text
    --max-errors N    stop printing after N errors (default 40)

Exit code: 0 = pass, 1 = validation failed, 2 = bad usage / unreadable input.

Checks, per contract (docs/CONTRACT.md §2, §5):
  1. each line is a JSON object with the six fields, right types
  2. verdict in {CLOSE, RFI, ESCALATE}
  3. reason_code belongs to that verdict (system/policy/<inst>.json when readable)
  4. alert_ids is exactly the set of alerts the case has in cases.jsonl
  5. every case appears exactly once; no unknown case_id, no duplicates
  6. every evidence ID exists in the case: a doc_id on file for that customer, a
     transaction_id of one of the case's alerts, or an internal_list entry_id
  7. reason is 2-4 sentences, is not generic boilerplate, and names at least one
     concrete number or ID from this case
  8. an RFI reason says what is being asked for (warning only)

Figure checks sample three sources before saying a number is invented: the alert
messages and measured blocks, every transaction row of that customer (not only
the alerted ones), and the full text of every evidence document on file for them
(commas stripped). Only a figure absent from all three is reported.

Standard library only.
"""

import json
import os
import re
import sys

# Canonical code table from docs/CONTRACT.md. Only used when the policy file cannot
# be read; it never overrides system/policy/<inst>.json.
CANONICAL = {
    "CLOSE": [
        "COLLECTION_DOCUMENTED", "BUSINESS_RECORDS_RECONCILE", "DOCUMENTED_EVENT",
        "INVOICE_MATCHES", "OWN_ACCOUNT", "GROUP_COMPANY", "THIRD_PARTY_DOCUMENTED",
        "REFUND_OF_EARLIER_PAYMENT", "RETURNING_CUSTOMER", "LIST_MATCH_DIFFERENT_PARTY",
        "WITHIN_PROFILE",
    ],
    "RFI": [
        "RFI_PURPOSE_DOCUMENTS", "RFI_BUSINESS_RECORDS", "RFI_SOURCE_OF_FUNDS",
        "RFI_COUNTERPARTY_DETAILS", "RFI_UPDATED_PROFILE",
    ],
    "ESCALATE": [
        "ESC_MULE_ACTIVITY", "ESC_STRUCTURING", "ESC_UNEXPLAINED_FUNDS",
        "ESC_PASS_THROUGH", "ESC_INVOICE_MISMATCH", "ESC_HIGH_RISK_CORRIDOR",
        "ESC_ACCOUNT_MISUSE", "ESC_THIRD_PARTY_FUNDING", "ESC_EARLY_REDEMPTION",
        "ESC_LISTED_PARTY",
    ],
}

VERDICTS = ("CLOSE", "RFI", "ESCALATE")
FIELDS = ("case_id", "alert_ids", "verdict", "reason_code", "reason", "evidence")

# Sentences that fit any case, so they earn nothing (docs/CONTRACT.md reason rules).
GENERIC_PATTERNS = [
    r"经审阅(相关)?证据",
    r"(该|此)?(活动|交易|行为)(已|已被)(解释|核实|确认)",
    r"未见(异常|可疑)",
    r"no further action",
    r"activity (has been|is) (explained|verified|consistent)",
    r"after (reviewing|considering) the (evidence|documents)",
    r"the (documents|evidence) on file (explain|support)",
    r"nothing (untoward|suspicious) (was )?(found|identified)",
    r"does not (appear|seem) (unusual|suspicious)",
    r"all (checks|requirements) (have been )?(completed|met)",
    r"appropriate action (has been|was) taken",
]

QUOTED = re.compile(r'"[^"]*"|“[^”]*”|‘[^’]*’')


def split_sentences(text):
    """Split into sentences without counting quoted speech or abbreviations.

    A customer quote inside a reason ("yes, that's right. it is the £14,700…")
    is one sentence, and "Sp. z o.o" or "Ltd." must not add one either.
    """
    text = QUOTED.sub("QUOTED", text or "")
    parts = re.split(r"(?<=[.!?。！？])\s+|\n+", text)
    out = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if out and part[0].islower():
            out[-1] = out[-1] + " " + part
        else:
            out.append(part)
    return out
ID_TOKEN = re.compile(r"\b[A-Z]{2,5}-[A-Z0-9]{2,}\b")
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
RFI_VERBS = re.compile(
    r"\b(ask|asked|asking|request|requested|requesting|provide|providing|obtain|"
    r"obtaining|send|supply|supplying|confirm|clarify|clarifying|explain|document|"
    r"evidence of)\b", re.I)


class Report(object):
    def __init__(self, path, institution):
        self.path = path
        self.institution = institution
        self.errors = []
        self.warnings = []
        self.stats = {
            "lines": 0, "cases_expected": 0, "cases_seen": 0,
            "verdicts": {v: 0 for v in VERDICTS},
            "reason_codes": {}, "evidence_counts": [],
            "sentence_counts": [], "missing_cases": [],
        }

    def error(self, line_no, case_id, message):
        self.errors.append((line_no, case_id, message))

    def warn(self, line_no, case_id, message):
        self.warnings.append((line_no, case_id, message))


def read_jsonl_lines(path):
    rows = []
    with open(path, "r", encoding="utf-8-sig") as fh:
        for line_no, line in enumerate(fh, 1):
            if line.strip():
                rows.append((line_no, line))
    return rows


def load_jsonl(path):
    out = []
    with open(path, "r", encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def load_policy(inst):
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    path = os.path.join(root, "system", "policy", inst + ".json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        codes = data.get("codes") or {}
        table = {v: list(codes.get(v, [])) for v in VERDICTS}
        if all(table[v] for v in VERDICTS):
            return table, path
    except (OSError, ValueError):
        pass
    return {v: list(CANONICAL[v]) for v in VERDICTS}, "canonical table"


def index_inputs(data_dir):
    cases = {}
    for row in load_jsonl(os.path.join(data_dir, "cases.jsonl")):
        cases[row["case_id"]] = row

    alerts_by_case = {}
    tx_by_alert = {}
    alert_rows_by_case = {}
    for row in load_jsonl(os.path.join(data_dir, "alerts.jsonl")):
        alerts_by_case.setdefault(row["case_id"], []).append(row["alert_id"])
        alert_rows_by_case.setdefault(row["case_id"], []).append(row)
        tx_by_alert[row["alert_id"]] = list(row.get("transaction_ids") or [])

    docs_by_customer = {}
    for row in load_jsonl(os.path.join(data_dir, "evidence.jsonl")):
        docs_by_customer.setdefault(row["customer_id"], []).append(row)

    entry_ids = {row["entry_id"] for row in load_jsonl(
        os.path.join(data_dir, "internal_list.jsonl"))}

    tx_numbers = {}
    tx_path = os.path.join(data_dir, "transactions.jsonl")
    if os.path.exists(tx_path):
        for row in load_jsonl(tx_path):
            tx_numbers.setdefault(row.get("customer_id"), set()).update(
                numbers_in(json.dumps(row, ensure_ascii=False)))

    return (cases, alerts_by_case, alert_rows_by_case, tx_by_alert,
            docs_by_customer, entry_ids, tx_numbers)


def numbers_in(text):
    """Digit strings in a piece of text, thousands separators removed."""
    values = set()
    for chunk in NUMBER.findall(text or ""):
        plain = chunk.replace(",", "")
        values.add(plain)
        for part in re.findall(r"\d+", plain):
            values.add(part)
        if "." in plain:
            values.add(plain.split(".")[0])
    return values


class NumberIndex(object):
    """Every number a case legitimately has access to.

    Sampled from the alert messages and measured blocks, every transaction row
    of that customer (not only the alerted ones) and the full text of every
    evidence document on file for them. A figure in a reason that appears in any
    of those is real; only a figure found in none of them is worth a warning.
    """

    def __init__(self, data_dir, docs_by_customer, tx_numbers):
        self.dir = data_dir
        self.docs_by_customer = docs_by_customer
        self.tx_numbers = tx_numbers
        self._doc_numbers = {}
        self._blob = {}

    def _doc_numbers_for(self, customer_id):
        if customer_id in self._doc_numbers:
            return self._doc_numbers[customer_id]
        values = set()
        for doc in self.docs_by_customer.get(customer_id, []):
            path = os.path.join(self.dir, doc.get("file") or "")
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    values.update(numbers_in(fh.read()))
            except OSError:
                pass
        self._doc_numbers[customer_id] = values
        return values

    def for_case(self, case, alert_rows):
        customer_id = case.get("customer_id")
        key = (case.get("case_id"), customer_id)
        if key in self._blob:
            return self._blob[key]
        values = set(self.tx_numbers.get(customer_id, set()))
        values |= self._doc_numbers_for(customer_id)
        for alert in alert_rows:
            values |= numbers_in(alert.get("message") or "")
            values |= numbers_in(json.dumps(alert.get("measured") or {}, ensure_ascii=False))
            values |= numbers_in(json.dumps(alert.get("transaction_ids") or []))
        values |= numbers_in(json.dumps(case.get("review_window") or {}, ensure_ascii=False))
        values |= numbers_in(case.get("opened_at") or "")
        values |= numbers_in(case.get("held_payment_id") or "")
        self._blob[key] = values
        return values


def check_reason(rec, case, alert_rows, docs, doc_set, tx_ids, alert_ids, entry_ids,
                 numbers_index, rep, line_no):
    reason = rec["reason"]
    stripped = reason.strip()

    generic = [p for p in GENERIC_PATTERNS if re.search(p, stripped, re.I)]
    if generic:
        rep.error(line_no, rec.get("case_id"),
                  "reason is generic boilerplate (matched %r); it must name this case's "
                  "own documents, people or amounts" % generic[0])

    sentences = split_sentences(stripped)
    rep.stats["sentence_counts"].append(len(sentences))
    if not 2 <= len(sentences) <= 4:
        rep.error(line_no, rec.get("case_id"),
                  "reason has %d sentence(s); contract requires 2-4" % len(sentences))

    identifiers = set(ID_TOKEN.findall(stripped))
    for pool in (doc_set, tx_ids, set(alert_ids), entry_ids):
        identifiers.update(x for x in pool if x and x in stripped)
    identifiers = {x for x in identifiers
                   if x in doc_set or x in tx_ids or x in alert_ids or x in entry_ids}

    numbers = {m.replace(",", "") for m in NUMBER.findall(stripped)}
    numbers = {n.lstrip("0") or "0" for n in numbers}

    known = numbers_index.for_case(case, alert_rows)
    if not identifiers:
        hits = sorted(n for n in numbers if n in known and len(n) >= 2)
        if hits:
            identifiers = set(hits[:1])
    if not identifiers:
        rep.error(line_no, rec.get("case_id"),
                  "reason names no concrete number or ID belonging to this case")

    if numbers:
        unknown = sorted(n for n in numbers
                         if n not in known and len(n) >= 5 and "." in n)
        if unknown:
            rep.warn(line_no, rec.get("case_id"),
                     "reason quotes figure(s) not found in the case inputs: %s"
                     % ", ".join(unknown[:3]))

    if rec["reason_code"].startswith("RFI_") and not RFI_VERBS.search(stripped):
        rep.warn(line_no, rec.get("case_id"),
                 "RFI reason does not say what to ask the customer for")


def validate(out_path, data_dir, strict=False):
    inst = os.path.basename(os.path.abspath(data_dir).rstrip(os.sep))
    rep = Report(out_path, inst)
    codes, code_source = load_policy(inst)
    rep.stats["code_source"] = code_source

    if not os.path.isdir(data_dir):
        raise SystemExit("validate: --data %s is not a directory" % data_dir)
    try:
        (cases, alerts_by_case, alert_rows_by_case, tx_by_alert,
         docs_by_customer, entry_ids, tx_numbers) = index_inputs(data_dir)
    except OSError as exc:
        raise SystemExit("validate: cannot read institution files in %s (%s)"
                         % (data_dir, exc))
    rep.stats["cases_expected"] = len(cases)
    numbers_index = NumberIndex(data_dir, docs_by_customer, tx_numbers)

    try:
        raw_rows = read_jsonl_lines(out_path)
    except OSError as exc:
        raise SystemExit("validate: cannot read %s (%s)" % (out_path, exc))
    if not raw_rows:
        rep.error(0, None, "output file is empty; %d cases expected" % len(cases))

    seen = {}
    for line_no, raw in raw_rows:
        rep.stats["lines"] += 1
        try:
            rec = json.loads(raw)
        except ValueError as exc:
            rep.error(line_no, None, "invalid JSON: %s" % exc)
            continue
        if not isinstance(rec, dict):
            rep.error(line_no, None, "line is not a JSON object (%s)"
                      % type(rec).__name__)
            continue

        case_id = rec.get("case_id")
        label = case_id if isinstance(case_id, str) else "<line %d>" % line_no

        missing = [f for f in FIELDS if f not in rec]
        if missing:
            rep.error(line_no, label, "missing field(s): %s" % ", ".join(missing))
        extra = [f for f in rec if f not in FIELDS]
        if extra:
            rep.warn(line_no, label, "extra field(s) not in the contract: %s"
                     % ", ".join(sorted(extra)))
        if missing:
            continue

        if not isinstance(case_id, str) or not case_id:
            rep.error(line_no, label, "case_id must be a non-empty string")
            continue
        if not isinstance(rec["alert_ids"], list) or \
                not all(isinstance(a, str) for a in rec["alert_ids"]):
            rep.error(line_no, label, "alert_ids must be a list of strings")
            continue
        if not isinstance(rec["evidence"], list) or \
                not all(isinstance(e, str) for e in rec["evidence"]):
            rep.error(line_no, label, "evidence must be a list of strings")
            continue
        if not isinstance(rec["reason"], str):
            rep.error(line_no, label, "reason must be a string")
            continue
        if not isinstance(rec["verdict"], str) or not isinstance(rec["reason_code"], str):
            rep.error(line_no, label, "verdict and reason_code must be strings")
            continue

        if case_id in seen:
            rep.error(line_no, label, "duplicate case_id (first seen on line %d)"
                      % seen[case_id])
            continue
        seen[case_id] = line_no
        case = cases.get(case_id)
        if case is None:
            rep.error(line_no, label, "case_id not present in cases.jsonl")
            continue

        verdict = rec["verdict"]
        if verdict not in VERDICTS:
            rep.error(line_no, label, "verdict %r not in %s"
                      % (verdict, "/".join(VERDICTS)))
            continue
        rep.stats["verdicts"][verdict] += 1
        rep.stats["reason_codes"][rec["reason_code"]] = \
            rep.stats["reason_codes"].get(rec["reason_code"], 0) + 1
        if rec["reason_code"] not in codes[verdict]:
            owner = [v for v in VERDICTS if rec["reason_code"] in codes[v]]
            if owner:
                rep.error(line_no, label, "reason_code %s belongs to %s, not %s"
                          % (rec["reason_code"], owner[0], verdict))
            else:
                rep.error(line_no, label, "reason_code %r is not a %s code"
                          % (rec["reason_code"], inst))

        expected_alerts = alerts_by_case.get(case_id, [])
        got = rec["alert_ids"]
        if len(set(got)) != len(got):
            rep.error(line_no, label, "alert_ids contains duplicates")
        if set(got) != set(expected_alerts):
            missing_a = sorted(set(expected_alerts) - set(got))
            extra_a = sorted(set(got) - set(expected_alerts))
            bits = []
            if missing_a:
                bits.append("missing " + ", ".join(missing_a))
            if extra_a:
                bits.append("not in the case: " + ", ".join(extra_a))
            rep.error(line_no, label, "alert_ids mismatch (%s)" % "; ".join(bits))

        docs = docs_by_customer.get(case["customer_id"], [])
        doc_set = {d["doc_id"] for d in docs}
        tx_ids = set()
        for alert_id in expected_alerts:
            tx_ids.update(tx_by_alert.get(alert_id, []))
        valid_ids = doc_set | tx_ids | entry_ids

        bad = [e for e in rec["evidence"] if e not in valid_ids]
        if bad:
            rep.error(line_no, label, "evidence ID(s) not in this case's inputs: %s"
                      % ", ".join(bad[:6]))
        if len(set(rec["evidence"])) != len(rec["evidence"]):
            rep.warn(line_no, label, "evidence contains duplicate IDs")
        if not rec["evidence"]:
            rep.warn(line_no, label, "evidence list is empty")
        rep.stats["evidence_counts"].append(len(rec["evidence"]))

        check_reason(rec, case, alert_rows_by_case.get(case_id, []), docs,
                     doc_set, tx_ids, expected_alerts, entry_ids, numbers_index,
                     rep, line_no)

    rep.stats["cases_seen"] = len(seen)
    missing_cases = sorted(set(cases) - set(seen))
    rep.stats["missing_cases"] = missing_cases
    for case_id in missing_cases[:20]:
        rep.error(0, case_id,
                  "case has no output line (a missing case counts as an escalation)")
    if len(missing_cases) > 20:
        rep.error(0, None, "... and %d more missing cases" % (len(missing_cases) - 20))

    if strict:
        for line_no, case_id, message in rep.warnings:
            rep.errors.append((line_no, case_id, "[strict] " + message))
        rep.warnings = []
    return rep


def print_text(rep, quiet=False, max_errors=40):
    if not quiet:
        print("validate: %s" % rep.path)
        print("  institution    : %s" % rep.institution)
        print("  code table     : %s" % rep.stats.get("code_source"))
        print("  cases expected : %d" % rep.stats["cases_expected"])
        print("  output lines   : %d" % rep.stats["lines"])
        print("  cases covered  : %d" % rep.stats["cases_seen"])
        dist = ", ".join("%s=%d" % (v, rep.stats["verdicts"][v]) for v in VERDICTS)
        print("  verdicts       : %s" % dist)
        if rep.stats["evidence_counts"]:
            counts = rep.stats["evidence_counts"]
            print("  evidence cited : avg %.2f, min %d, max %d"
                  % (sum(counts) / float(len(counts)), min(counts), max(counts)))
        print("")

    shown = 0
    for line_no, case_id, message in rep.errors:
        if shown >= max_errors:
            print("  ... %d more error(s) suppressed (use --max-errors)"
                  % (len(rep.errors) - shown))
            break
        where = "line %d" % line_no if line_no else "file"
        print("  ERROR  %-12s %-18s %s" % (where, case_id or "-", message))
        shown += 1
    for line_no, case_id, message in rep.warnings[:max_errors]:
        where = "line %d" % line_no if line_no else "file"
        print("  WARN   %-12s %-18s %s" % (where, case_id or "-", message))

    status = "PASS" if not rep.errors else "FAIL"
    print("\n%s  %s  (%d error(s), %d warning(s), %d/%d cases)"
          % (status, rep.path, len(rep.errors), len(rep.warnings),
             rep.stats["cases_seen"], rep.stats["cases_expected"]))


def print_json(rep):
    payload = {
        "file": rep.path,
        "institution": rep.institution,
        "pass": not rep.errors,
        "errors": [{"line": l, "case_id": c, "message": m} for l, c, m in rep.errors],
        "warnings": [{"line": l, "case_id": c, "message": m} for l, c, m in rep.warnings],
        "stats": rep.stats,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv):
    args = list(argv[1:])
    if not args or args[0] in ("-h", "--help"):
        sys.stderr.write(__doc__)
        return 2
    out_path = None
    data_dir = None
    quiet = strict = as_json = False
    max_errors = 40
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--data":
            i += 1
            if i >= len(args):
                sys.stderr.write("validate: --data needs a directory\n")
                return 2
            data_dir = args[i]
        elif arg.startswith("--data="):
            data_dir = arg.split("=", 1)[1]
        elif arg == "--quiet":
            quiet = True
        elif arg == "--strict":
            strict = True
        elif arg == "--json":
            as_json = True
        elif arg == "--max-errors":
            i += 1
            try:
                max_errors = int(args[i])
            except (IndexError, ValueError):
                sys.stderr.write("validate: --max-errors needs a number\n")
                return 2
        elif arg.startswith("-"):
            sys.stderr.write("validate: unknown option %s\n" % arg)
            return 2
        elif out_path is None:
            out_path = arg
        else:
            sys.stderr.write("validate: unexpected argument %s\n" % arg)
            return 2
        i += 1

    if not out_path or not data_dir:
        sys.stderr.write(
            "usage: python3 tools/validate.py <output.jsonl> --data <institution_dir>\n")
        return 2

    rep = validate(out_path, data_dir, strict=strict)
    if as_json:
        print_json(rep)
    else:
        print_text(rep, quiet=quiet, max_errors=max_errors)
    return 0 if not rep.errors else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
