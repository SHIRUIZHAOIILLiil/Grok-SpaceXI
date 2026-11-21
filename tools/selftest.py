#!/usr/bin/env python3
"""Self-test for the tools/ suite: validate.py, repro.sh, label tables.

Usage:
    python3 tools/selftest.py [--data data/institutions] [--output output]

Runs, and prints one PASS/FAIL line each:

  1. validate.py accepts the four committed output files (schema is fine even if
     every verdict is ESCALATE, which is what the baseline looks like)
  2. validate.py rejects 11 deliberately broken lines, each with the error we
     expect: missing field, wrong type, bad verdict, code from the wrong verdict,
     alert_ids mismatch, invented evidence ID, generic reason, one-sentence
     reason, unknown case, duplicate case, invalid JSON
  3. validate.py rejects an output file that omits cases
  4. labels.json covers every dev case and every evidence-type combination, and
     every advised reason_code belongs to its verdict
  5. repro.sh detects a non-deterministic pipeline (a stub that writes a random
     number) and reports the first differing byte

Exit code 0 when every check passes, 1 otherwise.
"""

import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable or "python3"


class Checker(object):
    def __init__(self):
        self.failures = 0
        self.checks = 0

    def report(self, name, ok, detail=""):
        self.checks += 1
        if not ok:
            self.failures += 1
        print("%s  %-58s %s" % ("PASS" if ok else "FAIL", name, detail))
        return ok


def run(args, cwd=None):
    proc = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True)
    return proc.returncode, proc.stdout


def load_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def read_cases(data_dir):
    return load_jsonl(os.path.join(data_dir, "cases.jsonl"))


def check_baseline(ck, data_root, out_dir):
    for inst in sorted(os.listdir(data_root)):
        inst_dir = os.path.join(data_root, inst)
        if not os.path.isdir(inst_dir):
            continue
        out = os.path.join(out_dir, inst + ".jsonl")
        if not os.path.exists(out):
            ck.report("baseline %s: output file exists" % inst, False, out)
            continue
        code, text = run([PY, os.path.join(HERE, "validate.py"), out,
                          "--data", inst_dir, "--quiet"])
        ck.report("baseline %s validates" % inst, code == 0, text.strip().splitlines()[-1])


def build_broken(data_dir, scratch):
    rows = load_jsonl(os.path.join(data_dir, "cases.jsonl"))
    alerts = {}
    txs = {}
    for row in load_jsonl(os.path.join(data_dir, "alerts.jsonl")):
        alerts.setdefault(row["case_id"], []).append(row["alert_id"])
        txs.setdefault(row["case_id"], []).extend(row.get("transaction_ids") or [])
    cases = sorted(rows, key=lambda r: r["case_id"])

    def good_for(case_id):
        ids = sorted(alerts.get(case_id, []))
        return {
            "case_id": case_id,
            "alert_ids": ids,
            "verdict": "ESCALATE",
            "reason_code": "ESC_UNEXPLAINED_FUNDS",
            "reason": "Alert %s raised the profile rule and no document on file explains the "
                      "money movement. The case goes to the MLRO for a reporting decision."
                      % (ids[0] if ids else "n/a"),
            "evidence": sorted(txs.get(case_id, []))[:1],
        }

    picks = [c["case_id"] for c in cases[:14]]
    faults = [
        ("missing field", picks[0], lambda r: {k: v for k, v in r.items() if k != "evidence"},
         "missing field(s)"),
        ("alert_ids not a list", picks[1], lambda r: dict(r, alert_ids="nope"),
         "alert_ids must be a list"),
        ("verdict outside the enum", picks[2], lambda r: dict(r, verdict="CLOSED"),
         "not in CLOSE/RFI/ESCALATE"),
        ("reason_code from the wrong verdict", picks[3],
         lambda r: dict(r, verdict="CLOSE", reason_code="ESC_STRUCTURING"), "belongs to ESCALATE"),
        ("unknown reason_code", picks[4], lambda r: dict(r, reason_code="NOT_A_CODE"), "is not a"),
        ("alert_ids mismatch", picks[5], lambda r: dict(r, alert_ids=[]), "alert_ids mismatch"),
        ("invented evidence ID", picks[6],
         lambda r: dict(r, evidence=["DOC-DOES-NOT-EXIST"]), "not in this case's inputs"),
        ("generic reason", picks[7],
         lambda r: dict(r, reason="经审阅相关证据，该活动已被解释，未见异常。"), "generic boilerplate"),
        ("one-sentence reason", picks[8],
         lambda r: dict(r, reason="Only one sentence, no facts."), "1 sentence"),
        ("reason with no case fact", picks[9],
         lambda r: dict(r, reason="The documents were reviewed carefully. "
                                  "No further action is needed."), "no concrete number or ID"),
        ("unknown case_id", picks[10],
         lambda r: dict(r, case_id="ZZ-CS000000"), "not present in cases.jsonl"),
    ]

    lines = []
    for _name, case_id, mutate, _expect in faults:
        lines.append(json.dumps(mutate(good_for(case_id)), ensure_ascii=False))
    dup = good_for(picks[11])
    lines.append(json.dumps(dup, ensure_ascii=False))
    lines.append(json.dumps(dup, ensure_ascii=False))  # duplicate case_id
    lines.append("{this is not json")
    path = os.path.join(scratch, "broken.jsonl")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    control = os.path.join(scratch, "control.jsonl")
    base = os.path.join(ROOT, "output", os.path.basename(data_dir) + ".jsonl")
    if os.path.exists(base):
        out = []
        for line in read_jsonl_text(base):
            rec = json.loads(line)
            if rec["case_id"] == picks[0]:
                rec = good_for(picks[0])
            out.append(json.dumps(rec, ensure_ascii=False))
        with open(control, "w", encoding="utf-8") as fh:
            fh.write("\n".join(out) + "\n")
    return path, [(n, e) for n, _c, _m, e in faults], control


