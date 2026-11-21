"""Evidence access for one institution folder. Standard library only.

Owner: B.  Frozen signatures (docs/CONTRACT.md §4) are unchanged; everything else
here is additive:

  * ``skeleton``      - template fingerprint (unchanged behaviour)
  * ``template_key``  - coarser family key used to group skeletons
  * ``classify``      - text -> human readable semantic tag
  * ``Index.tag``     - per document tag (also on every doc dict)
  * ``Index.find_by_counterparty`` / ``find_by_date`` / ``find_by_country``
  * ``Index.find_explaining_documents`` - locate the documents that speak to an
    alert (amount / counterparty / date / country)

Deterministic throughout: no random, no clock, no dict-order dependence.
Unknown templates fall back to ``tag = "unknown"`` and never raise.
"""
import json
import os
import re

_AMOUNT = re.compile(r"£\s?([\d,]+\.\d{2})")
_MONTHS = ("January|February|March|April|May|June|July|August|"
           "September|October|November|December")
_LONG_DATE = re.compile(r"\b\d{1,2} (?:%s) \d{4}\b" % _MONTHS)
_ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_NUMBER = re.compile(r"\b\d+\b")
_NAME = re.compile(r"\b[A-Z][a-z]+(?: [A-Z][a-z]+)*\b")
_WS = re.compile(r"\s+")

# -- dates -------------------------------------------------------------------
_MONTH_NUM = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}
_M_YEAR = re.compile(r"\b(%s)\s+(\d{4})\b" % _MONTHS, re.IGNORECASE)
_BORN = re.compile(
    r"\bborn\s+(?:on\s+)?(\d{1,2})\s+(%s)\s+(\d{4})" % _MONTHS, re.IGNORECASE)
_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")

# -- addresses ---------------------------------------------------------------
_POSTCODE = re.compile(r"\b([A-Z]{1,2}\d{1,2}[A-Z]?)\s*(\d[A-Z]{2})\b",
                       re.IGNORECASE)
_UNIT = re.compile(r"\b(?:unit|flat|suite|apartment|apt)\s*([0-9]+[a-z]?)\b",
                   re.IGNORECASE)
_STREET_NO = re.compile(r"^\s*(\d+[a-z]?)\b", re.IGNORECASE)

# Legal forms only.  Trading / Holdings / Group are part of a company's name
# and must not be stripped, or "X Trading Ltd" would equal "X Holdings Ltd".
_SUFFIXES = {
    "ltd", "limited", "plc", "llp", "lp", "co", "company", "inc", "corp",
    "corporation", "gmbh", "ag", "bv", "nv", "sa", "sas", "sarl", "srl", "sp",
    "oo", "z", "fze", "fzco", "pjsc", "jsc", "llc", "pte", "pty",
}
_HONORIFICS = {"mr", "mrs", "ms", "miss", "dr", "sir", "madam", "mx"}
_ADDR_NOISE = {
    "unit", "flat", "suite", "apartment", "apt", "the", "of", "and", "at",
    "road", "rd", "street", "st", "avenue", "ave", "close", "cl", "lane",
    "ln", "way", "place", "pl", "terrace", "crescent", "drive", "dr", "works",
    "business", "park", "estate", "house", "floor",
}

