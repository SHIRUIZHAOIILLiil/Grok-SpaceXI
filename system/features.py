"""Build the per-case feature dict. Standard library only.

Owner: B.  Signature is frozen in CONTRACT.md - do not change it.

Two things this module is responsible for:

1. ``internal_matches`` - for every TM22 alert, the internal list entry, the
   party the payment actually went to, which fields match and which contradict.
   This is the only evidence a list-match verdict can rest on (POLICY.md: close
   only when the evidence shows a different party; escalate when the listed
   party is the counterparty or controls it; RFI when nothing settles it).
2. ``alert_documents`` - for every alert, the documents that mention its amount,
   counterparty, date or country, with the field each document matched.  This
   is the "explanatory document" locator built on ``evidence.Index``.
"""
import json
import os
import re

import evidence
import extract

_LOADED = {}
_LIST = {}

_ENTRY_IN_MESSAGE = re.compile(r"\b[A-Z]{2}-L\d+\b")

# Fields a TM22 alert can claim a match on, keyed by phrase in measured.matched_on.
_CLAIM_FIELDS = (
    ("dob", ("date of birth", "month and year of birth", "dob")),
    ("address", ("address", "registered office", "residential")),
    ("company_number", ("company number",)),
    ("identifier", ("identifier", "swift", "internal case")),
    ("name", ("name",)),
)


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


def _load_list(institution_dir):
    """Internal list entries by entry_id, cached per institution folder."""
    key = os.path.abspath(institution_dir)
    if key not in _LIST:
        entries = {}
        for row in evidence._read_jsonl(os.path.join(institution_dir,
                                                     "internal_list.jsonl")):
            entries[row.get("entry_id")] = row
        _LIST[key] = entries
    return _LIST[key]


def _in_window(row, window):
    if not window:
        return True
    booked = (row.get("booked_at") or "")[:10]
    return window.get("from", "") <= booked <= window.get("to", "9999-12-31")


# ---------------------------------------------------------------------------
# Small parsing helpers
# ---------------------------------------------------------------------------

def _table_rows(text):
    """Markdown tables in a document as a list of dicts keyed by the header."""
    rows = []
    header = None
    for line in (text or "").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):
            continue
        if header is None:
            header = [c.lower() for c in cells]
            continue
        rows.append(dict(zip(header, cells)))
    return rows


def _registered_office(text):
    m = re.search(r"\*\*Registered office:\*\*\s*(.+)", text or "")
    return m.group(1).strip() if m else None


def _company_number(text):
    m = re.search(r"\*\*Company number:\*\*\s*([0-9A-Za-z]+)", text or "")
    return m.group(1).strip() if m else None


def _company_name(text, title):
    """Company a register document belongs to (heading or **Company:** field)."""
    m = re.search(r"\*\*Company:\*\*\s*(.+)", text or "")
    if m:
        return m.group(1).strip()
    if title:
        m = re.search(r"\bfor\s+(.+)$", title.strip())
        if m:
            return m.group(1).strip()
    return None


def _claimed_fields(alert):
    """Which fields the TM22 alert says it matched on."""
    claim = (alert.get("measured") or {}).get("matched_on") or ""
    claim = claim.lower()
    claimed = []
    for field, phrases in _CLAIM_FIELDS:
        if any(p in claim for p in phrases):
            claimed.append(field)
    if not claimed and "name" in claim:
        claimed.append("name")
    return claimed


def _party_name(alert):
    """The counterparty named by a TM22 alert, without the role commentary."""
    measured = alert.get("measured") or {}
    party = (measured.get("matched_party") or "").strip()
    if party:
        # "Robin Fernworth, director of Rayhurst Consulting Ltd until 7 Aug 2026"
        head = party.split(",")[0].strip()
        return head or party
    msg = alert.get("message") or ""
    m = re.search(r"Matched party:\s*([^.,]+)", msg)
    if m:
        return m.group(1).strip()
    return ""