def check_broken(ck, data_dir, scratch):
    path, faults, control = build_broken(data_dir, scratch)
    code, text = run([PY, os.path.join(HERE, "validate.py"), path,
                      "--data", data_dir, "--max-errors", "200"])
    ck.report("broken file is rejected (exit 1)", code == 1, "exit %d" % code)
    for name, expect in faults:
        ck.report("  caught: %s" % name, expect in text, "")
    ck.report("  caught: duplicate case_id", "duplicate case_id" in text, "")
    ck.report("  caught: invalid JSON", "invalid JSON" in text, "")
    ck.report("  caught: missing lines", "no output line" in text, "")
    if os.path.exists(control):
        code, text = run([PY, os.path.join(HERE, "validate.py"), control,
                          "--data", data_dir, "--quiet"])
        ck.report("control file with a hand-written good line passes", code == 0,
                  text.strip().splitlines()[-1] if text.strip() else "")


def check_invented_figure(ck, data_dir, scratch, out_dir):
    """A figure that appears nowhere in the case must still be caught."""
    base = os.path.join(out_dir, os.path.basename(data_dir) + ".jsonl")
    if not os.path.exists(base):
        ck.report("invented figure is warned", False, "no baseline output")
        return
    rows = [json.loads(line) for line in read_jsonl_text(base)]
    target = rows[0]
    target = dict(target)
    target["reason"] = (
        "Alert %s raised the profile rule and £987,654.32 arrived in the window. "
        "No document on file explains the money movement, so the case goes to the MLRO."
        % (target["alert_ids"][0] if target["alert_ids"] else "n/a"))
    rows[0] = target
    path = os.path.join(scratch, "invented_figure.jsonl")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    code, text = run([PY, os.path.join(HERE, "validate.py"), path,
                      "--data", data_dir, "--strict", "--quiet"])
    ok = code == 1 and "not found in the case inputs" in text
    ck.report("invented figure is warned (and fails under --strict)", ok,
              "exit %d" % code)


def check_missing_cases(ck, data_dir, scratch, out_dir):
    src = os.path.join(out_dir, os.path.basename(data_dir) + ".jsonl")
    rows = read_jsonl_text(src)
    path = os.path.join(scratch, "short.jsonl")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(rows[:-3]) + "\n")
    code, text = run([PY, os.path.join(HERE, "validate.py"), path,
                      "--data", data_dir, "--quiet"])
    ok = code == 1 and "no output line" in text
    ck.report("truncated output rejected as missing cases", ok,
              text.strip().splitlines()[-1] if text.strip() else "")


def read_jsonl_text(path):
    with open(path, "r", encoding="utf-8") as fh:
        return [line.rstrip("\n") for line in fh if line.strip()]


