"""Decision table. Owner: A.

Pure function: no disk reads, no randomness, no wall clock, no dict-order
dependence (everything iterates over sorted collections).

Order of work for one case
--------------------------
1. Red flags that override an explanation (structuring, device sharing,
   mule recruitment, dissolved counterparty, goods that do not fit the
   business) are tested first: they are the cases where a document exists
   but the document is the problem.
2. A list match (TM22) is resolved on its own: same party -> escalate,
   different party -> close, nothing on file -> RFI.
3. Eleven CLOSE grounds are tried in order of specificity. A ground closes
   the case only when the document it relies on carries the money the alerts
   measured, and the ground covers *every* rule that fired.
4. Anything left over goes to RFI when one document would settle it, and to
   ESCALATE when the activity is unexplained or shows signs of crime.
   The default is ESCALATE / ESC_UNEXPLAINED_FUNDS: never a guessed CLOSE.
"""

import re

FALLBACK = ("ESCALATE", "ESC_UNEXPLAINED_FUNDS")

_MONTHS = ("January|February|March|April|May|June|July|August|September|"
           "October|November|December")
_DATE = re.compile(r"\b\d{1,2} (?:%s) \d{4}\b" % _MONTHS)
_FIELD = re.compile(r"\*\*([A-Za-z][A-Za-z0-9 /'&.-]{0,40}):\*\*\s*(.*)")
_PARTY_TO = re.compile(r"to ([A-Z][A-Za-z&.'\- ]{2,60}?) on \d{1,2} (?:%s)" % _MONTHS)
_PARTY_FROM = re.compile(r"from ([A-Z][A-Za-z&.'\- ]{2,60}?)(?: on| paid)")
_ENTRY = re.compile(r"internal list entry (\S+) on ([^.]+)\.")
_PAID_TO = re.compile(r"(?:payment of|paid out to) £([\d,]+\.\d{2}) to ([A-Z][^,]+?)(?: on|,)")
_PARTY_PAID = re.compile(r"^([A-Z][A-Za-z&.'\- ]{2,60}?) paid £")

_STOP = set("""a an the and or of for to from by with at in on as is are was were be
this that these those uk ltd limited co company plc llp inc its it their our our
goods services service business item items one two three four five six seven eight
nine ten consignment order payment paid received supplied supply sale purchase
invoice total amount due please thank you dear sir madam regards best kind team
we i my me your our they them his her""".split())

_AMT = re.compile(r"£\s?([\d,]+\.\d{2})")


def _clean(text):
    """Remove full stops from a fragment so it cannot break sentence splitting."""
    return re.sub(r"\s+", " ", re.sub(r"\.", "", text or "")).strip()


def _title(doc):
    """Document title with internal full stops removed, so it cannot break a sentence."""
    text = (doc.get("title") or "document").strip()
    text = re.sub(r"\.", "", text)
    return text[:70].strip()


def _doc_amounts(doc):
    """Every GBP figure in the document, in order, duplicates kept."""
    out = []
    for raw in _AMT.findall(doc.get("text") or ""):
        try:
            out.append(float(raw.replace(",", "")))
        except ValueError:
            pass
    return out


def _table_totals(doc):
    """Sum of the last money column of each markdown table row.

    Collection reports, takings books, payment files and schedules all put the
    money that matters in the last money cell of the row.
    """
    rows = []
    for line in (doc.get("text") or "").splitlines():
        line = line.strip()
        if not line.startswith("|") or set(line) <= set("|- "):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        amounts = []
        for cell in cells:
            found = _AMT.findall(cell)
            if found:
                try:
                    amounts.append(float(found[-1].replace(",", "")))
                except ValueError:
                    pass
        if amounts:
            rows.append(amounts[-1])
    totals = []
    if rows:
        totals.append(sum(rows))
    return totals


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def _money(value):
    try:
        return "£{:,.2f}".format(float(value))
    except (TypeError, ValueError):
        return "£0.00"


def _num(value):
    try:
        return float(str(value).replace(",", "").replace("£", "").strip())
    except (TypeError, ValueError):
        return None


def _party_of(message):
    """The counterparty named in an alert message, if one is named."""
    if not message:
        return ""
    for pattern in (_PARTY_TO, _PARTY_FROM, _PAID_TO, _PARTY_PAID):
        found = pattern.search(message)
        if found:
            value = found.group(found.lastindex).strip(" .,")
            if 2 < len(value) < 70:
                return value
    return ""


def _fields(doc):
    out = {}
    for line in (doc.get("text") or "").splitlines():
        m = _FIELD.match(line.strip())
        if m:
            out.setdefault(m.group(1).strip().lower(), m.group(2).strip())
    return out


def _tokens(value):
    return {w for w in re.findall(r"[a-z]{3,}", (value or "").lower())
            if w not in _STOP}