# Tag -> the verdict and reason code the tag can support ("" = neutral).
TAG_SUPPORT = {
    "invoice_matches_payment": ("CLOSE", "INVOICE_MATCHES"),
    "purchase_order_documented": ("CLOSE", "INVOICE_MATCHES"),
    "business_contract": ("CLOSE", "DOCUMENTED_EVENT"),
    "asset_sale": ("CLOSE", "DOCUMENTED_EVENT"),
    "asset_purchase": ("CLOSE", "DOCUMENTED_EVENT"),
    "gift_from_relative": ("CLOSE", "DOCUMENTED_EVENT"),
    "inheritance": ("CLOSE", "DOCUMENTED_EVENT"),
    "insurance_settlement": ("CLOSE", "DOCUMENTED_EVENT"),
    "employment_payout": ("CLOSE", "DOCUMENTED_EVENT"),
    "holdings_sale": ("CLOSE", "DOCUMENTED_EVENT"),
    "medical_treatment_abroad": ("CLOSE", "DOCUMENTED_EVENT"),
    "event_booking": ("CLOSE", "DOCUMENTED_EVENT"),
    "purchase_receipt": ("CLOSE", "DOCUMENTED_EVENT"),
    "cash_withdrawal_returned": ("CLOSE", "DOCUMENTED_EVENT"),
    "refund": ("CLOSE", "REFUND_OF_EARLIER_PAYMENT"),
    "erroneous_transfer_refund": ("CLOSE", "REFUND_OF_EARLIER_PAYMENT"),
    "cash_business_records": ("CLOSE", "BUSINESS_RECORDS_RECONCILE"),
    "cash_collection_documented": ("CLOSE", "COLLECTION_DOCUMENTED"),
    "own_account_statement": ("CLOSE", "OWN_ACCOUNT"),
    "own_account_instruction": ("CLOSE", "OWN_ACCOUNT"),
    "company_ownership_record": ("CLOSE", "GROUP_COMPANY"),
    "dormant_return": ("CLOSE", "RETURNING_CUSTOMER"),
    "loan_documented": ("CLOSE", "THIRD_PARTY_DOCUMENTED"),
    "family_support_abroad": ("RFI", "RFI_PURPOSE_DOCUMENTS"),
    "loan_from_friend_claim": ("RFI", "RFI_SOURCE_OF_FUNDS"),
    "background_kyc": ("", ""),
    "no_explanation": ("", ""),
    "mule_recruitment_chat": ("ESCALATE", "ESC_MULE_ACTIVITY"),
    "third_party_funds_held": ("ESCALATE", "ESC_THIRD_PARTY_FUNDING"),
    "group_funds_pass_through": ("ESCALATE", "ESC_PASS_THROUGH"),
    "structuring_enquiry": ("ESCALATE", "ESC_STRUCTURING"),
    "high_risk_routing_unexplained": ("ESCALATE", "ESC_HIGH_RISK_CORRIDOR"),
    "shared_device_export": ("ESCALATE", "ESC_ACCOUNT_MISUSE"),
    "incoming_fraud_report": ("ESCALATE", "ESC_UNEXPLAINED_FUNDS"),
    "unknown": ("", ""),
}

# Document types present in the development set.  Any other type is an unseen
# template: it only gets a tag when its wording matches a rule, else unknown.
KNOWN_TYPES = frozenset([
    "advert", "bank_statement", "booking_confirmation", "cancellation_confirmation",
    "carrier_invoice", "cash_collection_reports", "cash_handling_procedure",
    "cash_reconciliation", "company_register_extract", "completion_statement",
    "consulting_contract", "contact_note", "contract_schedule", "credit_note",
    "customer_email", "customer_letter", "dealer_invoice", "deposit_return_letter",
    "device_export", "due_diligence_summary", "email", "employment_contract",
    "factoring_agreement", "freight_invoices", "gift_letter", "group_structure",
    "holding_deposit_receipt", "hospital_invoice", "insurance_schedule",
    "insurer_letter", "invoice", "loan_agreement", "management_accounts",
    "payment_file", "proof_of_address", "purchase_order", "receipt",
    "redundancy_letter", "remittance_advice", "reverification_record", "sale_receipt",
    "sending_bank_fraud_report", "settlement_letter", "significant_control_register",
    "solicitor_letter", "staff_note", "supplier_invoice", "supplier_invoices",
    "supply_contract", "support_chat", "takings_book", "ticket_report", "venue_email",
    "vehicle_sale_receipt",
])


def skeleton(text):
    """Normalise a document to a template fingerprint.

    Amounts, dates, numbers and capitalised names are replaced so that two
    documents generated from the same template share a fingerprint.
    """
    t = _AMOUNT.sub("<AMT>", text)
    t = _LONG_DATE.sub("<DATE>", t)
    t = _ISO_DATE.sub("<DATE>", t)
    t = _NUMBER.sub("<N>", t)
    t = _NAME.sub("<NAME>", t)
    return _WS.sub(" ", t).strip()


