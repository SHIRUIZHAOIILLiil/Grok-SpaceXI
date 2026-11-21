#!/usr/bin/env python3
"""Queryable audit index for a finished run. Standard library only.

    python3 tools/audit.py build
    python3 tools/audit.py why BK-CS109535
    python3 tools/audit.py docs
    python3 tools/audit.py rules
    python3 tools/audit.py sql "select verdict, count(*) from cases group by 1"

The scored pipeline never touches this file: `system/run` reads one folder and
writes one file, with no state between runs. This index is the other half of
the story - a durable, queryable record of what the system decided and why,
which is what an audited process actually needs and what a JSONL folder cannot
give you on its own.
"""
import argparse
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "institutions")
OUTPUT = os.path.join(ROOT, "output")
DB = os.path.join(ROOT, "build", "audit.db")

SCHEMA = """
create table if not exists cases (
  case_id text primary key, institution text, customer_id text, customer_name text,
  kind text, verdict text, reason_code text, reason text, review_from text, review_to text);
create table if not exists alerts (
  alert_id text primary key, case_id text, rule_id text, rule_name text, message text);
create table if not exists documents (
  doc_id text primary key, institution text, customer_id text, type text, title text, dated text);
create table if not exists transactions (
  transaction_id text primary key, customer_id text, booked_at text, direction text,
  channel text, amount_gbp real, counterparty_name text, counterparty_country text);
create table if not exists citations (
  case_id text, evidence_id text, kind text);
create index if not exists ix_alerts_case on alerts(case_id);
create index if not exists ix_cit_case on citations(case_id);
create index if not exists ix_doc_cust on documents(customer_id);
"""


def rows(path):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def build():
    if os.path.exists(DB):
        os.remove(DB)
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    db = sqlite3.connect(DB)
    db.executescript(SCHEMA)
    for inst in sorted(os.listdir(DATA)):
        base = os.path.join(DATA, inst)
        if not os.path.isdir(base):
            continue
        customers = {c["customer_id"]: c for c in rows(os.path.join(base, "customers.jsonl"))}
        doc_ids = {}
        for doc in rows(os.path.join(base, "evidence.jsonl")):
            doc_ids[doc["doc_id"]] = doc.get("type")
            db.execute("insert or replace into documents values (?,?,?,?,?,?)",
                       (doc["doc_id"], inst, doc["customer_id"], doc.get("type"),
                        doc.get("title"), doc.get("dated")))
        for tx in rows(os.path.join(base, "transactions.jsonl")):
            db.execute("insert or replace into transactions values (?,?,?,?,?,?,?,?)",
                       (tx["transaction_id"], tx["customer_id"], tx.get("booked_at"),
                        tx.get("direction"), tx.get("channel"), tx.get("amount_gbp"),
                        tx.get("counterparty_name"), tx.get("counterparty_country")))
        cases = {c["case_id"]: c for c in rows(os.path.join(base, "cases.jsonl"))}
        tx_ids = set()
        list_ids = set()
        for entry in rows(os.path.join(base, "internal_list.jsonl")):
            list_ids.add(entry["entry_id"])
        alerts = {}
        for alert in rows(os.path.join(base, "alerts.jsonl")):
            alerts.setdefault(alert["case_id"], []).append(alert)
            db.execute("insert or replace into alerts values (?,?,?,?,?)",
                       (alert["alert_id"], alert["case_id"], alert.get("rule_id"),
                        alert.get("rule_name"), alert.get("message")))
        for tx in rows(os.path.join(base, "transactions.jsonl")):
            tx_ids.add(tx["transaction_id"])
        out = os.path.join(OUTPUT, inst + ".jsonl")
        for decided in rows(out):
            case = cases.get(decided["case_id"])
            cust_id = (case or {}).get("customer_id", "")
            cust = customers.get(cust_id, {})
            window = (case or {}).get("review_window") or {}
            db.execute("insert or replace into cases values (?,?,?,?,?,?,?,?,?,?)",
                       (decided["case_id"], inst, cust_id, cust.get("name"),
                        cust.get("kind"), decided["verdict"], decided["reason_code"],
                        decided["reason"], window.get("from"), window.get("to")))
            for ev in decided.get("evidence") or []:
                if ev in doc_ids:
                    kind = "document"
                elif ev in tx_ids:
                    kind = "transaction"
                elif ev in list_ids:
                    kind = "list_entry"
                else:
                    kind = "other"
                db.execute("insert into citations values (?,?,?)", (decided["case_id"], ev, kind))
    db.commit()
    n = db.execute("select count(*) from cases").fetchone()[0]
    c = db.execute("select count(*) from citations").fetchone()[0]
    db.close()
    print("built %s: %d cases, %d citations" % (DB, n, c))


def show(cur):
    cols = [d[0] for d in cur.description]
    data = cur.fetchall()
    widths = [len(c) for c in cols]
    for row in data:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(str(val)))
    print("  ".join(c.ljust(widths[i]) for i, c in enumerate(cols)))
    print("  ".join("-" * w for w in widths))
    for row in data:
        print("  ".join(str(v).ljust(widths[i]) for i, v in enumerate(row)))
    print("(%d rows)" % len(data))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "why", "docs", "rules", "sql"])
    ap.add_argument("arg", nargs="?")
    args = ap.parse_args()
    if args.cmd == "build":
        return build()
    db = sqlite3.connect(DB)
    cur = db.cursor()
    if args.cmd == "why":
        cur.execute("select verdict, reason_code, reason from cases where case_id = ?",
                    (args.arg,))
        show(cur)
        cur.execute("select rule_id, message from alerts where case_id = ? order by rule_id",
                    (args.arg,))
        show(cur)
        cur.execute("""select c.evidence_id, d.type, d.title
                       from citations c left join documents d on d.doc_id = c.evidence_id
                       where c.case_id = ? order by c.evidence_id""", (args.arg,))
        show(cur)
    elif args.cmd == "docs":
        cur.execute("""select coalesce(d.type, 'transaction') as kind, count(*) as cited
                       from citations c left join documents d on d.doc_id = c.evidence_id
                       group by 1 order by cited desc limit 15""")
        show(cur)
    elif args.cmd == "rules":
        cur.execute("""select a.rule_id, sum(c.verdict = 'CLOSE') as close,
                              sum(c.verdict = 'RFI') as rfi,
                              sum(c.verdict = 'ESCALATE') as escalate, count(*) as n
                       from alerts a join cases c on c.case_id = a.case_id
                       group by 1 order by n desc""")
        show(cur)
    elif args.cmd == "sql":
        cur.execute(args.arg)
        show(cur)
    db.close()


if __name__ == "__main__":
    sys.exit(main())