def _subjects(customer, docs, tx_names):
    """Every identity the case file speaks about, with the fields it states.

    Returns dicts with ``role``, ``name``, ``dob`` (``(y, m)`` or ``(y, m, d)``),
    ``address``, ``company_number``, ``identifiers`` and ``doc_ids``.
    """
    subjects = [{
        "role": "customer",
        "name": customer.get("name"),
        "dob": evidence.dob_tuple(customer.get("date_of_birth")),
        "address": customer.get("address"),
        "company_number": customer.get("company_number"),
        "identifiers": {},
        "doc_ids": [],
    }]
    for name in tx_names:
        subjects.append({
            "role": "counterparty", "name": name, "dob": None, "address": None,
            "company_number": None, "identifiers": {}, "doc_ids": [],
        })
    for doc in docs:
        text = doc.get("text") or ""
        dtype = doc.get("type")
        doc_id = doc.get("doc_id")
        office = _registered_office(text)
        number = _company_number(text)
        if dtype in ("company_register_extract", "significant_control_register",
                     "group_structure"):
            company_name = _company_name(text, doc.get("title"))
            for row in _table_rows(text):
                name = (row.get("officer") or row.get("person")
                        or row.get("person with significant control")
                        or row.get("company"))
                if not name:
                    continue
                born = row.get("born") or ""
                subjects.append({
                    "role": "officer", "name": name,
                    "dob": evidence.parse_month_year(born) if born else None,
                    "address": office, "company_number": number,
                    "identifiers": {}, "doc_ids": [doc_id],
                })
            if office or company_name:
                subjects.append({
                    "role": "company", "name": company_name, "dob": None,
                    "address": office, "company_number": number,
                    "identifiers": {}, "doc_ids": [doc_id],
                })
            continue
        # A document that names a person and states a date of birth (gift letter,
        # loan agreement, letter from the customer) identifies that person.
        dob = evidence.parse_dob(text)
        if not dob and doc.get("type") == "gift_letter":
            # A gift letter names the giver and states their date of birth in
            # prose ("I, X, born 10 July 1997, confirm ..."), which the local
            # pattern misses. The model may only supply a verbatim quote, and the
            # quote is parsed here, so a wrong answer changes nothing.
            dob = extract.date_of_birth(text)
        if dob:
            m = re.search(r"\bI,\s*([A-Z][^,\n]{2,60}),", text)
            name = m.group(1).strip() if m else None
            if name is None:
                m = re.search(r"#\s*[^\n]*?\bfrom\s+([A-Z][^,\n]{2,60})", text)
                name = m.group(1).strip() if m else None
            if name:
                subjects.append({
                    "role": "person", "name": name, "dob": dob,
                    "address": None, "company_number": None,
                    "identifiers": {}, "doc_ids": [doc_id],
                })
    return subjects


