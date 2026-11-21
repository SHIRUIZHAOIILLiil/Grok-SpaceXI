#!/usr/bin/env python3
"""Report on one or more output files: verdicts, rules, reasons, evidence.

Usage:
    python3 tools/report.py [--output output] [--data data/institutions]
                            [--json] [--inst bank,emoney] [--top N]

Reads every <output>/<institution>.jsonl that has a matching data folder and
prints, per institution and in total:

  * verdict distribution (CLOSE / RFI / ESCALATE) and CLOSE rate
  * fallback rate: the share of cases left on ESC_UNEXPLAINED_FUNDS
  * reason_code distribution
  * institution x rule distribution (a case counts once per rule it raised,
    with the verdict it got)
  * reason length: sentences per reason, words per sentence
  * evidence citation count distribution
  * quality counters: evidence IDs that do not exist in the case, generic
    reasons, reasons with no case-specific number or ID, RFI reasons that do
    not say what to ask for, multi-alert cases closed

Exit code 0 always unless inputs are unreadable (2).
"""

import json
import os
import re
import sys

VERDICTS = ("CLOSE", "RFI", "ESCALATE")
FALLBACK_CODE = "ESC_UNEXPLAINED_FUNDS"
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
GENERIC_PATTERNS = [
    r"经审阅(相关)?证据",
    r"(该|此)?(活动|交易|行为)(已|已被)(解释|核实|确认)",
    r"no further action",
    r"activity (has been|is) (explained|verified|consistent)",
    r"after (reviewing|considering) the (evidence|documents)",
    r"the (documents|evidence) on file (explain|support)",
    r"nothing (untoward|suspicious) (was )?(found|identified)",
    r"does not (appear|seem) (unusual|suspicious)",
    r"all (checks|requirements) (have been )?(completed|met)",
    r"appropriate action (has been|was) taken",
]
NOISE = {"due_diligence_summary", "proof_of_address", "contact_note"}

RFI_VERBS = re.compile(
    r"\b(ask|asked|asking|request|requested|requesting|provide|providing|obtain|"
    r"obtaining|send|supply|supplying|confirm|clarify|clarifying|explain|document|"
    r"evidence of)\b", re.I)


def load_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows





class InstStats(object):
    def __init__(self, inst):
        self.inst = inst
        self.cases = 0
        self.rows = 0
        self.verdicts = {v: 0 for v in VERDICTS}
        self.codes = {}
        self.rules = {}
        self.sent_counts = []
        self.words_per_sentence = []
        self.evidence_counts = []
        self.bad_evidence = 0
        self.generic = 0
        self.no_anchor = 0
        self.rfi_no_request = 0
        self.multi_alert_closed = 0
        self.multi_alert_cases = 0
        self.missing = 0
        self.unknown = 0
        self.empty_evidence = 0
        self.reason_chars = []
        self.compared = 0
        self.agree_verdict = 0
        self.agree_code = 0
        self.confusion = {}
        self.code_confusion = {}
        self.risky = {}

    def as_dict(self):
        return {
            "cases": self.cases, "rows": self.rows,
            "verdicts": self.verdicts,
            "close_rate": (self.verdicts["CLOSE"] / float(self.cases)) if self.cases else 0.0,
            "fallback_rate": (self.codes.get(FALLBACK_CODE, 0) / float(self.cases)) if self.cases else 0.0,
            "codes": self.codes,
            "rules": self.rules,
            "avg_sentences": (sum(self.sent_counts) / float(len(self.sent_counts))) if self.sent_counts else 0.0,
            "avg_words_per_sentence": (sum(self.words_per_sentence) / float(len(self.words_per_sentence))) if self.words_per_sentence else 0.0,
            "evidence_histogram": self.evidence_counts,
            "bad_evidence": self.bad_evidence,
            "generic_reasons": self.generic,
            "no_anchor_reasons": self.no_anchor,
            "rfi_without_request": self.rfi_no_request,
            "multi_alert_cases": self.multi_alert_cases,
            "multi_alert_closed": self.multi_alert_closed,
            "missing_cases": self.missing,
            "unknown_cases": self.unknown,
            "empty_evidence": self.empty_evidence,
            "compared": self.compared,
            "agree_verdict": self.agree_verdict,
            "agree_code": self.agree_code,
            "confusion": self.confusion,
            "code_confusion": self.code_confusion,
            "risky_closes": self.risky,
        }