def template_key(doc_type, text, length=120):
    """Coarser family key: document type plus the opening of the fingerprint.

    ``skeleton`` still varies with the goods, the wording variant or the table
    size.  That is useful for auditing but too fine for a human mapping table;
    the opening (heading plus first field labels) collapses every instance of
    one template into one family.
    """
    return "%s|%s" % (doc_type or "", skeleton(text)[:length])


def _read_jsonl(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _amounts(text):
    return sorted({round(float(a.replace(",", "")), 2) for a in _AMOUNT.findall(text)})


def parse_dates(text):
    """Every date in a document, normalised to ISO ``YYYY-MM-DD``."""
    out = set()
    for m in _ISO.finditer(text or ""):
        out.add("%s-%s-%s" % (m.group(1), m.group(2), m.group(3)))
    for m in _LONG_DATE.finditer(text or ""):
        parts = m.group(0).split()
        month = _MONTH_NUM.get(parts[1].lower())
        if month:
            out.add("%s-%02d-%02d" % (parts[2], month, int(parts[0])))
    return sorted(out)


def name_tokens(value):
    """Lower-case identity tokens of a person or company name."""
    if not value:
        return []
    text = re.sub(r"[^A-Za-z0-9 ]+", " ", str(value)).lower()
    tokens = [t for t in text.split() if t and t not in _HONORIFICS]
    core = [t for t in tokens if t not in _SUFFIXES]
    return core or tokens


def names_match(left, right):
    """True when two names denote the same person/company (punctuation free)."""
    a, b = name_tokens(left), name_tokens(right)
    if not a or not b:
        return False
    if a == b:
        return True
    # A middle initial or one extra given name does not change identity.
    if len(a) >= 2 and len(b) >= 2 and a[0] == b[0] and a[-1] == b[-1]:
        return abs(len(a) - len(b)) <= 1
    return False


def address_parts(value):
    """Split an address into postcode / unit / street number / name tokens."""
    if not value:
        return {}
    text = str(value)
    parts = {}
    pc = _POSTCODE.search(text)
    if pc:
        parts["postcode"] = (pc.group(1) + pc.group(2)).upper()
    unit = _UNIT.search(text)
    if unit:
        parts["unit"] = unit.group(1).lower()
    number = _STREET_NO.search(text)
    if number:
        parts["number"] = number.group(1).lower()
    tokens = [t for t in re.sub(r"[^A-Za-z0-9 ]+", " ", text).lower().split()
              if t not in _ADDR_NOISE and not t.isdigit() and len(t) > 2]
    parts["tokens"] = sorted(set(tokens))
    return parts


def compare_address(left, right):
    """Compare two addresses: ``full`` / ``partial`` / ``none``.

    ``partial`` is the "registered address in <works>" list hit: same premises
    name, different unit (4A vs 4B) - which must not be read as the same party.
    """
    if not left or not right:
        return "none"
    a, b = address_parts(left), address_parts(right)
    if not a or not b:
        return "none"
    if a.get("postcode") and b.get("postcode") and a["postcode"] != b["postcode"]:
        return "none"
    shared = len(set(a.get("tokens", [])) & set(b.get("tokens", [])))
    if (a.get("postcode") and a.get("postcode") == b.get("postcode")
            and a.get("number") and a.get("number") == b.get("number")):
        return "full"
    if a.get("unit") and b.get("unit") and a["unit"] != b["unit"] and shared >= 2:
        return "partial"
    if a.get("number") and b.get("number") and a["number"] != b["number"] and shared >= 2:
        return "partial"
    if shared >= 3 and not (a.get("postcode") or b.get("postcode")):
        return "full"
    return "none"


def parse_dob(text):
    """First full date of birth in a text, as ``(year, month, day)``."""
    m = _BORN.search(text or "")
    if m:
        month = _MONTH_NUM.get(m.group(2).lower())
        if month:
            return (int(m.group(3)), month, int(m.group(1)))
    return None


def parse_month_year(text):
    """Month and year of birth from an officer table cell, ``(year, month)``."""
    m = _M_YEAR.search(text or "")
    if m:
        month = _MONTH_NUM.get(m.group(1).lower())
        if month:
            return (int(m.group(2)), month)
    return None


def dob_tuple(value):
    """ISO date string -> ``(year, month, day)``."""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", value or "")
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def _hasany(text, *phrases):
    return any(p in text for p in phrases)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

_CHAT_TYPES = ("support_chat", "contact_note", "staff_note", "customer_email",
               "customer_letter", "email", "reverification_record")

_THRESHOLD_WORDS = ("below the £10,000", "under £10,000", "below £10,000",
                    "under the £10,000", "less than £10,000",
                    "installments of under", "installments of less",
                    "split into", "aggregat", "keeping individual",
                    "keeping each individual")
_REPORTING_WORDS = ("threshold", "reporting", "exempt", "documentation",
                    "paperwork", "requirement", "invoice", "avoid", "sufficient",
                    "identification", "being prompted")
_EVASION_WORDS = ("unwilling to explain", "unable to explain", "declined to explain",
                  "unwilling to provide", "unable to provide", "declined to provide",
                  "declined to discuss", "evasive", "refused to explain",
                  "pressed for clarification", "requested further clarification",
                  "asked for clarification", "further clarification")
_ROUTING_WORDS = ("lebanon", "routing", "routed", "destination of the funds",
                  "beneficiary location", "being routed", "directed to")

_LOAN_WORDS = ("loan from a friend", "loan provided by a friend",
               "personal loan from a friend", "loan from a friend of mine",
               "funds from a loan", "loan funds from a friend",
               "loan i received from a friend", "from a friend to assist",
               "from a friend to help")
_PASS_THROUGH_WORDS = ("cover our supplier payment", "cover our upcoming supplier payment",
                       "cover a supplier payment", "supplier obligation",
                       "both companies are mine")
_CASH_BACK_WORDS = ("deposited that cash back", "deposited the cash back",
                    "paid that cash back", "paid the cash back in",
                    "dropped that cash back", "cash back into my account",
                    "cash back in today", "same cash you previously withdrew",
                    "same cash that", "same cash amount", "identical cash amount")


def classify(doc_type, text):
    """Map a document to a semantic tag.  Never raises.

    Rules are ordered: suspicion first (a chat that recruits a money mule is a
    mule chat whatever the letterhead says), then documents that explain funds,
    then background material.  A type outside ``KNOWN_TYPES`` with no matching
    wording returns ``"unknown"`` so ``decide`` always has a safe branch.
    """
    try:
        t = (text or "").lower()
        if not t.strip():
            return "unknown"
        dtype = doc_type or ""

        # -- suspicion ------------------------------------------------------
        if _hasany(t, "payments assistant", "as my wages", "keep 8%",
                   "keep a percentage", "keep a commission",
                   "clients pay into my account", "client payments into my account",
                   "send it on to the company"):
            return "mule_recruitment_chat"
        if _hasany(t, "invest for a few people", "investing through mine",
                   "cannot open an account here", "cant open an account here",
                   "invest for them", "changed their minds"):
            return "third_party_funds_held"
        if _hasany(t, *_PASS_THROUGH_WORDS):
            return "group_funds_pass_through"
        if _hasany(t, *_THRESHOLD_WORDS) and _hasany(t, *_REPORTING_WORDS):
            return "structuring_enquiry"
        if _hasany(t, *_EVASION_WORDS) and _hasany(t, *_ROUTING_WORDS):
            return "high_risk_routing_unexplained"
        if dtype == "device_export":
            return "shared_device_export"
        if dtype == "sending_bank_fraud_report":
            return "incoming_fraud_report"
        if _hasany(t, *_LOAN_WORDS):
            return "loan_from_friend_claim"

        # -- documents that explain funds -----------------------------------
        if dtype in ("invoice", "supplier_invoice", "supplier_invoices",
                     "carrier_invoice", "freight_invoices"):
            return "invoice_matches_payment"
        if dtype == "purchase_order":
            return "purchase_order_documented"
        if dtype in ("sale_receipt", "vehicle_sale_receipt", "advert",
                     "completion_statement"):
            return "asset_sale"
        if dtype == "dealer_invoice":
            return "asset_purchase"
        if dtype == "gift_letter":
            return "gift_from_relative"
        if dtype == "solicitor_letter":
            return "inheritance"
        if dtype == "insurer_letter":
            return "insurance_settlement"
        if dtype in ("redundancy_letter", "settlement_letter"):
            return "employment_payout"
        if dtype in ("credit_note", "cancellation_confirmation", "venue_email",
                     "deposit_return_letter", "holding_deposit_receipt"):
            return "refund"
        if dtype in ("takings_book", "cash_reconciliation", "management_accounts",
                     "ticket_report", "cash_handling_procedure"):
            return "cash_business_records"
        if dtype in ("cash_collection_reports", "payment_file", "remittance_advice"):
            return "cash_collection_documented"
        if dtype in ("group_structure", "significant_control_register",
                     "company_register_extract"):
            return "company_ownership_record"
        if dtype == "bank_statement":
            return "own_account_statement"
        if dtype == "reverification_record":
            return "dormant_return"
        if dtype == "customer_letter":
            return "own_account_instruction"
        if dtype == "customer_email":
            if _hasany(t, "sell my", "sell holdings", "sell the fund", "redeem",
                       "withdraw the money") and _hasany(
                           t, "redundan", "living expenses", "need the money"):
                return "holdings_sale"
            if _hasany(t, "accidentally transferred", "in error", "by mistake",
                       "mistakenly transferred", "return of", "made an error",
                       "reversal of", "returned to my", "return these funds"):
                return "erroneous_transfer_refund"
            return "no_explanation"
        if dtype == "loan_agreement":
            return "loan_documented"
        if dtype in ("consulting_contract", "contract_schedule", "supply_contract",
                     "employment_contract", "factoring_agreement"):
            return "business_contract"
        if dtype == "booking_confirmation":
            return "event_booking"
        if dtype in ("receipt", "insurance_schedule"):
            return "purchase_receipt"
        if dtype == "hospital_invoice":
            return "medical_treatment_abroad"

        # -- claims in chats that only restate the alert ---------------------
        if _hasany(t, "heart surgery", "university medical center",
                   "medical treatment"):
            return "medical_treatment_abroad"
        if _hasany(t, "sending money to help my family", "help my family there",
                   "support my family there", "money to help my family"):
            return "family_support_abroad"
        if _hasany(t, *_CASH_BACK_WORDS):
            return "cash_withdrawal_returned"
        if _hasany(t, "gift from my uncle", "gift from my aunt", "gift from my"):
            return "gift_from_relative"
        if _hasany(t, "selling my car", "selling my motorbike", "selling my van",
                   "sale of my car"):
            return "asset_sale"

        # -- background ------------------------------------------------------
        if dtype in ("due_diligence_summary", "proof_of_address", "contact_note"):
            return "background_kyc"
        if dtype in _CHAT_TYPES or dtype in KNOWN_TYPES:
            return "no_explanation"
        return "unknown"
    except Exception:  # an unseen template must never break a run
        return "unknown"


def tag_support(tag):
    """``(verdict, reason_code)`` a tag can support; empty strings when neutral."""
    return TAG_SUPPORT.get(tag, ("", ""))


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------

class Index(object):
    """Lazily reads the evidence documents of one institution folder."""

    skeleton = staticmethod(skeleton)
    template_key = staticmethod(template_key)
    classify = staticmethod(classify)
    tag_support = staticmethod(tag_support)

    def __init__(self, institution_dir):
        self.dir = institution_dir
        self._by_customer = {}
        self._text = {}
        self._records = {}
        for row in _read_jsonl(os.path.join(institution_dir, "evidence.jsonl")):
            self._by_customer.setdefault(row["customer_id"], []).append(row)
        self._internal = _read_jsonl(os.path.join(institution_dir, "internal_list.jsonl"))
        self._reviews = {}
        for row in _read_jsonl(os.path.join(institution_dir, "previous_reviews.jsonl")):
            self._reviews.setdefault(row["customer_id"], []).append(row)

    def _doc(self, row):
        doc_id = row["doc_id"]
        cached = self._records.get(doc_id)
        if cached is not None:
            return dict(cached)
        text = self._text.get(doc_id)
        if text is None:
            path = os.path.join(self.dir, row.get("file", ""))
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    text = fh.read()
            except OSError:
                text = ""
            self._text[doc_id] = text
        record = {
            "doc_id": doc_id,
            "type": row.get("type"),
            "title": row.get("title"),
            "dated": row.get("dated"),
            "text": text,
            "skeleton": skeleton(text),
            "amounts": _amounts(text),
            "tag": classify(row.get("type"), text),
            "template": template_key(row.get("type"), text),
            "dates": parse_dates(text),
            "text_lower": text.lower(),
        }
        self._records[doc_id] = record
        return dict(record)

    def docs(self, customer_id):
        return [self._doc(r) for r in self._by_customer.get(customer_id, [])]

    def docs_by_type(self, customer_id):
        out = {}
        for doc in self.docs(customer_id):
            out.setdefault(doc["type"], []).append(doc)
        return out

    def internal_list(self):
        return list(self._internal)

    def previous_reviews(self, customer_id):
        return list(self._reviews.get(customer_id, []))

    # -- lookup helpers (additive; frozen signatures untouched) -------------

    def find_by_amount(self, customer_id, gbp, tol=0.01):
        hits = []
        for doc in self.docs(customer_id):
            for value in doc["amounts"]:
                if abs(value - gbp) <= tol:
                    hits.append(doc)
                    break
        return hits

    def find_by_text(self, customer_id, needle):
        needle = (needle or "").strip().lower()
        if not needle:
            return []
        return [d for d in self.docs(customer_id) if needle in d["text_lower"]]

    def find_by_counterparty(self, customer_id, name):
        """Documents naming a counterparty (case/punctuation/suffix free)."""
        tokens = name_tokens(name)
        if not tokens:
            return []
        phrase = " ".join(tokens)
        hits = []
        for doc in self.docs(customer_id):
            words = re.sub(r"[^a-z0-9 ]+", " ", doc["text_lower"]).split()
            if all(tok in words for tok in tokens):
                hits.append(doc)
            elif phrase and phrase in _WS.sub(" ", " ".join(words)):
                hits.append(doc)
        return hits

    def find_by_date(self, customer_id, value):
        """Documents containing a date (ISO in the doc or '8 August 2026')."""
        wanted = (value or "")[:10]
        if not wanted:
            return []
        return [d for d in self.docs(customer_id) if wanted in d["dates"]]

    def find_by_country(self, customer_id, country):
        country = (country or "").strip().lower()
        if not country:
            return []
        return [d for d in self.docs(customer_id) if country in d["text_lower"]]

    def find_explaining_documents(self, customer_id, amount=None, counterparty=None,
                                  date=None, country=None, tol=0.01):
        """Documents that speak to one alert, with the fields each one matches.

        Returns ``{"docs": [...], "by_field": {...}, "best": [...]}``; each doc
        carries a ``hits`` list (``amount``/``counterparty``/``date``/``country``)
        and ``best`` is ordered by number of hits then doc_id, so the strongest
        support comes first.
        """
        checks = (
            ("amount", amount, lambda: self.find_by_amount(customer_id, amount, tol)),
            ("counterparty", counterparty,
             lambda: self.find_by_counterparty(customer_id, counterparty)),
            ("date", date, lambda: self.find_by_date(customer_id, date)),
            ("country", country, lambda: self.find_by_country(customer_id, country)),
        )
        scored = {}
        for field, value, finder in checks:
            if value in (None, "", 0, 0.0):
                continue
            for doc in finder():
                scored.setdefault(doc["doc_id"], {"doc": doc, "hits": []})
                scored[doc["doc_id"]]["hits"].append(field)
        docs = []
        for doc_id in sorted(scored):
            doc = dict(scored[doc_id]["doc"])
            doc["hits"] = sorted(scored[doc_id]["hits"])
            docs.append(doc)
        by_field = {}
        for doc in docs:
            for field in doc["hits"]:
                by_field.setdefault(field, []).append(doc)
        best = sorted(docs, key=lambda d: (-len(d["hits"]), d["doc_id"]))
        return {"docs": docs, "by_field": by_field, "best": best}