def _compare(entry, subject):
    """Compare one list entry with one subject.

    Returns ``(matched_on, differences, compared)`` - the fields that agree, the
    fields that disagree (with both values) and how many fields could be
    compared at all.
    """
    entry_name = entry.get("name")
    entry_dob = evidence.dob_tuple(entry.get("date_of_birth"))
    entry_addr = entry.get("address")
    entry_ids = entry.get("identifiers") or {}

    matched, diffs, compared = [], [], 0

    name = subject.get("name")
    name_same = False
    if entry_name and name:
        compared += 1
        if evidence.names_match(entry_name, name):
            matched.append("name")
            name_same = True
        else:
            diffs.append({"field": "name", "entry": entry_name, "party": name})

    dob = subject.get("dob")
    # A date of birth only identifies the entry's person when the names agree:
    # an officer with a different name has a different date of birth by
    # definition, and recording that as a "difference" would mislead the reader.
    if entry_dob and dob and (name_same or not entry_name or not name):
        compared += 1
        same_month = entry_dob[:2] == tuple(dob[:2])
        if same_month and (len(dob) == 2 or len(entry_dob) == 2
                           or entry_dob[2] == dob[2]):
            matched.append("dob")
        elif same_month:
            diffs.append({"field": "dob",
                          "entry": entry.get("date_of_birth"),
                          "party": "%04d-%02d-%02d" % (dob[0], dob[1], dob[2]),
                          "note": "same month and year, different day"})
        else:
            diffs.append({"field": "dob",
                          "entry": entry.get("date_of_birth"),
                          "party": ("%04d-%02d" % (dob[0], dob[1])
                                    if len(dob) == 2
                                    else "%04d-%02d-%02d" % (dob[0], dob[1], dob[2]))})

    addr = subject.get("address")
    if entry_addr and addr:
        compared += 1
        verdict = evidence.compare_address(entry_addr, addr)
        if verdict == "full":
            matched.append("address")
        elif verdict == "partial":
            matched.append("address")
            diffs.append({"field": "address", "entry": entry_addr, "party": addr,
                          "note": "same premises name, different unit or number"})
        else:
            diffs.append({"field": "address", "entry": entry_addr, "party": addr})

    number = subject.get("company_number")
    entry_number = entry.get("company_number") or _identifier_company_number(entry_ids)
    if entry_number and number:
        compared += 1
        if str(entry_number).strip().lower() == str(number).strip().lower():
            matched.append("company_number")
        else:
            diffs.append({"field": "company_number", "entry": str(entry_number),
                          "party": str(number)})

    for key in sorted(entry_ids):
        value = str(entry_ids[key] or "").strip()
        if not value:
            continue
        subject_values = subject.get("identifiers") or {}
        for skey in sorted(subject_values):
            other = str(subject_values[skey] or "").strip()
            if not other:
                continue
            compared += 1
            if value.lower() == other.lower():
                matched.append("identifier")
            else:
                diffs.append({"field": "identifier:" + key, "entry": value,
                              "party": other})
    return matched, diffs, compared


def _identifier_company_number(identifiers):
    for key in sorted(identifiers or {}):
        if "company" in key.lower():
            return identifiers[key]
    return None


def _hint(claim, matched, diffs):
    """same_party / different_party / unresolved, from matches and conflicts."""
    fields = set(matched)
    conflicted = {d["field"].split(":")[0] for d in diffs}
    if {"name", "dob"} <= fields:
        return "same_party"
    if "identifier" in fields or "company_number" in fields:
        return "same_party"
    if "name" in fields and "dob" in conflicted:
        return "different_party"
    if "address" in fields and ({"name", "dob"} & conflicted):
        return "different_party"
    missing = set(claim) - fields
    if missing & conflicted:
        return "different_party"
    return "unresolved"


def _identifier_hits(entry, alert, docs, tx_by_id):
    """Entry identifiers (internal case number, SWIFT) found in the case file.

    The list stores identifiers that are not names: a case reference quoted in a
    document, a SWIFT/BIC on a statement.  A hit is real evidence of the same
    party, so it is compared in both directions: the identifier value is looked
    for in the documents and in the counterparty account/reference of the
    transactions the alert fired on.
    """
    identifiers = entry.get("identifiers") or {}
    hits = []
    evidence_ids = set()
    for key in sorted(identifiers):
        value = str(identifiers[key] or "").strip().lower()
        if len(value) < 4:
            continue
        for doc in docs:
            if value in (doc.get("text_lower") or ""):
                hits.append("identifier")
                evidence_ids.add(doc.get("doc_id"))
        for tx_id in sorted(alert.get("transaction_ids") or []):
            row = tx_by_id.get(tx_id) or {}
            haystack = " ".join(str(row.get(k) or "") for k in
                                ("counterparty_account", "reference", "counterparty_name"))
            if value in haystack.lower():
                hits.append("identifier")
                evidence_ids.add(tx_id)
    return hits, sorted(x for x in evidence_ids if x)