def load_pseudo_labels(path, inst):
    """case_id -> (verdict, code, needs_review) from tools/case_labels.jsonl."""
    out = {}
    if not path or not os.path.exists(path):
        return out
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("institution") != inst:
                continue
            out[row["case_id"]] = (row["pseudo_verdict"], row["pseudo_reason_code"],
                                   bool(row.get("needs_review")))
    return out


def analyse(inst, out_path, data_dir, pseudo=None):
    st = InstStats(inst)
    cases = {row["case_id"]: row for row in load_jsonl(
        os.path.join(data_dir, "cases.jsonl"))}
    st.cases = len(cases)

    alerts_by_case = {}
    tx_by_alert = {}
    alert_rows = []
    for row in load_jsonl(os.path.join(data_dir, "alerts.jsonl")):
        alerts_by_case.setdefault(row["case_id"], []).append(row["alert_id"])
        tx_by_alert[row["alert_id"]] = list(row.get("transaction_ids") or [])
        alert_rows.append(row)
    by_alert = {row["alert_id"]: row for row in alert_rows}

    docs_by_customer = {}
    for row in load_jsonl(os.path.join(data_dir, "evidence.jsonl")):
        docs_by_customer.setdefault(row["customer_id"], []).append(row["doc_id"])
    entry_ids = {row["entry_id"] for row in load_jsonl(
        os.path.join(data_dir, "internal_list.jsonl"))}

    types_by_customer = {}
    for row in load_jsonl(os.path.join(data_dir, "evidence.jsonl")):
        types_by_customer.setdefault(row["customer_id"], set()).add(row["type"])

    def signature_of(case_id):
        case = cases.get(case_id) or {}
        return types_by_customer.get(case.get("customer_id"), set())

    if not os.path.exists(out_path):
        st.missing = len(cases)
        return st

    seen = set()
    for rec in load_jsonl(out_path):
        st.rows += 1
        case_id = rec.get("case_id")
        if case_id in seen:
            continue
        seen.add(case_id)
        case = cases.get(case_id)
        if case is None:
            st.unknown += 1
            continue
        verdict = rec.get("verdict")
        code = rec.get("reason_code") or ""
        if verdict in st.verdicts:
            st.verdicts[verdict] += 1
        st.codes[code] = st.codes.get(code, 0) + 1

        alert_ids = alerts_by_case.get(case_id, [])
        rules = sorted({by_alert[a]["rule_id"] for a in alert_ids
                        if a in by_alert and by_alert[a].get("rule_id")})
        for rule in rules:
            slot = st.rules.setdefault(rule, {v: 0 for v in VERDICTS})
            if verdict in slot:
                slot[verdict] += 1
        if len(alert_ids) > 1:
            st.multi_alert_cases += 1
            if verdict == "CLOSE":
                st.multi_alert_closed += 1

        reason = rec.get("reason") or ""
        st.reason_chars.append(len(reason))
        parts = split_sentences(reason)
        st.sent_counts.append(len(parts))
        for part in parts:
            st.words_per_sentence.append(len(part.split()))

        evidence = rec.get("evidence") or []
        st.evidence_counts.append(len(evidence))
        if not evidence:
            st.empty_evidence += 1

        doc_set = set(docs_by_customer.get(case["customer_id"], []))
        tx_ids = set()
        for alert_id in alert_ids:
            tx_ids.update(tx_by_alert.get(alert_id, []))
        valid = doc_set | tx_ids | entry_ids
        if any(e not in valid for e in evidence):
            st.bad_evidence += 1

        if any(re.search(p, reason, re.I) for p in GENERIC_PATTERNS):
            st.generic += 1
        anchors = set(ID_TOKEN.findall(reason)) & valid
        if not anchors and not any(n.replace(",", "") in reason for n in NUMBER.findall(reason)):
            st.no_anchor += 1
        if code.startswith("RFI_") and not RFI_VERBS.search(reason):
            st.rfi_no_request += 1

        if pseudo and case_id in pseudo:
            pv, pc, review = pseudo[case_id]
            st.compared += 1
            st.agree_verdict += int(pv == verdict)
            st.agree_code += int(pc == code)
            if pv != verdict:
                st.confusion["%s->%s" % (pv, verdict)] = st.confusion.get("%s->%s" % (pv, verdict), 0) + 1
                if pv == "ESCALATE" and verdict == "CLOSE":
                    types = signature_of(case_id)
                    key = "+".join(sorted(t for t in types if t not in NOISE)) or "(noise only)"
                    slot = st.risky.setdefault(key, {"cases": 0, "ids": [], "codes": {}})
                    slot["cases"] += 1
                    if len(slot["ids"]) < 4:
                        slot["ids"].append(case_id)
                    slot["codes"][code] = slot["codes"].get(code, 0) + 1
            if pv == verdict and pc != code:
                st.code_confusion["%s->%s" % (pc, code)] = st.code_confusion.get("%s->%s" % (pc, code), 0) + 1

    st.missing = len(set(cases) - seen)
    return st