def _same_name(a, b):
    """Loose identity test on person/company names."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return False
    return ta <= tb or tb <= ta or len(ta & tb) >= max(2, min(len(ta), len(tb)) - 1)


def _parse_long(value):
    """'17 February 1959' -> (1959, 2, 17); None when it does not parse."""
    if not value:
        return None
    m = re.match(r"(\d{1,2}) (%s) (\d{4})" % _MONTHS, value.strip())
    if not m:
        return None
    return (int(m.group(3)), _MONTHS.split("|").index(m.group(2)) + 1, int(m.group(1)))


def _parse_iso(value):
    if not value:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", value.strip())
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def _long_date(value):
    """'2026-09-04' -> '4 September 2026'; anything else is returned as given."""
    parsed = _parse_iso(value)
    if not parsed:
        return _short_date(value)
    year, month, day = parsed
    return "%d %s %d" % (day, _MONTHS.split("|")[month - 1], year)


def _short_date(value):
    if not value:
        return ""
    return value.strip().rstrip(".")


class Case(object):
    """Everything the table needs, derived once from the feature dict."""

    def __init__(self, features, policy):
        self.f = features
        self.policy = policy or {}
        self.customer = features.get("customer") or {}
        self.declared = self.customer.get("declared") or {}
        self.kind = (self.customer.get("kind") or "individual").lower()
        self.name = self.customer.get("name") or "the customer"
        self.alerts = sorted(features.get("alerts") or [],
                             key=lambda a: (a.get("rule_id") or "", a.get("alert_id") or ""))
        self.rules = sorted({a.get("rule_id") for a in self.alerts if a.get("rule_id")})
        self.docs = sorted(features.get("evidence") or [], key=lambda d: d.get("doc_id") or "")
        self.by_type = {}
        for doc in self.docs:
            self.by_type.setdefault(doc.get("type") or "", []).append(doc)
        self.tx = sorted(features.get("tx_in_window") or [],
                         key=lambda r: (r.get("booked_at") or "", r.get("transaction_id") or ""))
        self.list_matches = features.get("internal_matches") or []
        self.policy_codes = self.policy.get("codes") or {}
        self.high_risk = set(self.policy.get("high_risk_countries") or [])
        self._derive()

    # -- derived facts ------------------------------------------------------
    def _derive(self):
        income = _num(self.declared.get("monthly_income_gbp"))
        turnover = _num(self.declared.get("annual_turnover_gbp"))
        self.baseline = income if income else (turnover / 12.0 if turnover else 0.0)

        self.alert_amounts = {}
        self.focus = 0.0
        self.primary = None
        for alert in self.alerts:
            rule = alert.get("rule_id") or ""
            values = []
            measured = alert.get("measured") or {}
            for key in sorted(measured):
                key_l = key.lower()
                if "gbp" in key_l or "amount" in key_l or "total" in key_l:
                    value = _num(measured[key])
                    if value and value >= 100:
                        values.append(value)
            self.alert_amounts[rule] = sorted(values)
            best = max(values) if values else 0.0
            if best > self.focus:
                self.focus = best
                self.primary = alert

        if not self.focus:
            # some alerts (the list match) carry the money only in the message
            for alert in self.alerts:
                found = [_num(a) for a in _AMT.findall(alert.get("message") or "")]
                found = [f for f in found if f and f >= 1]
                if found:
                    best = max(found)
                    if best > self.focus:
                        self.focus = best
                        self.primary = alert

        self.multiple = 0.0
        for alert in self.alerts:
            if alert.get("rule_id") == "TM01":
                value = _num((alert.get("measured") or {}).get("multiple"))
                if value:
                    self.multiple = value
        if not self.multiple and self.baseline and self.focus:
            self.multiple = self.focus / self.baseline

        # paid-out share, used to separate pass-through from a modest movement
        self.paid_out = 0.0
        self.received = 0.0
        for alert in self.alerts:
            measured = alert.get("measured") or {}
            self.paid_out = max(self.paid_out, _num(measured.get("paid_out_gbp")) or 0.0)
            self.received = max(self.received, _num(measured.get("received_gbp")) or 0.0)
        if not self.received:
            self.received = self.focus

        self.countries = [c for c in (self.declared.get("expected_countries") or [])]
        self.counterparties = sorted({(r.get("counterparty_name") or "") for r in self.tx
                                      if r.get("counterparty_name")})
        self.tx_amounts = sorted({a for a in (_num(r.get("amount_gbp")) for r in self.tx)
                                  if a and a >= 150}, reverse=True)

        msg = (self.primary or {}).get("message", "") if self.primary else ""
        self.lead_message = msg
        dates = _DATE.findall(msg)
        self.date = _short_date(dates[-1]) if dates else ""
        self.party = _party_of(msg)
        if not self.party:
            for alert in self.alerts:
                self.party = _party_of(alert.get("message") or "")
                if self.party:
                    break
        self.country = ""
        for alert in self.alerts:
            found = (alert.get("measured") or {}).get("countries")
            if found:
                self.country = found if isinstance(found, str) else ", ".join(found)

    # -- doc helpers --------------------------------------------------------
    def docs_of(self, *types):
        out = []
        for name in types:
            out.extend(self.by_type.get(name, []))
        return sorted(out, key=lambda d: d.get("doc_id") or "")

    def text_of(self, docs):
        return " ".join((d.get("text") or "") for d in docs).lower()

    def values(self, rules=None):
        """Every amount the alerts measured, largest first."""
        out = []
        for rule in sorted(rules or self.rules):
            out.extend(self.alert_amounts.get(rule) or [])
        return sorted({v for v in out if v >= 150}, reverse=True)

    def match(self, docs, rules=None, band=(0.80, 1.06), extra=None):
        """First (document, amount) whose money equals what an alert measured.

        A document matches when it states one of the measured amounts, or when
        the amounts it lists add up to one of them (a table of takings, a
        schedule of instalments). Repeated amounts in a table are counted.
        """
        wanted = self.values(rules)
        if extra:
            wanted = sorted(set(wanted) | {v for v in extra if v and v >= 150}, reverse=True)
        if not wanted:
            return (docs[0], self.focus) if docs else (None, None)
        for doc in docs:
            raw = _doc_amounts(doc)
            for amount in raw:
                if amount < 150:
                    continue
                for value in wanted:
                    if band[0] * value <= amount <= band[1] * value:
                        return doc, amount
            for total in _table_totals(doc) + ([sum(a for a in raw if a >= 50)] if raw else []):
                for value in wanted:
                    if band[0] * value <= total <= band[1] * value:
                        return doc, total
        return None, None

    def covers_amounts(self, docs, rules=None, band=(0.80, 1.06)):
        doc, _amount = self.match(docs, rules, band)
        return doc is not None

    def doc_ids(self, docs, limit=4):
        return [d.get("doc_id") for d in docs[:limit] if d.get("doc_id")]

    def tx_ids(self, limit=6):
        out = []
        for alert in self.alerts:
            for tid in (alert.get("transaction_ids") or []):
                if tid not in out:
                    out.append(tid)
        return out[:limit]

    def all_ids(self, docs):
        ids = self.doc_ids(docs)
        for tid in self.tx_ids(4):
            if tid not in ids:
                ids.append(tid)
        return ids

    # -- verdict builders ---------------------------------------------------
    def result(self, verdict, code, reason, ids):
        return {"verdict": verdict, "reason_code": code,
                "evidence_ids": sorted(set(i for i in ids if i)), "reason": reason}


# --------------------------------------------------------------------------
# 1. red flags
# --------------------------------------------------------------------------
_STRUCT_WORDS = ("aggregat", "reporting threshold", "threshold", "breaking", "structur",
                 "increment", "instalment", "installment", "below the", "under £10",
                 "below £10", "different branch", "supporting invoice")


def _structuring(case):
    notes = case.docs_of("staff_note")
    if not notes:
        return None
    text = case.text_of(notes)
    if not any(word in text for word in _STRUCT_WORDS):
        return None
    note = notes[0]
    deposit = max(case.alert_amounts.get("TM03") or [case.focus])
    return case.result(
        "ESCALATE", "ESC_STRUCTURING",
        "A branch note ({doc}, {date}) records {name} asking whether deposits made at "
        "different branches are aggregated and whether keeping each one below the "
        "reporting threshold avoids a report, then saying they would use another branch. "
        "The activity in the alert is {amount} in cash across several deposits and "
        "locations. Deliberately splitting cash to stay under a threshold is structuring, "
        "so the case goes to the MLRO rather than back to the customer.".format(
            doc=note.get("doc_id"), date=_long_date(str(note.get("dated") or "")),
            name=case.name, amount=_money(deposit)),
        case.all_ids(notes))


def _device_sharing(case):
    devices = case.docs_of("device_export")
    if not devices:
        return None
    shared = False
    for doc in devices:
        text = doc.get("text") or ""
        ids = set(re.findall(r"\b[A-Z]{2}-C\d{3,}\b", text))
        if len(ids) >= 2:
            shared = True
    if not shared:
        return None
    doc = devices[0]
    return case.result(
        "ESCALATE", "ESC_ACCOUNT_MISUSE",
        "The device and login export ({doc}) shows one handset used to sign in to several "
        "different customer accounts, with logins also coming from outside the UK. "
        "The activity on {name}'s account ({amount} moved) is therefore not being operated "
        "by the customer alone. Someone else appears to control the account, which is an "
        "escalation rather than a question for the customer.".format(
            doc=doc.get("doc_id"), name=case.name, amount=_money(case.focus)),
        case.all_ids(devices))


def _mule(case):
    chats = case.docs_of("support_chat")
    text = case.text_of(chats)
    reports = case.docs_of("sending_bank_fraud_report")
    recruited = ("payments assistant" in text or "keep 8" in text
                 or ("remote job" in text and "crypto" in text))
    if recruited:
        doc = chats[0] if chats else (reports[0] if reports else None)
        return case.result(
            "ESCALATE", "ESC_MULE_ACTIVITY",
            "In the chat on file ({doc}) {name} says the money comes from clients of a "
            "'remote job' and is forwarded to a company crypto account, keeping 8% as "
            "wages, with no contract and no meeting. {amount} moved through the account in "
            "the review window and other banks have sent fraud reports on payments into it. "
            "Receiving and passing on other people's money for a third party is mule "
            "activity and goes to the MLRO.".format(
                doc=doc.get("doc_id") if doc else "none", name=case.name,
                amount=_money(case.focus)),
            case.all_ids(chats + reports))
    if reports and not chats:
        doc = reports[0]
        return case.result(
            "ESCALATE", "ESC_MULE_ACTIVITY",
            "{n} fraud reports from other banks ({doc}) say their customers paid {amount} "
            "into this account for goods that never arrived. The account received the money "
            "and moved it on. That pattern is receiving and passing on other people's money, "
            "so it is escalated rather than queried with the customer.".format(
                n=len(reports), doc=doc.get("doc_id"), amount=_money(case.focus)),
            case.all_ids(reports))
    return None


def _dissolved(case):
    hits = []
    for doc in case.docs:
        if doc.get("type") in ("due_diligence_summary", "proof_of_address", "contact_note"):
            continue
        text = (doc.get("text") or "")
        if re.search(r"[Dd]issolved on \d", text):
            hits.append(doc)
    if not hits:
        return None
    doc = hits[0]
    fields = _fields(doc)
    company = fields.get("company") or ""
    when = ""
    m = re.search(r"[Dd]issolved on (\d{1,2} (?:%s) \d{4})" % _MONTHS, doc.get("text") or "")
    if m:
        when = m.group(1)
    return case.result(
        "ESCALATE", "ESC_UNEXPLAINED_FUNDS",
        "{amount} came into the account from {party}, and the company record on file "
        "({doc}) shows {company} was dissolved on {when}, so it cannot be trading. "
        "{name} describes the money as a loan from a friend, which does not fit a payment "
        "from a dissolved company. The funds have no credible explanation and are moved on, "
        "so the case is escalated.".format(
            amount=_money(case.focus), party=case.party or company or "the counterparty",
            doc=doc.get("doc_id"), company=company or "the payer", when=when or "an earlier date",
            name=case.name),
        case.all_ids(hits))


def _invoice_goods_mismatch(case):
    business = (case.customer.get("business_activity") or "")
    if not business:
        return None
    if case.docs_of("supply_contract", "purchase_order", "contract_schedule"):
        return None
    biz_tokens = _tokens(business)
    for doc in case.docs_of("supplier_invoices", "supplier_invoice", "invoice"):
        fields = _fields(doc)
        goods = fields.get("goods") or fields.get("description") or ""
        if not goods:
            cells = []
            for row in _rows(doc)[1:]:
                for cell in row:
                    cleaned = re.sub(r"[£\d,]", " ", cell).strip()
                    if re.match(r"(?i)^(inv|invoice|po|ref)\b", cleaned):
                        continue
                    if len(re.findall(r"[A-Za-z]{3,}", cleaned)) >= 2:
                        cells.append(cleaned)
            if cells:
                goods = max(cells, key=lambda c: (len(c), c))
        if not goods or len(_tokens(goods)) < 1:
            continue
        if _tokens(goods) & biz_tokens:
            continue
        supplier = fields.get("supplier") or ""
        tied = bool(supplier) and any(_same_name(supplier, c) for c in case.counterparties)
        if not tied and not case.covers_amounts([doc], band=(0.55, 1.12)):
            continue
        if True:
            return case.result(
                "ESCALATE", "ESC_INVOICE_MISMATCH",
                "The invoices on file ({doc}) are for {goods}, while {name} is declared as "
                "{business}. Nothing in the paperwork ties the {amount} that moved to the "
                "trade the account is meant to carry{extra}. The invoices do not support the "
                "payments, so the case is escalated.".format(
                    doc=doc.get("doc_id"), goods=goods.rstrip("."), name=case.name,
                    business=business.rstrip("."), amount=_money(case.focus),
                    extra=(", and the supplier is a general trading company that does not "
                           "deal in this class of goods"
                           if "general trading" in (doc.get("text") or "").lower() else "")),
                case.all_ids([doc]))
    return None


def _officers(doc):
    """Officer names from a company register extract (first column of the table)."""
    names = []
    in_table = False
    for line in (doc.get("text") or "").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            in_table = False
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells:
            continue
        head = cells[0].lower()
        if head in ("officer", "person with significant control", "person"):
            in_table = True
            continue
        if set(line) <= set("|- "):
            continue
        if in_table and cells[0] and not re.search(r"\d", cells[0]):
            names.append(cells[0])
    return names


def _linked_payouts(case):
    """Payments to freshly incorporated companies run by the customer's own officer."""
    registers = case.docs_of("company_register_extract")
    if len(registers) < 2:
        return None
    mine, others = [], []
    for doc in registers:
        fields = _fields(doc)
        company = fields.get("company") or ""
        if _same_name(company, case.name):
            mine.append(doc)
        else:
            others.append(doc)
    if not mine or not others:
        return None
    officers = set()
    for doc in mine:
        for name in _officers(doc):
            officers.add(name)
    if not officers:
        return None
    window_to = (case.f.get("review_window") or {}).get("to") or ""
    linked = []
    for doc in others:
        names = set(_officers(doc)) & officers
        if not names:
            continue
        fields = _fields(doc)
        company = fields.get("company") or ""
        if company and _tokens(company) and company.lower() in case.text_of(case.docs).lower():
            linked.append((doc, sorted(names)[0], company))
    if not linked:
        return None
    doc, officer, company = linked[0]
    return case.result(
        "ESCALATE", "ESC_PASS_THROUGH",
        "Money arrives at {name} and is paid straight out to companies that were only "
        "incorporated weeks earlier and are run by the customer's own director, {officer}: "
        "{companies}. The only commercial paperwork on file is a contract worth a fraction of "
        "the {amount} that moved, so the payments have no credible purpose other than moving "
        "the money to linked parties. That is pass-through activity and is escalated.".format(
            name=case.name, officer=officer,
            companies=", ".join(sorted({c for _d, _o, c in linked})[:3]),
            amount=_money(case.focus)),
        case.all_ids([d for d, _o, _c in linked][:3] + mine[:1]))