def _tm22_match(alert, entry, customer, docs, tx_by_id):
    """One internal_matches record: entry, party, matched fields, differences."""
    tx_names = []
    for tx_id in sorted(alert.get("transaction_ids") or []):
        row = tx_by_id.get(tx_id)
        if row and row.get("counterparty_name"):
            tx_names.append(row["counterparty_name"])
    party = _party_name(alert)
    if party:
        tx_names.append(party)
    tx_names = sorted({n for n in tx_names if n})

    claim = _claimed_fields(alert)
    rank = {"counterparty": 0, "company": 1, "customer": 2, "person": 3,
            "officer": 4}
    best = None
    for subject in _subjects(customer, docs, tx_names):
        matched, diffs, compared = _compare(entry, subject)
        record = {
            "entry": entry,
            "alert_id": alert.get("alert_id"),
            "party": party or (tx_names[0] if tx_names else subject.get("name")),
            "subject": subject.get("name"),
            "matched_on": sorted(set(matched)),
            "differences": diffs,
            "compared_fields": compared,
            "relation": subject.get("role"),
            "evidence_ids": sorted({d for d in subject.get("doc_ids") or []}
                                   | set(alert.get("transaction_ids") or [])),
        }
        record["verdict_hint"] = _hint(claim, matched, diffs)
        key = (-len(set(matched)), -compared, rank.get(subject.get("role"), 9),
               len(diffs), subject.get("name") or "")
        if best is None or key < best[0]:
            best = (key, record)
    if best is None:
        return {
            "entry": entry, "alert_id": alert.get("alert_id"), "party": party,
            "matched_on": [], "differences": [], "compared_fields": 0,
            "relation": "unknown", "evidence_ids": list(
                alert.get("transaction_ids") or []),
            "verdict_hint": "unresolved",
        }
    record = best[1]
    record["claimed"] = claim
    ident_hits, ident_ids = _identifier_hits(entry, alert, docs, tx_by_id)
    if ident_hits:
        record["matched_on"] = sorted(set(record["matched_on"]) | {"identifier"})
        record["evidence_ids"] = sorted(set(record["evidence_ids"]) | set(ident_ids))
        record["verdict_hint"] = _hint(claim, record["matched_on"],
                                       record["differences"])
    return record


# ---------------------------------------------------------------------------
# Alert -> explanatory documents
# ---------------------------------------------------------------------------

def _alert_amounts(alert, tx_by_id):
    """Amounts the alert is actually about.

    Measured baselines and limits (``baseline_gbp``, ``limit_gbp``) describe the
    customer's declared profile, not the activity: searching for them makes a
    due diligence summary look like it explains the alert, so they are skipped.
    """
    amounts = set()
    for key in sorted(alert.get("measured") or {}):
        if not key.endswith("_gbp"):
            continue
        if any(skip in key for skip in ("baseline", "limit", "income", "declared",
                                        "expected")):
            continue
        try:
            amounts.add(round(float(alert["measured"][key]), 2))
        except (TypeError, ValueError):
            pass
    for tx_id in sorted(alert.get("transaction_ids") or []):
        row = tx_by_id.get(tx_id)
        if row:
            try:
                amounts.add(round(float(row.get("amount_gbp")), 2))
            except (TypeError, ValueError):
                pass
    return sorted(amounts)


def _alert_names(alert, tx_by_id):
    """Counterparties the alert names: transaction parties plus measured names."""
    names = set()
    for tx_id in sorted(alert.get("transaction_ids") or []):
        row = tx_by_id.get(tx_id)
        if row and row.get("counterparty_name"):
            names.add(row["counterparty_name"])
    party = _party_name(alert)
    if party:
        names.add(party)
    measured = alert.get("measured") or {}
    for key in sorted(measured):
        if key in ("fund", "counterparty", "payer", "payee", "merchant", "scheme"):
            value = re.sub(r"\s*\([^)]*\)", "", str(measured[key] or "")).strip()
            if len(value) >= 4:
                names.add(value)
    return sorted(names)