def pct(part, whole):
    return (100.0 * part / whole) if whole else 0.0


def hist_line(counts):
    buckets = {}
    for value in counts:
        key = "0" if value == 0 else ("1" if value == 1 else ("2" if value == 2 else
              ("3" if value == 3 else ("4" if value == 4 else "5+"))))
        buckets[key] = buckets.get(key, 0) + 1
    order = ["0", "1", "2", "3", "4", "5+"]
    total = len(counts) or 1
    return "  ".join("%s:%d(%4.1f%%)" % (k, buckets.get(k, 0), pct(buckets.get(k, 0), total))
                     for k in order)


def print_text(stats, out_dir, data_dir, top_rules=12):
    print("report: %s  (data %s)" % (out_dir, data_dir))
    print("")
    header = "%-13s %6s %7s %7s %7s %8s %9s %8s" % (
        "institution", "cases", "CLOSE", "RFI", "ESC", "CLOSE%", "fallback%", "rows")
    print(header)
    print("-" * len(header))
    totals = {"cases": 0, "close": 0, "rfi": 0, "esc": 0, "fallback": 0, "rows": 0}
    for st in stats:
        print("%-13s %6d %7d %7d %7d %7.1f%% %8.1f%% %8d" % (
            st.inst, st.cases, st.verdicts["CLOSE"], st.verdicts["RFI"],
            st.verdicts["ESCALATE"], pct(st.verdicts["CLOSE"], st.cases),
            pct(st.codes.get(FALLBACK_CODE, 0), st.cases), st.rows))
        totals["cases"] += st.cases
        totals["close"] += st.verdicts["CLOSE"]
        totals["rfi"] += st.verdicts["RFI"]
        totals["esc"] += st.verdicts["ESCALATE"]
        totals["fallback"] += st.codes.get(FALLBACK_CODE, 0)
        totals["rows"] += st.rows
    print("-" * len(header))
    print("%-13s %6d %7d %7d %7d %7.1f%% %8.1f%% %8d" % (
        "TOTAL", totals["cases"], totals["close"], totals["rfi"], totals["esc"],
        pct(totals["close"], totals["cases"]), pct(totals["fallback"], totals["cases"]),
        totals["rows"]))
    print("")

    print("reason_code distribution")
    codes = {}
    for st in stats:
        for code, n in st.codes.items():
            codes[code] = codes.get(code, 0) + n
    for code, n in sorted(codes.items(), key=lambda kv: (-kv[1], kv[0]))[:24]:
        print("  %-32s %5d  %5.1f%%" % (code, n, pct(n, totals["cases"])))
    if len(codes) > 24:
        print("  ... %d more codes" % (len(codes) - 24))
    print("")

    print("institution x rule  (cases raising the rule, by verdict)")
    print("  %-13s %-5s %6s %6s %6s %6s  %7s" % (
        "institution", "rule", "CLOSE", "RFI", "ESC", "cases", "CLOSE%"))
    for st in stats:
        for rule in sorted(st.rules):
            slot = st.rules[rule]
            n = sum(slot.values())
            print("  %-13s %-5s %6d %6d %6d %6d  %6.1f%%" % (
                st.inst, rule, slot["CLOSE"], slot["RFI"], slot["ESCALATE"], n,
                pct(slot["CLOSE"], n)))
    print("")

    print("reason and evidence shape")
    for st in stats:
        if not st.sent_counts:
            continue
        print("  %-13s sentences/reason %5.2f   words/sentence %5.1f   chars/reason %5.0f" % (
            st.inst,
            sum(st.sent_counts) / float(len(st.sent_counts)),
            (sum(st.words_per_sentence) / float(len(st.words_per_sentence)))
            if st.words_per_sentence else 0.0,
            sum(st.reason_chars) / float(len(st.reason_chars))))
    print("  evidence citations per case:")
    for st in stats:
        print("    %-13s %s" % (st.inst, hist_line(st.evidence_counts)))
    print("")

    print("quality counters (share of that institution's cases)")
    print("  %-13s %9s %9s %9s %9s %9s %9s" % (
        "institution", "bad evid", "generic", "no anchor", "rfi no ask", "empty ev",
        "missing"))
    for st in stats:
        print("  %-13s %8.1f%% %8.1f%% %8.1f%% %8.1f%% %8.1f%% %8.1f%%" % (
            st.inst, pct(st.bad_evidence, st.cases), pct(st.generic, st.cases),
            pct(st.no_anchor, st.cases), pct(st.rfi_no_request, st.cases),
            pct(st.empty_evidence, st.cases), pct(st.missing, st.cases)))
    print("")
    if any(st.compared for st in stats):
        print("agreement with tools/case_labels.jsonl (pseudo-labels, not ground truth)")
        for st in stats:
            if not st.compared:
                continue
            print("  %-13s verdict %5.1f%%  code %5.1f%%  (%d cases compared)"
                  % (st.inst, pct(st.agree_verdict, st.compared),
                     pct(st.agree_code, st.compared), st.compared))
        merged = {}
        for st in stats:
            for key, n in st.confusion.items():
                merged[key] = merged.get(key, 0) + n
        if merged:
            print("  biggest verdict disagreements (label->output):")
            for key, n in sorted(merged.items(), key=lambda kv: -kv[1])[:8]:
                print("    %-28s %4d" % (key, n))
        merged_codes = {}
        for st in stats:
            for key, n in st.code_confusion.items():
                merged_codes[key] = merged_codes.get(key, 0) + n
        if merged_codes:
            print("  biggest reason_code disagreements (label->output):")
            for key, n in sorted(merged_codes.items(), key=lambda kv: -kv[1])[:8]:
                print("    %-48s %4d" % (key, n))
        risky = {}
        for st in stats:
            for key, slot in st.risky.items():
                agg = risky.setdefault(key, {"cases": 0, "codes": {}, "by_inst": {}})
                agg["cases"] += slot["cases"]
                agg["by_inst"][st.inst] = slot["cases"]
                for c, n in slot["codes"].items():
                    agg["codes"][c] = agg["codes"].get(c, 0) + n
        if risky:
            print("  risky closes (pseudo-label says ESCALATE, output says CLOSE): %d cases"
                  % sum(v["cases"] for v in risky.values()))
            for key, agg in sorted(risky.items(), key=lambda kv: -kv[1]["cases"])[:6]:
                print("    %-52s %4d  %s  code=%s"
                      % (key, agg["cases"],
                         ",".join("%s:%d" % kv for kv in sorted(agg["by_inst"].items())),
                         max(agg["codes"], key=agg["codes"].get)))
        print("")

    multi = sum(st.multi_alert_cases for st in stats)
    closed = sum(st.multi_alert_closed for st in stats)
    print("multi-alert cases: %d, of which CLOSE: %d (%.1f%%)"
          % (multi, closed, pct(closed, multi)))
    if totals["close"] == 0:
        print("NOTE: no CLOSE verdicts — this looks like the all-ESCALATE baseline "
              "(verdict score 0 by construction).")
    print("")