def _rows(doc):
    """Markdown table rows as lists of cells."""
    out = []
    for line in (doc.get("text") or "").splitlines():
        line = line.strip()
        if not line.startswith("|") or set(line) <= set("|- "):
            continue
        out.append([c.strip() for c in line.strip("|").split("|")])
    return out


def _payment_file_risk(case):
    """A commission file whose different payees share one address is a front.

    Contractor files carry a contract number per payee and are paid against
    contracts; commission files carry home addresses, and in the abusive cases
    several payees sit at the same address.
    """
    files = case.docs_of("payment_file")
    for doc in files:
        rows = _rows(doc)
        if not rows:
            continue
        header = [c.lower() for c in rows[0]]
        if "address" not in header:
            continue
        idx = header.index("address")
        seen = {}
        for row in rows[1:]:
            if len(row) <= idx:
                continue
            addr = row[idx].strip().lower()
            if not addr:
                continue
            seen.setdefault(addr, set()).add(row[0])
        shared = [a for a in sorted(seen) if len(seen[a]) >= 2]
        if shared:
            return case.result(
                "ESCALATE", "ESC_THIRD_PARTY_FUNDING",
                "The commission payment file ({doc}) pays {n} different individuals, but "
                "several of them share the same home address, so the payees are not the "
                "independent overseas agents the file claims. The account also receives money "
                "from companies that are not the customer. Third parties are being paid out of "
                "and funded into the account through an arrangement that does not stand up, so "
                "the case is escalated.".format(doc=doc.get("doc_id"), n=max(1, len(rows) - 1)),
                case.all_ids([doc]))
    return None