def _alert_date(alert):
    dates = evidence.parse_dates(alert.get("message") or "")
    return dates[0] if dates else None


def _alert_countries(alert, tx_by_id):
    countries = set()
    for tx_id in sorted(alert.get("transaction_ids") or []):
        row = tx_by_id.get(tx_id)
        if row and row.get("counterparty_country"):
            countries.add(row["counterparty_country"])
    return sorted(countries)


def _alert_documents(index, customer_id, alert, tx_by_id):
    """Documents that speak to one alert, best first, with the fields they match."""
    found = {}
    for amount in _alert_amounts(alert, tx_by_id):
        for doc in index.find_by_amount(customer_id, amount):
            found.setdefault(doc["doc_id"], {"doc": doc, "hits": set(),
                                             "amounts": set()})["hits"].add("amount")
            found[doc["doc_id"]]["amounts"].add(amount)
    for name in _alert_names(alert, tx_by_id):
        for doc in index.find_by_counterparty(customer_id, name):
            found.setdefault(doc["doc_id"], {"doc": doc, "hits": set(),
                                             "amounts": set()})["hits"].add("counterparty")
    date = _alert_date(alert)
    if date:
        for doc in index.find_by_date(customer_id, date):
            found.setdefault(doc["doc_id"], {"doc": doc, "hits": set(),
                                             "amounts": set()})["hits"].add("date")
    for country in _alert_countries(alert, tx_by_id):
        for doc in index.find_by_country(customer_id, country):
            found.setdefault(doc["doc_id"], {"doc": doc, "hits": set(),
                                             "amounts": set()})["hits"].add("country")
    out = []
    for doc_id in sorted(found):
        item = found[doc_id]
        doc = item["doc"]
        tag = doc.get("tag") or "unknown"
        weights = {"amount": 2, "counterparty": 2, "date": 1, "country": 1}
        score = sum(weights[h] for h in item["hits"])
        if tag == "background_kyc":
            score -= 1  # a KYC summary restates the profile; it explains nothing
        out.append({
            "doc_id": doc_id,
            "type": doc.get("type"),
            "tag": tag,
            "hits": sorted(item["hits"]),
            "amounts": sorted(item["amounts"]),
            "score": score,
        })
    out.sort(key=lambda d: (-d["score"], d["doc_id"]))
    return out


# ---------------------------------------------------------------------------
# build_case
# ---------------------------------------------------------------------------

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
    alerts.sort(key=lambda a: a.get("alert_id") or "")

    docs = index.docs(customer_id)
    by_type = {}
    for doc in docs:
        doc.setdefault("tag", "unknown")
        by_type.setdefault(doc["type"], []).append(doc)

    tx_by_id = {r["transaction_id"]: r for r in tx}

    # TM22 list matches.  Sorted by alert id, one record per list entry hit.
    entries = _load_list(institution_dir)
    matches = []
    for alert in alerts:
        if alert.get("rule_id") != "TM22":
            continue
        measured = alert.get("measured") or {}
        entry_id = measured.get("list_entry")
        if not entry_id:
            m = _ENTRY_IN_MESSAGE.search(alert.get("message") or "")
            entry_id = m.group(0) if m else None
        entry = entries.get(entry_id)
        if not entry:
            continue
        matches.append(_tm22_match(alert, entry, customer, docs, tx_by_id))

    alert_docs = {}
    for alert in alerts:
        alert_docs[alert.get("alert_id")] = _alert_documents(
            index, customer_id, alert, tx_by_id)

    tag_counts = {}
    for doc in docs:
        tag_counts[doc["tag"]] = tag_counts.get(doc["tag"], 0) + 1

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
        "tx_by_id": tx_by_id,
        "evidence": docs,
        "docs_by_type": by_type,
        "signature": sorted(by_type),
        "internal_matches": matches,
        "alert_documents": alert_docs,
        "tag_counts": tag_counts,
        "previous_reviews": index.previous_reviews(customer_id),
        "held_payment": case.get("held_payment"),
    }