def main(argv):
    out_dir = "output"
    data_dir = "data/institutions"
    as_json = False
    only = None
    labels_path = None
    args = list(argv[1:])
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("-h", "--help"):
            sys.stderr.write(__doc__)
            return 0
        elif arg == "--output":
            i += 1
            out_dir = args[i]
        elif arg == "--data":
            i += 1
            data_dir = args[i]
        elif arg == "--json":
            as_json = True
        elif arg == "--labels":
            i += 1
            labels_path = args[i]
        elif arg == "--inst":
            i += 1
            only = [x.strip() for x in args[i].split(",") if x.strip()]
        else:
            sys.stderr.write("report: unknown argument %s\n" % arg)
            return 2
        i += 1

    if not os.path.isdir(data_dir):
        sys.stderr.write("report: --data %s is not a directory\n" % data_dir)
        return 2

    insts = only or sorted(d for d in os.listdir(data_dir)
                           if os.path.isdir(os.path.join(data_dir, d)))
    stats = []
    for inst in insts:
        path = os.path.join(out_dir, inst + ".jsonl")
        try:
            stats.append(analyse(inst, path, os.path.join(data_dir, inst),
                                 pseudo=load_pseudo_labels(labels_path, inst)))
        except OSError as exc:
            sys.stderr.write("report: %s: %s\n" % (inst, exc))
            return 2

    if as_json:
        payload = {
            "output": out_dir, "data": data_dir,
            "institutions": {st.inst: st.as_dict() for st in stats},
            "totals": {
                "cases": sum(st.cases for st in stats),
                "verdicts": {v: sum(st.verdicts[v] for st in stats) for v in VERDICTS},
                "codes": {c: sum(st.codes.get(c, 0) for st in stats)
                          for c in sorted({c for st in stats for c in st.codes})},
            },
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_text(stats, out_dir, data_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