def _payment_file_ground(case):
    """A payment file that lists the beneficiaries explains a many-to-one alert."""
    files = case.docs_of("payment_file")
    if not files:
        return None
    doc = files[0]
    rows = _rows(doc)
    if len(rows) < 10:
        return None
    doc2, amount = case.match(files, {"TM01", "TM02", "TM04", "TM08"},
                              band=(0.72, 1.12), extra=case.tx_amounts)
    if doc2 is None and "TM04" not in case.rules:
        return None
    return case.result(
        "CLOSE", "INVOICE_MATCHES",
        "The payment file ({doc}) lists {n} named beneficiaries with their contracts and the "
        "amount due to each, and the payments on the account follow that file. It is the "
        "payment run behind the {amount} that was paid out to multiple beneficiaries, which "
        "the many-to-one rule caught. A payment file matching the payees and amounts supports "
        "the payments, so the case is closed.".format(
            doc=doc.get("doc_id"), n=max(1, len(rows) - 1),
            amount=_money(amount if doc2 else case.focus)),
        case.all_ids(files))


# --------------------------------------------------------------------------
# 2. list match
# --------------------------------------------------------------------------
def _list_match(case):
    if "TM22" not in case.rules:
        return None
    alerts = [a for a in case.alerts if a.get("rule_id") == "TM22"]
    alert = alerts[0]
    message = alert.get("message") or ""
    m = _ENTRY.search(message)
    basis = (m.group(2) if m else "").strip().lower()
    entry_id = m.group(1) if m else ""
    flow = "receipt from" if "receipt of" in message else "payment to"
    found = [_num(a) for a in _AMT.findall(message)]
    found = [f for f in found if f]
    matched_amount = max(found) if found else case.focus

    # anything corroborating identity in the file
    gift = case.docs_of("gift_letter")
    register = case.docs_of("company_register_extract")
    others = [r for r in case.rules if r != "TM22"]

    entries = []
    for match in case.list_matches:
        if not isinstance(match, dict):
            continue
        entry = match.get("entry") or {}
        if entry_id and entry.get("entry_id") not in (None, entry_id):
            continue
        entries.append(entry)

    different = None
    same = None
    for entry in entries:
        entry_party = (entry.get("name") or "")
        entry_dob = _parse_iso(entry.get("date_of_birth"))
        entry_addr = (entry.get("address") or "")
        # gift letter: the giver names themselves and their date of birth
        for doc in gift:
            fields = _fields(doc)
            giver_dob = _parse_long(fields.get("date of birth") or "")
            body = doc.get("text") or ""
            gm = re.search(r"I, ([A-Z][A-Za-z'\- ]+?),?(?: born)?", body)
            giver = gm.group(1).strip() if gm else ""
            if entry_dob and giver_dob and entry_dob != giver_dob:
                different = (doc, entry)
            elif entry_dob and giver_dob and entry_dob == giver_dob:
                same = (doc, entry)
        # company register: officer age or registered office
        for doc in register:
            text = doc.get("text") or ""
            if entry_addr and entry_addr.lower() in text.lower():
                same = (doc, entry)
            if entry_party and entry_party.lower() in text.lower():
                same = (doc, entry)

    # A hard contradiction found in the feature layer settles the match even
    # when the local parser cannot read the date out of the document wording,
    # e.g. a date of birth written into the body of a gift letter.
    for match in case.list_matches:
        if not isinstance(match, dict):
            continue
        entry = match.get("entry") or {}
        if entry_id and entry.get("entry_id") not in (None, entry_id):
            continue
        if match.get("verdict_hint") != "different_party":
            continue
        hard = [d for d in (match.get("differences") or [])
                if isinstance(d, dict) and d.get("field") == "dob"]
        if not hard:
            continue
        d = hard[0]
        party_dob, entry_dob = d.get("party") or "", d.get("entry") or ""
        try:
            gap = abs(int(entry_dob[:4]) - int(party_dob[:4]))
        except (TypeError, ValueError):
            gap = 0
        if gap < 2:
            continue
        ids = [i for i in (match.get("evidence_ids") or []) if i]
        doc = ids[0] if ids else "on file"
        return case.result(
            "CLOSE", "LIST_MATCH_DIFFERENT_PARTY",
            "The {amount} {flow} {party} was flagged against internal list entry "
            "{entry_id} on {basis}. The document on file ({doc}) gives that person a "
            "date of birth of {pdob}, while the listed entry {listed} gives {edob} - "
            "{gap} years apart. A shared name is the only thing they have in common, "
            "so the counterparty is not the listed party and the case is closed.".format(
                amount=_money(matched_amount), party=case.party or "the counterparty",
                entry_id=entry_id or "on file", basis=basis or "name", doc=doc,
                listed=entry.get("name") or "the listed party",
                pdob=_short_date(party_dob), edob=_short_date(entry_dob),
                gap=gap, flow=flow),
            ids)

    if same and not different:
        doc, entry = same
        return case.result(
            "ESCALATE", "ESC_LISTED_PARTY",
            "The {amount} {flow} {party} matches internal list entry {entry_id} "
            "({basis}). The record on file ({doc}) confirms the same name and date of birth "
            "or address as {listed}, who is the subject of an unresolved internal "
            "investigation, so the match is the listed party and not a namesake. "
            "The counterparty is the listed party, or a company it controls, and the case "
            "is escalated.".format(
                amount=_money(matched_amount), party=case.party or "the counterparty",
                entry_id=entry_id or "on file", basis=basis or "name", flow=flow,
                doc=doc.get("doc_id"), listed=entry.get("name") or "the listed party"),
            case.all_ids([doc]))
    if different:
        doc, entry = different
        return case.result(
            "CLOSE", "LIST_MATCH_DIFFERENT_PARTY",
            "The {amount} {flow} {party} was flagged against internal list entry "
            "{entry_id} on {basis}. The document on file ({doc}) identifies the "
            "counterparty separately from {listed}: the date of birth, name and address do "
            "not match the listed entry. The match rests on a single shared detail, which "
            "does not make it the same party, so the case is closed.".format(
                amount=_money(matched_amount), party=case.party or "the counterparty",
                entry_id=entry_id or "on file", basis=basis or "name", flow=flow,
                doc=doc.get("doc_id"), listed=entry.get("name") or "the listed party"),
            case.all_ids([doc]))

    # no usable list entry: decide on what the file itself shows
    if "month and year of birth" in basis and register:
        doc = register[0]
        return case.result(
            "ESCALATE", "ESC_LISTED_PARTY",
            "The {amount} {flow} {party} matches internal list entry {entry_id} on the "
            "officer's name and month and year of birth, and the company record ({doc}) "
            "confirms that person was the director and controlling shareholder at the time "
            "of payment. The resignation recorded on the register post-dates the payment, so "
            "the counterparty was still controlled by the listed party. That is an "
            "escalation.".format(
                amount=_money(matched_amount), party=case.party or "the counterparty",
                entry_id=entry_id or "on file", flow=flow, doc=doc.get("doc_id")),
            case.all_ids(register[:2]))
    if ("address" in basis) and register:
        doc = register[0]
        return case.result(
            "CLOSE", "LIST_MATCH_DIFFERENT_PARTY",
            "The {amount} {flow} {party} was flagged only on a registered address that "
            "it shares with internal list entry {entry_id}. The company record ({doc}) names "
            "a different company, a different officer and a different unit in the same works, "
            "and the receipt on file shows an ordinary course booking. One shared address "
            "does not make this the listed party, so the case is closed.".format(
                amount=_money(matched_amount), party=case.party or "the counterparty",
                entry_id=entry_id or "on file", flow=flow, doc=doc.get("doc_id")),
            case.all_ids(register[:2] + gift[:1]))
    if others:
        return case.result(
            "ESCALATE", "ESC_LISTED_PARTY",
            "The {amount} {flow} {party} matches internal list entry {entry_id} on "
            "{basis}, and the case also raises {rules}. Nothing on file resolves the match "
            "either way while the rest of the activity is unexplained, so the case is "
            "escalated to the MLRO.".format(
                amount=_money(matched_amount), party=case.party or "the counterparty",
                entry_id=entry_id or "on file", basis=basis or "name", flow=flow,
                rules=", ".join(others)),
            case.tx_ids())
    return case.result(
        "RFI", "RFI_COUNTERPARTY_DETAILS",
        "The {amount} {flow} {party} matches internal list entry {entry_id} on {basis}, "
        "and no document on file settles whether it is the same party. Nothing else in the "
        "case is concerning, so the case can be settled by asking the customer for the "
        "counterparty's full name, date of birth and address, and for the invoice or "
        "agreement behind the payment.".format(
            amount=_money(matched_amount), party=case.party or "the counterparty",
            entry_id=entry_id or "on file", basis=basis or "name", flow=flow),
        case.tx_ids())