def check_labels(ck, data_root):
    path = os.path.join(HERE, "labels.json")
    if not os.path.exists(path):
        ck.report("labels.json exists", False, path)
        return
    with open(path, "r", encoding="utf-8") as fh:
        labels = json.load(fh)
    codes = {
        "CLOSE": {"COLLECTION_DOCUMENTED", "BUSINESS_RECORDS_RECONCILE", "DOCUMENTED_EVENT",
                  "INVOICE_MATCHES", "OWN_ACCOUNT", "GROUP_COMPANY",
                  "THIRD_PARTY_DOCUMENTED", "REFUND_OF_EARLIER_PAYMENT",
                  "RETURNING_CUSTOMER", "LIST_MATCH_DIFFERENT_PARTY", "WITHIN_PROFILE"},
        "RFI": {"RFI_PURPOSE_DOCUMENTS", "RFI_BUSINESS_RECORDS", "RFI_SOURCE_OF_FUNDS",
                "RFI_COUNTERPARTY_DETAILS", "RFI_UPDATED_PROFILE"},
        "ESCALATE": {"ESC_MULE_ACTIVITY", "ESC_STRUCTURING", "ESC_UNEXPLAINED_FUNDS",
                     "ESC_PASS_THROUGH", "ESC_INVOICE_MISMATCH", "ESC_HIGH_RISK_CORRIDOR",
                     "ESC_ACCOUNT_MISUSE", "ESC_THIRD_PARTY_FUNDING", "ESC_EARLY_REDEMPTION",
                     "ESC_LISTED_PARTY"},
    }
    for inst in sorted(labels["institutions"]):
        block = labels["institutions"][inst]
        data_dir = os.path.join(data_root, inst)
        cases = {r["case_id"]: r for r in read_cases(data_dir)}
        docs = {}
        for row in load_jsonl(os.path.join(data_dir, "evidence.jsonl")):
            docs.setdefault(row["customer_id"], set()).add(row["type"])
        signatures = {}
        for case in cases.values():
            signatures.setdefault(tuple(sorted(docs.get(case["customer_id"], set()))), 0)
            signatures[tuple(sorted(docs.get(case["customer_id"], set())))] += 1

        covered = sum(e["cases"] for e in block["entries"])
        ck.report("labels %s: every case covered" % inst,
                  covered == len(cases) and block["cases"] == len(cases),
                  "%d/%d" % (covered, len(cases)))
        ck.report("labels %s: every combination listed" % inst,
                  len(block["entries"]) == len(signatures)
                  and {tuple(e["signature"]) for e in block["entries"]} == set(signatures),
                  "%d/%d" % (len(block["entries"]), len(signatures)))
        bad = [(e["id"], e["advice"]["reason_code"]) for e in block["entries"]
               if e["advice"]["reason_code"] not in codes[e["advice"]["verdict"]]]
        ck.report("labels %s: reason_code belongs to verdict" % inst, not bad, str(bad[:3]))
        bad_rule = [(e["id"], r["reason_code"]) for e in block["entries"]
                    for r in e["rule_advice"]
                    if r["reason_code"] not in codes[r["verdict"]]]
        ck.report("labels %s: rule_advice codes valid" % inst, not bad_rule, str(bad_rule[:3]))
        mixed = [e["id"] for e in block["entries"]
                 if sum(e["heuristic_mix"].values()) != e["cases"]]
        ck.report("labels %s: heuristic_mix sums to cases" % inst, not mixed, str(mixed[:3]))


def check_repro_failure(ck, scratch):
    fake = os.path.join(scratch, "fakerepo")
    if os.path.isdir(fake):
        shutil.rmtree(fake)
    os.makedirs(os.path.join(fake, "tools"))
    os.makedirs(os.path.join(fake, "system"))
    for inst in ("bank", "payments_fx", "emoney", "investment"):
        os.makedirs(os.path.join(fake, "data", "institutions", inst))
        with open(os.path.join(fake, "data", "institutions", inst, "cases.jsonl"), "w") as fh:
            fh.write('{"case_id":"X-1"}\n')
    shutil.copy(os.path.join(HERE, "repro.sh"), os.path.join(fake, "tools", "repro.sh"))
    stub = os.path.join(fake, "system", "run")
    with open(stub, "w", encoding="utf-8") as fh:
        fh.write("""#!/bin/sh
python3 - "$2" <<'PY'
import os, sys, uuid
out = sys.argv[1]
os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
with open(out, 'w') as fh:
    fh.write('{"case_id":"X-1","nonce":"%s"}\\n' % uuid.uuid4())
PY
""")
    os.chmod(stub, 0o755)
    code, text = run([os.path.join(fake, "tools", "repro.sh"), "3"], cwd=fake)
    ok = code == 1 and "first difference" in text and "REPRO FAIL" in text
    ck.report("repro.sh detects non determinism", ok,
              "exit %d" % code)


def main(argv):
    data_root = os.path.join(ROOT, "data", "institutions")
    out_dir = os.path.join(ROOT, "output")
    args = list(argv[1:])
    i = 0
    while i < len(args):
        if args[i] == "--data":
            i += 1
            data_root = args[i]
        elif args[i] == "--output":
            i += 1
            out_dir = args[i]
        else:
            sys.stderr.write("selftest: unknown argument %s\n" % args[i])
            return 2
        i += 1

    scratch = os.environ.get("TMPDIR") or "/tmp"
    scratch = os.path.join(scratch, "tools-selftest")
    if os.path.isdir(scratch):
        shutil.rmtree(scratch)
    os.makedirs(scratch)

    ck = Checker()
    print("selftest: tools in %s" % HERE)
    print("")
    check_baseline(ck, data_root, out_dir)
    print("")
    bank_dir = os.path.join(data_root, "bank")
    check_broken(ck, bank_dir, scratch)
    print("")
    check_missing_cases(ck, bank_dir, scratch, out_dir)
    check_invented_figure(ck, bank_dir, scratch, out_dir)
    print("")
    check_labels(ck, data_root)
    print("")
    check_repro_failure(ck, scratch)
    print("")
    print("%d/%d checks passed" % (ck.checks - ck.failures, ck.checks))
    return 0 if ck.failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
