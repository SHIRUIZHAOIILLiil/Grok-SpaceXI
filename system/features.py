"""Build the per-case feature dict. Standard library only.

Owner: B.  Signature is frozen in CONTRACT.md — do not change it.
"""
import json
import os

_LOADED = {}


def _load(institution_dir):
    """Load customers and transactions once per institution folder."""
    key = os.path.abspath(institution_dir)
    if key in _LOADED:
        return _LOADED[key]
    customers = {}
    path = os.path.join(institution_dir, "customers.jsonl")
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                row = json.loads(line)
                customers[row["customer_id"]] = row
    tx_by_customer = {}
    path = os.path.join(institution_dir, "transactions.jsonl")
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                row = json.loads(line)
                tx_by_customer.setdefault(row["customer_id"], []).append(row)
    _LOADED[key] = (customers, tx_by_customer)
    return _LOADED[key]


def _in_window(row, window):
    if not window:
        return True
    booked = (row.get("booked_at") or "")[:10]
    return window.get("from", "") <= booked <= window.get("to", "9999-12-31")


def build_case(institution_dir, case, index):
    customers, tx_by_customer = _load(institution_dir)
    customer_id = case["customer_id"]
    customer = customers.get(customer_id, {})
    window = case.get("review_window") or {}
    tx = [r for r in tx_by_customer.get(customer_id, []) if _in_window(r, window)]

    alerts = []
    for alert in case.get("alerts", []):
        entry = dict(alert)
        entry.setdefault("transaction_ids", [])
        alerts.append(entry)

    docs = index.docs(customer_id)
    by_type = {}
    for doc in docs:
        by_type.setdefault(doc["type"], []).append(doc)

    return {
        "case_id": case["case_id"],
        "institution": case.get("institution") or os.path.basename(
            os.path.abspath(institution_dir)),
        "customer_id": customer_id,
        "review_window": window,
        "alerts": alerts,
        "rules": sorted({a.get("rule_id") for a in alerts if a.get("rule_id")}),
        "customer": customer,
        "tx_in_window": tx,
        "tx_by_id": {r["transaction_id"]: r for r in tx},
        "evidence": docs,
        "docs_by_type": by_type,
        "signature": sorted(by_type),
        "internal_matches": [],
        "previous_reviews": index.previous_reviews(customer_id),
        "held_payment": case.get("held_payment"),
    }