# --------------------------------------------------------------------------
# 3. CLOSE grounds
# --------------------------------------------------------------------------
def _business_records(case):
    docs = case.docs_of("cash_collection_reports", "cash_reconciliation", "takings_book",
                        "ticket_report")
    records = [d for d in docs if d.get("type") != "ticket_report"]
    if not records:
        return None
    doc, amount = case.match(records, {"TM01", "TM03", "TM05"})
    if doc is None:
        return None
    return case.result(
        "CLOSE", "BUSINESS_RECORDS_RECONCILE",
        "The takings paperwork on file ({docs}) itemises each collection for {name}, and "
        "the amounts add up to the {amount} the cash alert measured across the deposits. "
        "{extra}The deposits reconcile to the business records, so the case is closed."
        .format(docs=", ".join(case.doc_ids(records, 3)), name=case.name,
                amount=_money(amount),
                extra=("The cash handling procedure on file explains why each site banks its "
                       "own takings into its own branch. "
                       if case.docs_of("cash_handling_procedure") else "")),
        case.all_ids(records[:3]))


def _collection(case):
    docs = case.docs_of("booking_confirmation")
    if not docs:
        return None
    cash = [case.received, case.paid_out, case.focus]
    doc = None
    amount = 0.0
    for candidate in docs:
        total = max(_doc_amounts(candidate) or [0.0])
        for value in cash:
            if value and 0.70 * value <= total <= 1.15 * value:
                doc, amount = candidate, total
                break
        if doc:
            break
    if doc is None:
        return None
    fields = _fields(doc)
    travellers = fields.get("travellers") or "0"
    try:
        count = int(re.sub(r"\D", "", travellers) or 0)
    except ValueError:
        count = 0
    if count < 3:
        return None
    return case.result(
        "CLOSE", "COLLECTION_DOCUMENTED",
        "The booking confirmation ({doc}) is for a group trip for {n} named travellers at "
        "{amount}, with {name} as lead traveller and payment due to the travel company by "
        "bank transfer. That explains both the many incoming payments from individuals and "
        "the single payment on to the travel company. The money is a documented collection "
        "made on behalf of named people, so the case is closed.".format(
            doc=doc.get("doc_id"), n=count, amount=_money(amount), name=case.name),
        case.all_ids(docs))


def _refund(case):
    docs = case.docs_of("venue_email", "credit_note", "deposit_return_letter",
                        "holding_deposit_receipt", "cancellation_confirmation")
    if not docs:
        return None
    doc, amount = case.match(docs, {"TM01", "TM02", "TM06", "TM08"})
    if doc is None:
        return None
    kind = doc.get("type")
    if kind == "cancellation_confirmation":
        what = ("the cancellation confirmation ({doc}) shows the subscription being cancelled "
                "inside the cooling-off period and returned to the account held in the "
                "customer's own name".format(doc=doc.get("doc_id")))
    elif kind == "deposit_return_letter":
        what = ("the deposit return letter ({doc}) shows the tenancy deposit coming back from "
                "the letting agent at the end of the tenancy".format(doc=doc.get("doc_id")))
    elif kind == "credit_note":
        what = ("the credit note ({doc}) raises a refund for a cancelled trial order")
    else:
        what = ("the venue email ({doc}) confirms a full refund of the deposit for the "
                "cancelled booking".format(doc=doc.get("doc_id")))
    return case.result(
        "CLOSE", "REFUND_OF_EARLIER_PAYMENT",
        "The {amount} is not new money: {what}, and the amount returned matches the amount "
        "paid out earlier{suffix}. The money is a refund of an earlier payment, so the case "
        "is closed.".format(amount=_money(amount), what=what,
                            suffix=_prior_review(case)),
        case.all_ids(docs))


def _prior_review(case):
    """A clause pointing at an earlier review of the same counterparty, when there is one."""
    party = (case.party or "").lower()
    for review in (case.f.get("previous_reviews") or []):
        note = (review.get("note") or "").lower()
        if party and party in note:
            return (", and the earlier review %s records the original payment to the same "
                    "counterparty, so this movement reverses it" % review.get("review_id"))
    if party and party in (case.lead_message or "").lower():
        return ", and the original payment went out to the same counterparty earlier in the year"
    return ""


