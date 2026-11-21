#!/usr/bin/env python3
"""Load the audit index into Neon over plain HTTPS. No driver, no packages.

Neon speaks SQL over HTTP, so the standard library is enough:

    POST https://<endpoint-host>/sql
    Neon-Connection-String: postgresql://...
    {"query": "select 1", "params": []}

The connection string is read from `.neon_url` or `$NEON_URL` and never printed.

    python3 tools/neon_sync.py load          # create tables, replace contents
    python3 tools/neon_sync.py why BK-CS109535
    python3 tools/neon_sync.py docs
    python3 tools/neon_sync.py rules
    python3 tools/neon_sync.py sql "select verdict, count(*) from cases group by 1"
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "institutions")
OUTPUT = os.path.join(ROOT, "output")

DDL = [
    """create table if not exists cases (
         case_id text primary key, institution text, customer_id text, customer_name text,
         kind text, verdict text, reason_code text, reason text,
         review_from text, review_to text)""",
    """create table if not exists alerts (
         alert_id text primary key, case_id text, rule_id text, rule_name text,
         message text, measured jsonb)""",
    """create table if not exists documents (
         doc_id text primary key, institution text, customer_id text, type text,
         title text, dated text)""",
    """create table if not exists transactions (
         transaction_id text primary key, customer_id text, booked_at text, direction text,
         channel text, amount_gbp double precision, counterparty_name text,
         counterparty_country text)""",
    """create table if not exists citations (
         case_id text, evidence_id text, kind text)""",
    "create index if not exists ix_alerts_case on alerts(case_id)",
    "create index if not exists ix_cit_case on citations(case_id)",
    "create index if not exists ix_doc_cust on documents(customer_id)",
]


def connection_string():
    value = os.environ.get("NEON_URL")
    if value:
        return value.strip()
    path = os.path.join(ROOT, ".neon_url")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read().strip()
    raise SystemExit("no connection string: set NEON_URL or write .neon_url")


def endpoint(dsn):
    host = dsn.split("@", 1)[-1].split("/", 1)[0]
    return "https://" + host + "/sql"


def query(sql, params=None, dsn=None, timeout=90):
    dsn = dsn or connection_string()
    body = json.dumps({"query": sql, "params": params or []}).encode("utf-8")
    request = urllib.request.Request(endpoint(dsn), data=body, headers={
        "Neon-Connection-String": dsn,
        "Content-Type": "application/json",
        "User-Agent": "casefile-audit/1.0",
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400]
        raise SystemExit("neon error %s: %s" % (exc.code, detail))


def rows(path):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def collect():
    tables = {"cases": [], "alerts": [], "documents": [], "transactions": [], "citations": []}
    for inst in sorted(os.listdir(DATA)):
        base = os.path.join(DATA, inst)
        if not os.path.isdir(base):
            continue
        customers = {c["customer_id"]: c for c in rows(os.path.join(base, "customers.jsonl"))}
        doc_ids = set()
        for doc in rows(os.path.join(base, "evidence.jsonl")):
            doc_ids.add(doc["doc_id"])
            tables["documents"].append([doc["doc_id"], inst, doc["customer_id"], doc.get("type"),
                                        doc.get("title"), doc.get("dated")])
        tx_ids = set()
        for tx in rows(os.path.join(base, "transactions.jsonl")):
            tx_ids.add(tx["transaction_id"])
            tables["transactions"].append([tx["transaction_id"], tx["customer_id"],
                                           tx.get("booked_at"), tx.get("direction"),
                                           tx.get("channel"), tx.get("amount_gbp"),
                                           tx.get("counterparty_name"), tx.get("counterparty_country")])
        cases = {c["case_id"]: c for c in rows(os.path.join(base, "cases.jsonl"))}
        list_ids = {e["entry_id"] for e in rows(os.path.join(base, "internal_list.jsonl"))}
        for alert in rows(os.path.join(base, "alerts.jsonl")):
            tables["alerts"].append([alert["alert_id"], alert["case_id"], alert.get("rule_id"),
                                     alert.get("rule_name"), alert.get("message"),
                                     json.dumps(alert.get("measured") or {})])
        for decided in rows(os.path.join(OUTPUT, inst + ".jsonl")):
            case = cases.get(decided["case_id"]) or {}
            cust = customers.get(case.get("customer_id"), {})
            window = case.get("review_window") or {}
            tables["cases"].append([decided["case_id"], inst, case.get("customer_id"),
                                    cust.get("name"), cust.get("kind"), decided["verdict"],
                                    decided["reason_code"], decided["reason"],
                                    window.get("from"), window.get("to")])
            for ev in decided.get("evidence") or []:
                kind = ("document" if ev in doc_ids else "transaction" if ev in tx_ids
                        else "list_entry" if ev in list_ids else "other")
                tables["citations"].append([decided["case_id"], ev, kind])
    return tables


SHAPES = {
    "cases": "case_id text, institution text, customer_id text, customer_name text, kind text, "
             "verdict text, reason_code text, reason text, review_from text, review_to text",
    "alerts": "alert_id text, case_id text, rule_id text, rule_name text, message text, measured jsonb",
    "documents": "doc_id text, institution text, customer_id text, type text, title text, dated text",
    "transactions": "transaction_id text, customer_id text, booked_at text, direction text, "
                    "channel text, amount_gbp double precision, counterparty_name text, "
                    "counterparty_country text",
    "citations": "case_id text, evidence_id text, kind text",
}


def load():
    dsn = connection_string()
    for statement in DDL:
        query(statement, dsn=dsn)
        print("  ddl ok:", statement.split("\n")[0][:58])
    tables = collect()
    for name in ["citations", "alerts", "documents", "transactions", "cases"]:
        payload = json.dumps(tables[name])
        query("delete from %s" % name, dsn=dsn)
        if not payload or payload == "[]":
            print("  %-12s 0 rows" % name)
            continue
        query("insert into %s select * from jsonb_to_recordset($1::jsonb) as t(%s)"
              % (name, SHAPES[name]), [payload], dsn=dsn)
        print("  %-12s %d rows" % (name, len(tables[name])))
    result = query("select count(*)::int as n from cases", dsn=dsn)
    print("cases in neon:", result["rows"][0]["n"])


def show(result):
    fields = [f["name"] for f in result.get("fields") or []]
    data = result.get("rows") or []
    if not fields:
        print(result)
        return
    widths = [len(f) for f in fields]
    for row in data:
        for i, f in enumerate(fields):
            widths[i] = max(widths[i], len(str(row.get(f))))
    print("  ".join(f.ljust(widths[i]) for i, f in enumerate(fields)))
    print("  ".join("-" * w for w in widths))
    for row in data:
        print("  ".join(str(row.get(f)).ljust(widths[i]) for i, f in enumerate(fields)))
    print("(%d rows)" % len(data))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["load", "why", "docs", "rules", "sql"])
    ap.add_argument("arg", nargs="?")
    args = ap.parse_args()
    if args.cmd == "load":
        return load()
    if args.cmd == "why":
        show(query("select verdict, reason_code, reason from cases where case_id = $1", [args.arg]))
        show(query("select rule_id, message from alerts where case_id = $1 order by rule_id", [args.arg]))
        show(query("""select c.evidence_id, d.type, d.title from citations c
                      left join documents d on d.doc_id = c.evidence_id
                      where c.case_id = $1 order by c.evidence_id""", [args.arg]))
    elif args.cmd == "docs":
        show(query("""select coalesce(d.type, c.kind) as kind, count(*)::int as cited
                      from citations c left join documents d on d.doc_id = c.evidence_id
                      group by 1 order by cited desc limit 12"""))
    elif args.cmd == "rules":
        show(query("""select a.rule_id,
                             sum(case when c.verdict = 'CLOSE' then 1 else 0 end)::int as close,
                             sum(case when c.verdict = 'RFI' then 1 else 0 end)::int as rfi,
                             sum(case when c.verdict = 'ESCALATE' then 1 else 0 end)::int as escalate,
                             count(*)::int as n
                      from alerts a join cases c on c.case_id = a.case_id
                      group by 1 order by n desc"""))
    elif args.cmd == "sql":
        show(query(args.arg))


if __name__ == "__main__":
    sys.exit(main())