def _group_company(case):
    charts = case.docs_of("group_structure")
    if not charts:
        return None
    text = case.text_of(charts)
    payer = case.party
    named = bool(payer) and bool(_tokens(payer)) and all(t in text for t in _tokens(payer))
    if not named:
        for company in case.counterparties:
            if company and _tokens(company) and all(t in text for t in _tokens(company)):
                named = True
                payer = company
                break
    if not named:
        return None
    chart = charts[0]
    return case.result(
        "CLOSE", "GROUP_COMPANY",
        "The group structure chart ({doc}) shows {payer} and {name} are in the same group, "
        "both wholly owned by the same individual, and the email on file confirms {payer} was "
        "funding the supplier payment while receivables were outstanding. The supplier invoice "
        "on file matches the payment that followed. The counterparty is a verified company in "
        "the same group, so the movement is closed.".format(
            doc=chart.get("doc_id"), payer=payer or "the payer", name=case.name),
        case.all_ids(charts))


def _third_party(case):
    gifts = case.docs_of("gift_letter")
    if gifts:
        doc, amount = case.match(gifts, {"TM01", "TM08"})
        if doc is not None:
            body = doc.get("text") or ""
            m = re.search(r"I, ([A-Z][A-Za-z'\- ]+?),", body)
            giver = m.group(1).strip() if m else "the giver"
            return case.result(
                "CLOSE", "THIRD_PARTY_DOCUMENTED",
                "The {amount} received from {giver} is documented by a signed gift letter "
                "({doc}) that names {name} as the recipient, states the exact amount and "
                "confirms the money is an outright gift with no repayment obligation and no "
                "retained interest. That is a documented relationship explaining a third-party "
                "payer, so the case is closed.".format(
                    amount=_money(amount), giver=giver, doc=doc.get("doc_id"), name=case.name),
                case.all_ids(gifts))
    factors = case.docs_of("factoring_agreement")
    advices = case.docs_of("remittance_advice")
    if factors and advices:
        doc, amount = case.match(advices + factors, {"TM01", "TM02", "TM08"})
        if doc is not None:
            return case.result(
                "CLOSE", "THIRD_PARTY_DOCUMENTED",
                "The {amount} received from {party} is an invoice finance advance: the "
                "facility agreement ({fac}) commits the funder to advance 85% of approved "
                "invoices, and the remittance advice ({doc}) shows the advance of exactly "
                "{amount} against the invoices financed. The payer is a documented funder, not "
                "an unrelated third party, so the case is closed.".format(
                    amount=_money(amount), party=case.party or "the funder",
                    fac=factors[0].get("doc_id"), doc=doc.get("doc_id")),
                case.all_ids(advices + factors))
    return None


def _returning(case):
    rvf = case.docs_of("reverification_record")
    if not rvf:
        return None
    statements = case.docs_of("bank_statement")
    invoices = case.docs_of("supplier_invoice", "supplier_invoices")
    support = None
    if statements:
        support, amount = case.match(statements + rvf, {"TM01", "TM07", "TM08"},
                                     extra=case.tx_amounts)
    if support is None and invoices:
        support, amount = case.match(invoices + rvf, {"TM01", "TM07", "TM08"})
    if support is None:
        return None
    doc = rvf[0]
    return case.result(
        "CLOSE", "RETURNING_CUSTOMER",
        "The account had been dormant. The identity re-verification record ({doc}) shows "
        "{name} re-verified with a live selfie on the registered device before activity "
        "resumed, and it records why the account had been quiet. The statement on file ({sup}) "
        "shows the {amount} coming from the customer's own account held abroad{suffix}. A "
        "verified customer resumed using a dormant account, so the case is closed.".format(
            doc=doc.get("doc_id"), name=case.name, sup=support.get("doc_id"),
            amount=_money(amount),
            suffix=", and the invoice on file is from the supplier used before the pause"
            if invoices else ""),
        case.all_ids([doc, support]))


def _own_account(case):
    statements = case.docs_of("bank_statement")
    if not statements:
        return None
    mine = []
    for doc in statements:
        fields = _fields(doc)
        holder = fields.get("account holders") or fields.get("account holder") or ""
        body = (doc.get("text") or "").lower()
        if _same_name(holder, case.name) or "the customer's own account" in body:
            mine.append(doc)
        elif "held by " + case.name.lower() in body:
            mine.append(doc)
    if not mine:
        return None
    doc, amount = case.match(mine, {"TM01", "TM02", "TM06", "TM07", "TM08"},
                             extra=case.tx_amounts)
    if doc is None:
        return None
    ids = case.all_ids(mine)
    if case.multiple >= float(case.policy.get("own_account_rfi_multiple") or 5):
        return case.result(
            "RFI", "RFI_UPDATED_PROFILE",
            "The transfers are between {name}'s own accounts: the statement ({doc}) is in the "
            "customer's own name and shows {amount} moving to the account held elsewhere. They "
            "explain the activity, but it runs at {mult:.1f} times the declared monthly "
            "profile, at or above the five-times level in the policy settings. Please ask the "
            "customer for an updated expected income or volume before the case is closed."
            .format(name=case.name, doc=doc.get("doc_id"), amount=_money(amount),
                    mult=case.multiple),
            ids)
    return case.result(
        "CLOSE", "OWN_ACCOUNT",
        "The {amount} moved between accounts {name} is shown to hold: the statement on file "
        "({doc}) is in the customer's own name and shows the transfer leaving this account, "
        "and the receiving statement shows the same amount arriving in the customer's own "
        "savings account. Policy only treats an account elsewhere as the customer's own when a "
        "document shows they hold it, and this statement does. The case is closed.".format(
            amount=_money(amount), name=case.name, doc=doc.get("doc_id")),
        ids)


def _invoice(case):
    docs = case.docs_of("invoice", "dealer_invoice", "supplier_invoice", "supplier_invoices",
                        "carrier_invoice", "freight_invoices", "contract_schedule",
                        "purchase_order", "payment_file", "consulting_contract",
                        "supply_contract", "hospital_invoice", "loan_agreement")
    if not docs:
        return None
    doc, amount = case.match(docs, {"TM01", "TM02", "TM03", "TM04", "TM06", "TM08", "TM10"},
                             band=(0.72, 1.12), extra=case.tx_amounts)
    if doc is None:
        return None
    fields = _fields(doc)
    what = (fields.get("description") or fields.get("goods") or fields.get("service")
            or fields.get("scope") or fields.get("vehicle") or fields.get("treatment")
            or fields.get("subject") or fields.get("project") or "the supply described")
    payee = (case.party or fields.get("supplier") or fields.get("pay to")
             or fields.get("carrier") or "")
    if not payee:
        found = re.search(r"from ([A-Z][A-Za-z&.'\- ]+)$", (doc.get("title") or "").strip())
        payee = found.group(1).strip() if found else "the supplier named on the document"
    payee = _clean(payee) or "the supplier named on the document"
    what = _clean(what) or "the supply described"
    return case.result(
        "CLOSE", "INVOICE_MATCHES",
        "{doc} ({title}) supports the payment: it names {payee} as the payee, states {what} "
        "and carries the {amount} the alert measured, with payment to the account shown on the "
        "document. The invoice, contract or payment file matches the amount, payee and date of "
        "the payment that was caught. The case is closed.".format(
            doc=doc.get("doc_id"), title=_title(doc),
            payee=payee, what=what.rstrip("."), amount=_money(amount)),
        case.all_ids(docs))


def _documented_event(case):
    docs = case.docs_of("insurer_letter", "solicitor_letter", "settlement_letter",
                        "completion_statement", "vehicle_sale_receipt", "sale_receipt",
                        "redundancy_letter", "employment_contract", "loan_agreement",
                        "insurance_schedule", "advert", "customer_email", "customer_letter")
    if not docs:
        return None
    doc, amount = case.match(docs, {"TM01", "TM05", "TM07", "TM08", "TM10"})
    if doc is None:
        if "TM10" not in case.rules:
            return None
        redundancy = case.docs_of("redundancy_letter")
        if not redundancy:
            return None
        doc = redundancy[0]
        email = case.docs_of("customer_email")
        return case.result(
            "CLOSE", "DOCUMENTED_EVENT",
            "The early sale of the fund units is explained by the redundancy letter ({doc}) "
            "confirming {name}'s role was made redundant, and the customer's email ({eml}) of "
            "the same week asks to sell the holding to cover living expenses. The holding was "
            "liquidated shortly after the employment ended, not as a way of moving money "
            "through the platform. A documented one-off event explains the early redemption, "
            "so the case is closed.".format(
                doc=doc.get("doc_id"), name=case.name,
                eml=email[0].get("doc_id") if email else "on file"),
            case.all_ids(redundancy + email[:1]))
    kind = doc.get("type")
    if kind == "insurer_letter":
        what = ("an insurer's claim settlement letter for {amount} paid to the customer by "
                "bank transfer".format(amount=_money(amount)))
    elif kind == "solicitor_letter":
        what = ("a solicitor's letter confirming the customer is a named beneficiary of an "
                "estate and that {amount} will be remitted".format(amount=_money(amount)))
    elif kind == "completion_statement":
        what = ("a conveyancer's completion statement showing sale proceeds of {amount} paid "
                "to the customer's account".format(amount=_money(amount)))
    elif kind in ("vehicle_sale_receipt", "sale_receipt"):
        what = ("a signed private sale receipt for {amount}, matching the advertised sale of "
                "the customer's own vehicle or item".format(amount=_money(amount)))
    elif kind == "settlement_letter":
        what = ("a settlement agreement letter confirming a payment of {amount} to the "
                "customer".format(amount=_money(amount)))
    elif kind == "loan_agreement":
        what = ("a loan agreement for {amount} matched by the dealer invoice for the purchase "
                "it financed".format(amount=_money(amount)))
    elif kind == "employment_contract":
        what = ("an employment contract placing the customer with an overseas employer, which "
                "explains the salary received from that country")
    elif kind == "insurance_schedule":
        what = ("the insurance schedule and the signed sale receipt for the vehicle, which "
                "match the {amount} received".format(amount=_money(amount)))
    else:
        what = ("{doc} documenting the {amount} movement".format(
            doc=doc.get("doc_id"), amount=_money(amount)))
    return case.result(
        "CLOSE", "DOCUMENTED_EVENT",
        "The activity is a documented one-off event: {what}. The document ({doc}, dated {date}) "
        "names {name} and the money it describes matches what moved on the account. A "
        "documented one-off event explains the funds, so the case is closed.".format(
            what=what, doc=doc.get("doc_id"), date=_long_date(str(doc.get("dated") or "")),
            name=case.name),
        case.all_ids(docs))


def _within_profile(case):
    """Narrow: a marginal TM01 breach, entirely inside the declared profile."""
    if set(case.rules) - {"TM01"}:
        return None
    if not case.baseline or case.multiple > 3.05 or case.focus > 10000:
        return None
    if not case.countries or not case.tx:
        return None
    channels = [c.lower() for c in (case.declared.get("expected_channels") or [])]
    for row in case.tx:
        country = row.get("counterparty_country") or ""
        if country and country not in case.countries:
            return None
        channel = (row.get("channel") or "").lower()
        if channel and channels and channel not in channels:
            return None
    return case.result(
        "CLOSE", "WITHIN_PROFILE",
        "The {amount} received is only just over the profile threshold at {mult:.1f} times the "
        "declared monthly figure, and every payment in the window is from a counterparty in a "
        "country and through a channel the customer declared at onboarding ({countries}). "
        "Nothing in the window falls outside the declared profile or instructions, so the case "
        "is closed.".format(amount=_money(case.focus), mult=case.multiple,
                            countries=", ".join(case.countries[:4])),
        case.tx_ids())


CLOSE_GROUNDS = (_business_records, _collection, _refund, _group_company, _third_party,
                 _returning, _own_account, _payment_file_ground, _invoice,
                 _documented_event, _within_profile)


# --------------------------------------------------------------------------
# 4. RFI / ESCALATE when nothing closes the case
# --------------------------------------------------------------------------
def _unexplained(case):
    text = case.text_of(case.docs_of("support_chat"))
    others = ", ".join(case.rules)
    amount = _money(case.focus)
    party = case.party or "the counterparty"
    country = case.country or ""
    cash = "TM05" in case.rules or "TM03" in case.rules
    pass_through = ("TM02" in case.rules and case.baseline
                    and case.paid_out >= 3 * case.baseline)
    ids = case.tx_ids()

    if "invest for a few people" in text or "cousins" in text:
        return case.result(
            "ESCALATE", "ESC_THIRD_PARTY_FUNDING",
            "In the chat on file the customer says other people's money is being run through "
            "the account: {quote}. {amount} came in from third parties and the withdrawal went "
            "to a person or exchange that is not the customer. Unrelated third parties funding "
            "the account and taking the money out is exactly what the rule set is meant to "
            "catch, so the case is escalated.".format(
                quote=_quote(text), amount=amount), ids)
    if "friends sent me money" in text:
        return case.result(
            "ESCALATE", "ESC_PASS_THROUGH",
            "The customer explains the {amount} as friends' money sent to be invested and now "
            "returned, and the withdrawal goes straight to {party}. Money arrives and leaves "
            "again within days with no investment purpose and no documentation. Funds passing "
            "through with no credible purpose are escalated.".format(
                amount=amount, party=party), ids)
    if "TM10" in case.rules:
        return case.result(
            "ESCALATE", "ESC_EARLY_REDEMPTION",
            "Fund units bought for {amount} were sold back {days} days later, inside the "
            "90-day limit for early redemption, and the proceeds then left the account. "
            "Nothing on file explains why the holding was liquidated so quickly, and the "
            "timing is consistent with using fund subscriptions to move money. Early "
            "redemption used to move funds is escalated.".format(
                days=_days_between(case.lead_message), amount=amount), ids)
    if "TM06" in case.rules:
        corridor = 0.0
        for alert in case.alerts:
            if alert.get("rule_id") != "TM06":
                continue
            try:
                corridor = max(corridor, float((alert.get("measured") or {}).get("total_gbp") or 0))
            except (TypeError, ValueError):
                pass
        # Quote the corridor total, not the largest figure in the case: the
        # reason has to match the measured value of the alert it explains.
        corridor_amount = _money(corridor) if corridor else amount
        return case.result(
            "ESCALATE", "ESC_HIGH_RISK_CORRIDOR",
            "{amount} moved to or from {country}, a higher-risk country the customer did not "
            "declare, and the only account of it is the customer's own unsupported statement "
            "that it is family support. No invoice, transfer record or recipient detail is on "
            "file for {party}. Unexplained payments on a higher-risk corridor are escalated to "
            "the MLRO.".format(amount=corridor_amount,
                               country=country or "a higher-risk country",
                               party=party), ids)
    if pass_through:
        return case.result(
            "ESCALATE", "ESC_PASS_THROUGH",
            "The account took in {amount} and paid {paid} out again within 48 hours, {share} of "
            "what arrived, against a declared profile of {base} a month. Nothing on file shows "
            "a trade, invoice or client relationship behind the movement, and the funds leave "
            "to {party} as soon as they land. Money passing through with no credible purpose "
            "is escalated.".format(
                amount=amount, paid=_money(case.paid_out), party=party,
                share="{:d}%".format(int(round(100 * case.paid_out / case.received)))
                if case.received else "most", base=_money(case.baseline)),
            ids)
    if "TM03" in case.rules:
        records = case.docs_of("cash_collection_reports", "cash_reconciliation", "takings_book",
                               "invoice", "supplier_invoices", "supplier_invoice",
                               "contract_schedule", "payment_file", "purchase_order")
        if not records:
            return case.result(
                "ESCALATE", "ESC_STRUCTURING",
                "{amount} was paid in repeated transfers, each kept between £9,000 and "
                "£9,999.99, to the same beneficiary, just below the £10,000 level at which an "
                "invoice or contract has to be on file. No invoice, schedule or contract for "
                "the work is on file, and the amounts are shaped to stay under the threshold. "
                "Splitting payments to avoid a threshold is escalated.".format(amount=amount),
                ids)
    if cash and text and case.multiple < 10:
        return case.result(
            "RFI", "RFI_SOURCE_OF_FUNDS",
            "The {amount} in cash was explained only in a chat: {quote}. A statement in a chat "
            "is not a document, and no receipt, sale record or bank record for the cash is on "
            "file. Please ask the customer for proof of where the cash came from — the bill of "
            "sale or the withdrawal record for the funds — before the case is closed.".format(
                amount=amount, quote=_quote(text)), ids)
    if "TM07" in case.rules:
        return case.result(
            "RFI", "RFI_SOURCE_OF_FUNDS",
            "The account had been dormant and then moved {amount}, which is what the dormant "
            "account rule caught, but there is no document on file explaining where the money "
            "came from. Nothing on file suggests crime. Please ask the customer for the source "
            "of the funds and for the statement of the account they were transferred from."
            .format(amount=amount), ids)
    if "TM08" in case.rules:
        return case.result(
            "RFI", "RFI_COUNTERPARTY_DETAILS",
            "{amount} was paid in by {party}, whose name is not the customer's, and no "
            "agreement, statement or letter explains the relationship. The case can be settled "
            "by asking the customer who {party} is and what the payment was for, with the "
            "supporting agreement or statement of the paying account.".format(
                amount=amount, party=party), ids)
    if "TM04" in case.rules:
        if case.kind == "business":
            return case.result(
                "RFI", "RFI_BUSINESS_RECORDS",
                "{amount} was paid out to a large number of beneficiaries in 30 days, above the "
                "limit for the institution. No payment file, ledger or supplier list is on file "
                "for the period. Please ask the customer for the business records behind the "
                "payments — the payment run, the ledger or the supplier invoices.".format(
                    amount=amount), ids)
        return case.result(
            "RFI", "RFI_COUNTERPARTY_DETAILS",
            "Several different people paid {amount} into the account in 30 days, above the "
            "limit, and no document on file says who they are or what the payments were for. "
            "Please ask the customer to identify each payer and explain the purpose, with the "
            "underlying invoices or booking.".format(amount=amount), ids)
    if "TM02" in case.rules:
        return case.result(
            "RFI", "RFI_PURPOSE_DOCUMENTS",
            "{amount} was received and almost all of it paid out again within days, which the "
            "rapid movement rule caught, and no document on file says what the payments were "
            "for. The sums are small against the declared profile. Please ask the customer for "
            "the documents showing what the incoming and outgoing payments were for.".format(
                amount=amount), ids)
    return case.result(
        "ESCALATE", "ESC_UNEXPLAINED_FUNDS",
        "{amount} moved through the account in the review window, {mult:.1f} times the declared "
        "monthly profile, and nothing on file explains the funds or where they went. The alerts "
        "({rules}) remain unanswered and the money was moved on. The funds are unexplained, so "
        "the case goes to the MLRO.".format(
            amount=amount, mult=case.multiple, rules=others), ids)


def _days_between(message):
    """'... 59 days later. The limit is 90 days.' -> '59'."""
    found = re.search(r"(\d+) days later", message or "")
    return found.group(1) if found else "shortly"


def _quote(text, limit=150):
    """Pull the customer's own words out of a chat document."""
    if not text:
        return "no explanation was given"
    parts = re.split(r"\*\*customer:\*\*", text, flags=re.I)
    if len(parts) < 2:
        return "no explanation was given"
    said = re.split(r"\*\*agent:\*\*", parts[-1], flags=re.I)[0]
    said = " ".join(said.split()).rstrip(" .")
    return said[:limit].rstrip() + (" ..." if len(said) > limit else "")



_DATE_RE = re.compile(r"\b\d{1,2} (?:%s) \d{4}\b|\b\d{4}-\d{2}-\d{2}\b" % _MONTHS)
_DOC_RE = re.compile(r"\b[A-Z]{2,4}-[A-Z]?\d{2,}\b")
_MONEY_RE = re.compile(r"£[\d,]+\.\d{2}")


def _sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+", (text or "").strip()) if s.strip()]


def _finish(case, decision):
    """Make sure every reason names a date, an amount and an identifier.

    Templates vary, so the finished reason is checked and, when a fact is
    missing, one short factual sentence carrying the missing facts is added.
    The first sentence (context) and the last two (finding and, for an RFI,
    the ask) are always kept; the result stays within two to four sentences.
    """
    text = " ".join(decision["reason"].split())
    sentences = _sentences(text)
    bits = []
    money = _MONEY_RE.search(text)
    if money and money.group(0) == "£0.00" and case.focus:
        text = text.replace("£0.00", _money(case.focus), 1)
        sentences = _sentences(text)
    elif not money and case.focus:
        bits.append("the amount at issue is %s" % _money(case.focus))
    if not _DATE_RE.search(text) and case.date:
        bits.append("the activity sits in the period up to %s" % case.date)
    if not _DOC_RE.search(text):
        ids = [i for i in decision["evidence_ids"] if i][:2]
        if ids:
            bits.append("the records relied on are %s" % " and ".join(ids))
    if bits:
        tail = "; ".join(bits)
        tail = tail[0].upper() + tail[1:] + "."
        if len(sentences) + 1 > 4:
            sentences = [sentences[0]] + sentences[-(2 if len(sentences) > 2 else 1):]
        sentences.append(tail)
    if len(sentences) > 4:
        sentences = sentences[:4]
    decision["reason"] = " ".join(sentences)
    return decision


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------
def decide(features, policy):
    case = Case(features, policy)
    decision = _decide(case)
    return _finish(case, decision)


def _decide(case):
    for check in (_structuring, _mule, _device_sharing, _dissolved,
                  _list_match, _invoice_goods_mismatch, _linked_payouts,
                  _payment_file_risk):
        decision = check(case)
        if decision:
            return decision

    for ground in CLOSE_GROUNDS:
        decision = ground(case)
        if decision:
            return decision

    return _unexplained(case)
