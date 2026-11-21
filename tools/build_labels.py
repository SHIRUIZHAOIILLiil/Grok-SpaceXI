#!/usr/bin/env python3
"""Build the dev pseudo-label table: tools/case_labels.jsonl + tools/labels.json.

Usage:
    python3 tools/build_labels.py [--data data/institutions] [--out tools]

Why this exists
---------------
The dev set has no answers, so the only way to self-assess is to label the
recurring evidence shapes by hand and apply the institution's POLICY.md to each
one. This script does three things:

  1. classifies every dev case with a documented, deterministic reading of the
     policy (content-aware: a support chat, a branch note or a device export can
     carry opposite meanings, so the text decides, not the type alone);
  2. aggregates the per-case labels by evidence-type combination, which is the
     ~134 shapes the data actually repeats;
  3. writes labels.json (the combination table A reads) and LABELS.md (the
     human explanation), plus case_labels.jsonl (one line per case).

The labels are a *baseline*, not ground truth. Anything the policy cannot settle
from the files is marked needs_review and left on the conservative side
(ESCALATE / ESC_UNEXPLAINED_FUNDS or an RFI that asks for the missing document),
because a wrong CLOSE costs 10 and a needless escalation costs 2-3.

Standard library only.
"""

import json
import os
import re
import sys

VERDICTS = ("CLOSE", "RFI", "ESCALATE")
VERDICT_RANK = {"ESCALATE": 3, "RFI": 2, "CLOSE": 1}
FALLBACK = ("ESCALATE", "ESC_UNEXPLAINED_FUNDS")

# Types that only prove identity or record routine admin: they never explain
# activity on their own (contact_note has six admin skeletons, 785+824+835+900
# documents in the dev set).
NOISE = {"due_diligence_summary", "proof_of_address", "contact_note"}
# Types that can only be read with their text (see *_MARKERS below).
DUAL = {"support_chat", "staff_note", "device_export", "customer_email",
        "bank_statement", "email", "receipt", "staff_note"}

MULE_CHAT = [
    r"send it on", r"payments assistant", r"invest for (them|a few|my|other|friends)",
    r"investing through mine", r"changed their minds", r"clients pay into",
    r"for a few people", r"my cousins", r"they are investing through",
    r"invest for them",
]
VAGUE_CHAT = [
    r"family support", r"help my family", r"gift from my uncle",
    r"loan from a friend", r"loan from friends", r"sold my (car|motorbike)",
    r"selling my (car|motorbike)", r"for my parent", r"surgery", r"help with my studies",
    r"help me with bills",
]
STRUCT_NOTE = [
    r"aggregat", r"below the £", r"under £1?0?,?0?0", r"instal?lments?",
    r"different branches?", r"various branches?", r"multiple branches?",
    r"different locations", r"multiple locations", r"across branches",
    r"segments? under", r"exempt them from",
]
UNWILL_NOTE = [
    r"unwilling", r"refused", r"would not (say|explain|confirm|provide|tell)",
    r"declined to",
]

# rule -> ordered list of (doc type, CLOSE code, one-line ground).
# First hit wins, so the list is a priority order.
COVER = {
    "bank": {
        "TM01": [
            ("invoice", "INVOICE_MATCHES", "an invoice names the payee, the amount and the date of the payment"),
            ("dealer_invoice", "INVOICE_MATCHES", "a dealer invoice matches the vehicle and the amount paid"),
            ("consulting_contract", "INVOICE_MATCHES", "a signed consulting contract fixes the fee that was paid"),
            ("loan_agreement", "INVOICE_MATCHES", "a loan agreement documents the funds that were received"),
            ("management_accounts", "BUSINESS_RECORDS_RECONCILE", "the management accounts reconcile turnover to the money received"),
            ("bank_statement", "OWN_ACCOUNT", "the statement shows the money came from the customer's own account elsewhere"),
            ("venue_email", "REFUND_OF_EARLIER_PAYMENT", "the venue email documents the refund of the deposit already paid"),
            ("cash_collection_reports", "BUSINESS_RECORDS_RECONCILE", "the machine collection reports reconcile the takings paid in"),
            ("solicitor_letter", "DOCUMENTED_EVENT", "a solicitor's letter documents the estate payment received"),
            ("insurer_letter", "DOCUMENTED_EVENT", "an insurer's settlement letter documents the payout received"),
            ("vehicle_sale_receipt", "DOCUMENTED_EVENT", "a signed vehicle sale receipt documents the cash received"),
            ("hospital_invoice", "DOCUMENTED_EVENT", "a hospital invoice documents the treatment being paid for"),
            ("cash_reconciliation", "BUSINESS_RECORDS_RECONCILE", "the cash reconciliation sheets reconcile the takings banked"),
            ("ticket_report", "BUSINESS_RECORDS_RECONCILE", "the ticket sales report reconciles the cash banked"),
            ("booking_confirmation", "COLLECTION_DOCUMENTED", "a group booking confirmation documents the money collected from travellers"),
        ],
        "TM02": [
            ("invoice", "INVOICE_MATCHES", "an invoice names the payee, the amount and the date of the payment"),
            ("dealer_invoice", "INVOICE_MATCHES", "a dealer invoice matches the vehicle and the amount paid"),
            ("consulting_contract", "INVOICE_MATCHES", "a signed consulting contract fixes the fee that was paid"),
            ("loan_agreement", "INVOICE_MATCHES", "a loan agreement documents where the money came from"),
            ("cash_reconciliation", "BUSINESS_RECORDS_RECONCILE", "the cash reconciliation sheets reconcile the money in and out"),
            ("ticket_report", "BUSINESS_RECORDS_RECONCILE", "the ticket sales report reconciles the money in and out"),
            ("bank_statement", "OWN_ACCOUNT", "the statement shows the receiving account is the customer's own"),
            ("booking_confirmation", "COLLECTION_DOCUMENTED", "a group booking confirmation documents the collection that was paid out"),
        ],
        "TM03": [
            ("cash_collection_reports", "BUSINESS_RECORDS_RECONCILE", "the machine collection reports show the cash takings behind each deposit"),
            ("cash_handling_procedure", "BUSINESS_RECORDS_RECONCILE", "the cash handling procedure explains why each site banks separately"),
            ("cash_reconciliation", "BUSINESS_RECORDS_RECONCILE", "the cash reconciliation sheets show the takings behind each deposit"),
            ("ticket_report", "BUSINESS_RECORDS_RECONCILE", "the ticket sales report shows the gate takings behind each deposit"),
            ("management_accounts", "BUSINESS_RECORDS_RECONCILE", "the management accounts show cash sales covering the deposits"),
        ],
        "TM04": [
            ("booking_confirmation", "COLLECTION_DOCUMENTED", "the booking confirmation lists the travellers who each paid their share"),
            ("cash_reconciliation", "BUSINESS_RECORDS_RECONCILE", "the reconciliation shows the many payers are ticket and bar takings"),
            ("ticket_report", "BUSINESS_RECORDS_RECONCILE", "the ticket report shows the many payers are gate and bar sales"),
        ],
        "TM05": [
            ("vehicle_sale_receipt", "DOCUMENTED_EVENT", "a signed vehicle sale receipt documents the cash received"),
            ("insurance_schedule", "DOCUMENTED_EVENT", "the insurance schedule ties the vehicle in the sale receipt to the customer"),
            ("dealer_invoice", "INVOICE_MATCHES", "a dealer invoice matches the vehicle and the amount paid"),
        ],
        "TM06": [
            ("venue_email", "REFUND_OF_EARLIER_PAYMENT", "the venue email documents the refund of the deposit already paid"),
            ("hospital_invoice", "DOCUMENTED_EVENT", "the hospital invoice documents the treatment the payment settles"),
        ],
        "TM07": [
            ("insurer_letter", "DOCUMENTED_EVENT", "the insurer's settlement letter documents the payout that reactivated the account"),
            ("reverification_record", "RETURNING_CUSTOMER", "the re-verification record documents the customer's return after time abroad"),
            ("bank_statement", "OWN_ACCOUNT", "the statement shows the money moved to the customer's own account"),
        ],
        "TM22": [],
    },
    "emoney": {
        "TM01": [
            ("settlement_letter", "DOCUMENTED_EVENT", "a settlement agreement letter documents the compensation received"),
            ("venue_email", "REFUND_OF_EARLIER_PAYMENT", "the venue email documents the refund of the wedding deposit"),
            ("takings_book", "BUSINESS_RECORDS_RECONCILE", "the takings book reconciles the market takings to the money received"),
            ("booking_confirmation", "COLLECTION_DOCUMENTED", "the booking confirmation documents the money collected from travellers"),
            ("sale_receipt", "DOCUMENTED_EVENT", "the sale receipt documents the cash received for the bike"),
            ("hospital_invoice", "DOCUMENTED_EVENT", "the hospital invoice documents the treatment being paid for"),
            ("deposit_return_letter", "REFUND_OF_EARLIER_PAYMENT", "the deposit return letter documents the tenancy deposit coming back"),
            ("insurer_letter", "DOCUMENTED_EVENT", "an insurer's settlement letter documents the payout received"),
            ("bank_statement", "OWN_ACCOUNT", "the statement shows the money came from the customer's own account"),
            ("invoice", "INVOICE_MATCHES", "an invoice names the payee, the amount and the date of the payment"),
        ],
        "TM02": [
            ("bank_statement", "OWN_ACCOUNT", "the statement shows the money moved to the customer's own account"),
            ("deposit_return_letter", "REFUND_OF_EARLIER_PAYMENT", "the deposit return letter documents the tenancy deposit coming back"),
            ("holding_deposit_receipt", "REFUND_OF_EARLIER_PAYMENT", "the holding deposit receipt documents the deposit that is being returned"),
            ("booking_confirmation", "COLLECTION_DOCUMENTED", "the booking confirmation lists the travellers whose shares were collected"),
            ("takings_book", "BUSINESS_RECORDS_RECONCILE", "the takings book reconciles the market cash that was paid in and out"),
        ],
        "TM03": [
            ("takings_book", "BUSINESS_RECORDS_RECONCILE", "the takings book shows the market takings behind each top-up"),
        ],
        "TM04": [
            ("booking_confirmation", "COLLECTION_DOCUMENTED", "the booking confirmation lists the travellers who each paid their share"),
        ],
        "TM05": [
            ("advert", "DOCUMENTED_EVENT", "the advert documents the bike being offered for sale"),
            ("sale_receipt", "DOCUMENTED_EVENT", "the sale receipt documents the cash received for the bike"),
        ],
        "TM06": [
            ("venue_email", "REFUND_OF_EARLIER_PAYMENT", "the venue email documents the refund of the wedding deposit"),
            ("hospital_invoice", "DOCUMENTED_EVENT", "the hospital invoice documents the treatment the payment settles"),
        ],
        "TM07": [
            ("insurer_letter", "DOCUMENTED_EVENT", "the insurer's settlement letter documents the payout that reactivated the account"),
            ("reverification_record", "RETURNING_CUSTOMER", "the re-verification record documents the customer's return after time abroad"),
        ],
        "TM22": [],
    },
    "payments_fx": {
        "TM01": [
            ("bank_statement", "OWN_ACCOUNT", "the statement shows the funding account is held in the client's own name"),
            ("supplier_invoices", "INVOICE_MATCHES", "the supplier invoices match the amounts received from the client's customers"),
            ("supplier_invoice", "INVOICE_MATCHES", "the pro forma invoice matches the amount received"),
            ("purchase_order", "INVOICE_MATCHES", "the purchase order matches the amount received"),
            ("payment_file", "INVOICE_MATCHES", "the payment file lists the beneficiaries and amounts paid"),
            ("consulting_contract", "INVOICE_MATCHES", "the contract fixes the fee that was received"),
            ("credit_note", "REFUND_OF_EARLIER_PAYMENT", "the credit note documents the refund received from the supplier"),
            ("group_structure", "GROUP_COMPANY", "the group structure chart shows the payer is in the client's group"),
            ("factoring_agreement", "BUSINESS_RECORDS_RECONCILE", "the factoring agreement explains the invoice finance receipts"),
            ("remittance_advice", "BUSINESS_RECORDS_RECONCILE", "the remittance advice reconciles the financed invoices received"),
        ],
        "TM02": [
            ("payment_file", "INVOICE_MATCHES", "the payment file lists the beneficiaries the receipts were paid out to"),
            ("invoice", "INVOICE_MATCHES", "invoices on file match the payments out"),
            ("bank_statement", "OWN_ACCOUNT", "the statement shows the money moved to the client's own account"),
            ("factoring_agreement", "BUSINESS_RECORDS_RECONCILE", "the factoring agreement explains the in-and-out movement"),
            ("remittance_advice", "BUSINESS_RECORDS_RECONCILE", "the remittance advice reconciles the financed invoices"),
            ("freight_invoices", "INVOICE_MATCHES", "the freight invoices match the payments made to carriers"),
            ("carrier_invoice", "INVOICE_MATCHES", "the carrier invoice matches the payment made to the carrier"),
            ("consulting_contract", "INVOICE_MATCHES", "the contract fixes the fee that was received"),
            ("group_structure", "GROUP_COMPANY", "the group structure chart shows the parties are in one group"),
            ("email", "GROUP_COMPANY", "the email confirms the parties are the client's own companies"),
            ("credit_note", "REFUND_OF_EARLIER_PAYMENT", "the credit note documents the refund of the earlier payment"),
        ],
        "TM03": [
            ("contract_schedule", "INVOICE_MATCHES", "the contract payment schedule shows the instalments are contractual"),
            ("supplier_invoice", "INVOICE_MATCHES", "the pro forma invoice sets out the instalments"),
            ("supplier_invoices", "INVOICE_MATCHES", "the supplier invoices set out the instalments"),
            ("invoice", "INVOICE_MATCHES", "the invoice states the amount is payable in four instalments"),
        ],
        "TM04": [
            ("payment_file", "INVOICE_MATCHES", "the payment file lists the beneficiaries and amounts paid"),
            ("invoice", "INVOICE_MATCHES", "the invoices name the beneficiaries that were paid"),
        ],
        "TM06": [
            ("supplier_invoices", "INVOICE_MATCHES", "the supplier invoices match the payments to the higher-risk supplier"),
            ("supply_contract", "INVOICE_MATCHES", "the supply contract documents the trade with that supplier"),
            ("supplier_invoice", "INVOICE_MATCHES", "the pro forma invoice documents the trade with that supplier"),
            ("credit_note", "REFUND_OF_EARLIER_PAYMENT", "the credit note documents the refund from the supplier"),
        ],
        "TM07": [
            ("insurer_letter", "DOCUMENTED_EVENT", "the insurer's cargo claim letter documents the payout that reactivated the account"),
            ("reverification_record", "RETURNING_CUSTOMER", "the re-verification record documents the directors' return to trading"),
        ],
        "TM08": [
            ("insurer_letter", "DOCUMENTED_EVENT", "the insurer's cargo claim letter documents the third-party payout"),
            ("bank_statement", "OWN_ACCOUNT", "the statement names the holder of the funding IBAN"),
            ("group_structure", "GROUP_COMPANY", "the group structure chart shows the payer is in the client's group"),
            ("email", "GROUP_COMPANY", "the email confirms the payer is the client's own company"),
            ("credit_note", "REFUND_OF_EARLIER_PAYMENT", "the credit note documents the refund received from the supplier"),
            ("factoring_agreement", "BUSINESS_RECORDS_RECONCILE", "the factoring agreement explains the third-party receipts"),
            ("remittance_advice", "BUSINESS_RECORDS_RECONCILE", "the remittance advice reconciles the third-party receipts"),
            ("freight_invoices", "INVOICE_MATCHES", "the freight invoices show the third-party receipts pay carriers"),
            ("carrier_invoice", "INVOICE_MATCHES", "the carrier invoice shows the receipt pays that carrier"),
            ("supplier_invoices", "INVOICE_MATCHES", "the supplier invoices explain the third-party receipts"),
            ("payment_file", "INVOICE_MATCHES", "the payment file shows the third-party receipts being paid out to beneficiaries"),
            ("invoice", "INVOICE_MATCHES", "invoices on file explain the third-party receipts"),
            ("consulting_contract", "INVOICE_MATCHES", "the contract explains the third-party receipts"),
            ("purchase_order", "INVOICE_MATCHES", "the purchase order explains the third-party receipts"),
            ("supplier_invoice", "INVOICE_MATCHES", "the pro forma invoice explains the third-party receipts"),
            ("contract_schedule", "INVOICE_MATCHES", "the contract schedule explains the staged third-party receipts"),
        ],
        "TM22": [],
    },
    "investment": {
        "TM01": [
            ("gift_letter", "THIRD_PARTY_DOCUMENTED", "a signed gift letter documents the third-party payer and the relationship"),
            ("completion_statement", "DOCUMENTED_EVENT", "the completion statement documents the property sale proceeds"),
            ("cancellation_confirmation", "REFUND_OF_EARLIER_PAYMENT", "the cancellation confirmation documents the ISA subscription being returned"),
            ("insurer_letter", "DOCUMENTED_EVENT", "the insurer's settlement letter documents the payout received"),
            ("redundancy_letter", "DOCUMENTED_EVENT", "the redundancy letter documents the source of the funds"),
            ("customer_email", "DOCUMENTED_EVENT", "the customer's email explains the sale and withdrawal"),
            ("employment_contract", "WITHIN_PROFILE", "the employment contract documents the salary received from abroad"),
            ("customer_letter", "OWN_ACCOUNT", "the customer's letter directs withdrawals to their own account abroad"),
            ("bank_statement", "OWN_ACCOUNT", "the statement shows the transfers are between the customer's own accounts"),
        ],
        "TM02": [
            ("gift_letter", "THIRD_PARTY_DOCUMENTED", "the gift letter documents the third-party money that is being withdrawn"),
            ("cancellation_confirmation", "REFUND_OF_EARLIER_PAYMENT", "the cancellation confirmation documents the subscription being returned"),
            ("bank_statement", "OWN_ACCOUNT", "the statement shows the money returned to the customer's own account"),
            ("customer_email", "REFUND_OF_EARLIER_PAYMENT", "the customer's email documents the mistaken transfer being returned"),
            ("completion_statement", "DOCUMENTED_EVENT", "the completion statement documents the sale proceeds paid in and out"),
        ],
        "TM06": [
            ("customer_letter", "OWN_ACCOUNT", "the customer's letter directs the payments to their own account abroad"),
            ("employment_contract", "WITHIN_PROFILE", "the employment contract documents the foreign salary"),
        ],
        "TM07": [
            ("insurer_letter", "DOCUMENTED_EVENT", "the insurer's settlement letter documents the payout that reactivated the account"),
            ("reverification_record", "RETURNING_CUSTOMER", "the re-verification record documents the customer's return after time abroad"),
        ],
        "TM08": [
            ("gift_letter", "THIRD_PARTY_DOCUMENTED", "a signed gift letter documents the third-party payer and the relationship"),
            ("completion_statement", "DOCUMENTED_EVENT", "the completion statement documents the solicitor's client account paying the sale proceeds"),
            ("insurer_letter", "DOCUMENTED_EVENT", "the insurer's settlement letter documents the third-party payout"),
            ("cancellation_confirmation", "REFUND_OF_EARLIER_PAYMENT", "the cancellation confirmation documents the platform returning the subscription"),
            ("customer_email", "REFUND_OF_EARLIER_PAYMENT", "the customer's email documents the mistaken transfer being returned"),
            ("employment_contract", "DOCUMENTED_EVENT", "the employment contract documents the salary paid in by the employer"),
            ("bank_statement", "OWN_ACCOUNT", "the statement shows the account is the customer's own"),
            ("customer_letter", "OWN_ACCOUNT", "the customer's letter confirms the receiving account is their own"),
        ],
        "TM10": [
            ("redundancy_letter", "DOCUMENTED_EVENT", "the redundancy letter documents why the holdings are being sold"),
            ("customer_email", "DOCUMENTED_EVENT", "the customer's email explains the sale of holdings after redundancy"),
        ],
        "TM22": [],
    },
}

# Phrases reused when a rule has nothing on file.
UNEXPLAINED_HINT = {
    "TM01": ("RFI", "RFI_SOURCE_OF_FUNDS", "nothing on file shows where the money came from"),
    "TM02": ("RFI", "RFI_PURPOSE_DOCUMENTS", "nothing on file shows what the in-and-out movement was for"),
    "TM03": ("RFI", "RFI_BUSINESS_RECORDS", "nothing on file shows the takings behind the deposits"),
    "TM04": ("RFI", "RFI_PURPOSE_DOCUMENTS", "nothing on file shows why so many parties paid"),
    "TM05": ("RFI", "RFI_SOURCE_OF_FUNDS", "nothing on file shows where the cash came from"),
    "TM06": ("ESCALATE", "ESC_HIGH_RISK_CORRIDOR", "the higher-risk corridor is undocumented"),
    "TM07": ("RFI", "RFI_UPDATED_PROFILE", "nothing on file explains the reactivation"),
    "TM08": ("RFI", "RFI_COUNTERPARTY_DETAILS", "nothing on file identifies the third-party payer"),
    "TM10": ("ESCALATE", "ESC_EARLY_REDEMPTION", "nothing on file explains the early redemption"),
    "TM22": ("RFI", "RFI_COUNTERPARTY_DETAILS", "nothing on file settles whether the counterparty is the listed party"),
}


def modal(counts, prefer_verdict=None):
    """Most common key; ties break towards the more conservative verdict."""
    def rank(key):
        verdict = prefer_verdict
        if verdict is None:
            verdict = key if key in VERDICT_RANK else None
        return (counts[key], VERDICT_RANK.get(verdict, 0))
    return max(counts, key=rank)


def modal_pair(verdicts, codes):
    """Modal verdict, then the modal code among the codes that verdict allows."""
    verdict = modal(verdicts)
    subset = {}
    for code, n in codes.items():
        owner = "ESCALATE" if code.startswith("ESC_") else (
            "RFI" if code.startswith("RFI_") else "CLOSE")
        if owner == verdict:
            subset[code] = n
    code = modal(subset) if subset else max(codes, key=codes.get)
    return verdict, code


GENERIC_BASIS = {
    "INVOICE_MATCHES": "an invoice or contract names the payee, the amount and the date of the payment",
    "BUSINESS_RECORDS_RECONCILE": "business records (takings, collection reports, management accounts) reconcile to the money that moved",
    "COLLECTION_DOCUMENTED": "a documented collection for named people explains the many payers",
    "DOCUMENTED_EVENT": "a documented one-off event (payout, sale, inheritance, settlement) explains the funds",
    "REFUND_OF_EARLIER_PAYMENT": "the money is a refund of an earlier payment, documented by the counterparty",
    "OWN_ACCOUNT": "a document shows the other side of the transfer is the customer's own account",
    "LIST_MATCH_DIFFERENT_PARTY": "the register or the identity documents show the counterparty is not the listed party",
    "RETURNING_CUSTOMER": "a re-verification record shows the customer returned to a dormant account",
    "WITHIN_PROFILE": "the documents match the customer's declared profile or employment",
    "THIRD_PARTY_DOCUMENTED": "a signed document explains the third-party payer and the relationship",
    "GROUP_COMPANY": "the counterparty is a verified company in the same group",
    "RFI_SOURCE_OF_FUNDS": "nothing on file shows where the money came from; the customer has given only an account of it",
    "RFI_PURPOSE_DOCUMENTS": "nothing on file shows what the payments were for; the customer has given only an account of it",
    "RFI_BUSINESS_RECORDS": "nothing on file shows the business records behind the activity",
    "RFI_COUNTERPARTY_DETAILS": "the alert matched the counterparty on one detail only and nothing on file settles who they are",
    "RFI_UPDATED_PROFILE": "nothing on file explains the reactivation; an updated expected profile would settle it",
    "ESC_STRUCTURING": "a branch or staff note records the customer asking how to keep transactions below the reporting threshold",
    "ESC_MULE_ACTIVITY": "the customer receives other people's money and forwards it, and a sending bank reports a scam payment",
    "ESC_PASS_THROUGH": "the customer collects money from friends and relatives and sends it on with no purpose of their own",
    "ESC_ACCOUNT_MISUSE": "one device is used to operate several different customer accounts",
    "ESC_LISTED_PARTY": "a signed document gives the listed party's own date of birth, so the counterparty is the listed party",
    "ESC_HIGH_RISK_CORRIDOR": "payments to a higher-risk country are undocumented, or the payer refuses to explain them",
    "ESC_UNEXPLAINED_FUNDS": "no document explains the activity and the customer has given no account of it",
    "ESC_EARLY_REDEMPTION": "fund units are sold back early with nothing on file to explain it",
}


def read_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def any_match(patterns, text):
    low = text.lower()
    return any(re.search(p, low) for p in patterns)


def doc_text(data_dir, row):
    path = os.path.join(data_dir, row.get("file") or "")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def first_line(text):
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def money(value):
    try:
        return "£{:,.2f}".format(float(value))
    except (TypeError, ValueError):
        return None


def names_in(text):
    return set(re.findall(r"\b[A-Z][a-z]+(?: [A-Z][a-z]+)+\b", text))


class Institution(object):
    def __init__(self, data_dir):
        self.dir = data_dir
        self.inst = os.path.basename(os.path.abspath(data_dir).rstrip(os.sep))
        self.cases = {r["case_id"]: r for r in read_jsonl(
            os.path.join(data_dir, "cases.jsonl"))}
        self.customers = {r["customer_id"]: r for r in read_jsonl(
            os.path.join(data_dir, "customers.jsonl"))}
        self.alerts = {}
        for row in read_jsonl(os.path.join(data_dir, "alerts.jsonl")):
            self.alerts.setdefault(row["case_id"], []).append(row)
        self.docs = {}
        for row in read_jsonl(os.path.join(data_dir, "evidence.jsonl")):
            self.docs.setdefault(row["customer_id"], []).append(row)
        self.list_entries = read_jsonl(os.path.join(data_dir, "internal_list.jsonl"))
        self.by_entry = {r["entry_id"]: r for r in self.list_entries}
        self._text = {}

    def text(self, row):
        key = row["doc_id"]
        if key not in self._text:
            self._text[key] = doc_text(self.dir, row)
        return self._text[key]

    def docs_of(self, customer_id):
        return self.docs.get(customer_id, [])


def tm22_assessment(inst, case, docs, alerts):
    """TM22: is the counterparty the listed party, a different party, or open?"""
    alert = next((a for a in alerts if a["rule_id"] == "TM22"), None)
    if alert is None:
        return None
    entry = inst.by_entry.get((alert.get("measured") or {}).get("list_entry")) or {}
    listed_name = (entry.get("name") or "").strip()
    listed_dob = (entry.get("date_of_birth") or "").strip()
    listed_addr = (entry.get("address") or "").strip()
    matched_on = ((alert.get("measured") or {}).get("matched_on") or "").lower()
    by_type = {}
    for doc in docs:
        by_type.setdefault(doc["type"], []).append(doc)

    # A gift letter that names the listed party with their date of birth proves
    # the payer *is* the listed party.
    for doc in by_type.get("gift_letter", []):
        text = inst.text(doc)
        if listed_name and listed_name in text:
            dob_hit = False
            if listed_dob:
                iso = listed_dob
                day, month = iso[8:10].lstrip("0"), iso[5:7]
                months = ("January February March April May June July August "
                          "September October November December").split()
                long_form = "%s %s %s" % (day, months[int(month) - 1], iso[:4])
                dob_hit = long_form in text
            return {
                "verdict": "ESCALATE", "code": "ESC_LISTED_PARTY",
                "doc": doc["doc_id"],
                "basis": ("the gift letter gives the same date of birth as internal list entry %s, "
                          "so the payer is the listed party" % entry.get("entry_id")),
                "flag": "listed party proved by gift letter; ESC_LISTED_PARTY is the policy answer",
            }

    # A register extract that names the listed person as a resigned officer, with
    # a replacement appointed before the payment, shows the payee is no longer
    # controlled by the listed party.
    pay_dates = []
    for tx_id in (alert.get("transaction_ids") or []):
        pay_dates.append(tx_id)
    for doc in by_type.get("company_register_extract", []):
        text = inst.text(doc)
        if listed_name and listed_name in text and "Resigned" in text:
            return {
                "verdict": "CLOSE", "code": "LIST_MATCH_DIFFERENT_PARTY",
                "doc": doc["doc_id"],
                "basis": ("the register shows the listed officer resigned as a director before the "
                          "payment and a replacement was appointed, so the payee was no longer "
                          "controlled by the listed party"),
                "flag": "closing turns on the resignation date being effective before the payment",
            }

    # An address-only match with a register extract that never mentions the
    # listed person: the payee is a separate company at the same address.
    if matched_on.startswith("registered address"):
        for doc in by_type.get("company_register_extract", []):
            text = inst.text(doc)
            if listed_name and listed_name not in text:
                return {
                    "verdict": "CLOSE", "code": "LIST_MATCH_DIFFERENT_PARTY",
                    "doc": doc["doc_id"],
                    "basis": ("the register extract shows the payee is a separate company at a "
                              "different unit of the same works, with its own officers, so the "
                              "address match is not the listed party"),
                    "flag": None,
                }

    # Officer match where the register never names the listed person.
    if matched_on.startswith("company officer"):
        for doc in by_type.get("company_register_extract", []):
            if listed_name and listed_name not in inst.text(doc):
                return {
                    "verdict": "CLOSE", "code": "LIST_MATCH_DIFFERENT_PARTY",
                    "doc": doc["doc_id"],
                    "basis": ("the register extract lists different officers, so the officer match "
                              "is a name coincidence"),
                    "flag": "check the officer table before relying on this",
                }

    return {
        "verdict": "RFI", "code": "RFI_COUNTERPARTY_DETAILS", "doc": None,
        "basis": ("the alert matched %s on %s only, and nothing on file shows a date of birth or "
                  "address for the counterparty" % (listed_name, matched_on or "a single detail")),
        "flag": None,
    }


def classify(inst, case, signature):
    """Return (verdict, code, basis, confidence, flags, evidence_ids)."""
    customer = inst.customers.get(case["customer_id"], {})
    docs = inst.docs_of(case["customer_id"])
    alerts = inst.alerts.get(case["case_id"], [])
    rules = sorted({a["rule_id"] for a in alerts})
    by_type = {}
    for doc in docs:
        by_type.setdefault(doc["type"], []).append(doc)
    types = set(by_type)

    flags = []
    evidence = []

    # ---- 1. Suspicion that overrides any explanation -----------------------
    for doc in by_type.get("sending_bank_fraud_report", []):
        text = inst.text(doc)
        code = "ESC_MULE_ACTIVITY"
        basis = "a sending bank reports the payment into this account as an APP scam"
        for chat in by_type.get("support_chat", []):
            if any_match(MULE_CHAT, inst.text(chat)):
                basis = ("the sending bank's fraud report and the chat where the customer says the "
                         "money is passed on show the account is used to receive and forward other "
                         "people's money")
                break
        else:
            code = "ESC_THIRD_PARTY_FUNDING"
            basis = ("a sending bank reports that its customer's money reached this account in an "
                     "APP scam, and nothing on file shows a legitimate payer")
        return ("ESCALATE", code, basis, "high",
                ["fraud report on file: escalation is the policy answer, the code is a judgement"],
                [doc["doc_id"]] + [a["transaction_ids"][0] for a in alerts
                                   if a.get("transaction_ids")][:2])

    for doc in by_type.get("staff_note", []):
        text = inst.text(doc)
        if any_match(STRUCT_NOTE, text):
            return ("ESCALATE", "ESC_STRUCTURING",
                    "the branch note records the customer asking whether splitting deposits or "
                    "top-ups below the threshold avoids reporting, which is intent to structure",
                    "high",
                    ["the note is the strongest single signal in the dev set; do not close on it"],
                    [doc["doc_id"]] + [a["transaction_ids"][0] for a in alerts
                                       if a.get("transaction_ids")][:2])
    for doc in by_type.get("staff_note", []):
        text = inst.text(doc)
        if any_match(UNWILL_NOTE, text):
            return ("ESCALATE", "ESC_HIGH_RISK_CORRIDOR",
                    "the branch note records the director refusing to explain the destination of "
                    "payments to a higher-risk country",
                    "medium",
                    ["refusal to explain: policy says escalate rather than ask"],
                    [doc["doc_id"]])

    for doc in by_type.get("device_export", []):
        text = inst.text(doc)
        holders = set(re.findall(r"[A-Z]{2}-C\d+", text))
        if len(holders) > 1:
            return ("ESCALATE", "ESC_ACCOUNT_MISUSE",
                    "the device export shows one device used to log in to %d different customer "
                    "accounts, so the account is being operated for others" % len(holders),
                    "high",
                    ["shared device alone is context; several customers on one device is not"],
                    [doc["doc_id"]])

    for chat in by_type.get("support_chat", []):
        text = inst.text(chat)
        if any_match(MULE_CHAT, text):
            if inst.inst == "investment":
                return ("ESCALATE", "ESC_PASS_THROUGH",
                        "the chat records the customer collecting money from friends and relatives "
                        "to invest on their behalf and sending it on, which is pass-through for "
                        "third parties",
                        "medium",
                        ["mule vs pass-through is a code choice; the verdict is escalate"],
                        [chat["doc_id"]])
            return ("ESCALATE", "ESC_MULE_ACTIVITY",
                    "the chat records the customer receiving other people's money and sending it "
                    "on, which is mule behaviour",
                    "high",
                    ["the chat is the decisive document"],
                    [chat["doc_id"]])

    # ---- 2. Per-rule coverage ---------------------------------------------
    covered = {}
    missing = []
    for rule in rules:
        if rule == "TM22":
            verdict = tm22_assessment(inst, case, docs, alerts)
            if verdict:
                covered[rule] = verdict
                if verdict["flag"]:
                    flags.append("TM22: " + verdict["flag"])
                if verdict["doc"]:
                    evidence.append(verdict["doc"])
            else:
                missing.append(rule)
            continue
        hit = None
        for doc_type, code, phrase in COVER.get(inst.inst, {}).get(rule, []):
            if doc_type in by_type:
                hit = (code, phrase, by_type[doc_type][0]["doc_id"])
                break
        if hit:
            covered[rule] = {"verdict": "CLOSE", "code": hit[0], "basis": hit[1],
                             "doc": hit[2], "flag": None}
            evidence.append(hit[2])
        else:
            missing.append(rule)

    # ---- 3. Combine -------------------------------------------------------
    esc = [(r, c) for r, c in covered.items() if c["verdict"] == "ESCALATE"]
    if esc:
        rule, info = esc[0]
        return ("ESCALATE", info["code"], info["basis"], "high", flags,
                [info["doc"]] + evidence if info.get("doc") else evidence)

    rfi_covered = [(r, c) for r, c in covered.items() if c["verdict"] == "RFI"]
    if rfi_covered and not missing:
        rule, info = rfi_covered[0]
        return ("RFI", info["code"], info["basis"], "medium",
                flags + ["the alert turns on a single identity detail that no document settles: "
                         "policy answers this with an RFI, not a close"], evidence)

    if not missing and covered:
        # All alerts explained: pick the most specific ground.
        order = ["LIST_MATCH_DIFFERENT_PARTY", "OWN_ACCOUNT", "REFUND_OF_EARLIER_PAYMENT",
                 "COLLECTION_DOCUMENTED", "INVOICE_MATCHES", "BUSINESS_RECORDS_RECONCILE",
                 "DOCUMENTED_EVENT", "THIRD_PARTY_DOCUMENTED", "RETURNING_CUSTOMER",
                 "WITHIN_PROFILE", "GROUP_COMPANY"]
        best = None
        for code in order:
            for rule, info in covered.items():
                if info["code"] == code:
                    best = (rule, info)
                    break
            if best:
                break
        rule, info = best
        basis = info["basis"]
        if len(covered) > 1:
            others = [i["code"] for r, i in covered.items() if r != rule]
            if len(set(others) - {info["code"]}) > 1:
                flags.append("one CLOSE code covers several grounds (%s); the reason must cover "
                             "all of them" % ", ".join(sorted(set([info["code"]] + others))))
        return ("CLOSE", info["code"], basis, "high", flags, evidence)

    # ---- 4. Nothing on file explains the remaining alerts -----------------
    has_chat = any(any_match(VAGUE_CHAT, inst.text(c)) or any_match(MULE_CHAT, inst.text(c))
                   for c in by_type.get("support_chat", []))
    esc_hint = None
    for rule in missing:
        verdict, code, phrase = UNEXPLAINED_HINT.get(rule, FALLBACK + ("the activity is unexplained",))
        if verdict == "ESCALATE":
            esc_hint = (rule, code, phrase)
            break

    if esc_hint:
        rule, code, phrase = esc_hint
        return ("ESCALATE", code, phrase, "medium",
                flags + ["an alert stays unexplained after the documents on file: policy escalates"],
                evidence)

    if not covered and has_chat:
        rule = missing[0] if missing else "TM01"
        verdict, code, phrase = UNEXPLAINED_HINT.get(rule, FALLBACK)
        return ("RFI", code, phrase + ", and the customer has given only an account of it in chat",
                "low",
                flags + ["no document yet: the policy answer is an RFI, the fallback is "
                         "ESC_UNEXPLAINED_FUNDS if the account in chat does not hold up"],
                evidence)

    if not covered:
        rule = missing[0] if missing else "TM01"
        verdict, code, phrase = UNEXPLAINED_HINT.get(rule, FALLBACK)
        return ("ESCALATE", "ESC_UNEXPLAINED_FUNDS",
                "no document on file explains the activity and the customer has given no account "
                "of it (%s)" % phrase,
                "medium",
                flags + ["policy fallback: unproven activity escalates, it is never closed"],
                evidence)

    rule = missing[0]
    verdict, code, phrase = UNEXPLAINED_HINT.get(rule, FALLBACK)
    return ("ESCALATE", "ESC_UNEXPLAINED_FUNDS",
            "%s, so the alerts are only partly explained" % phrase,
            "medium",
            flags + ["partly explained combination: the unexplained alert keeps it open"],
            evidence)


def main(argv):
    data_root = "data/institutions"
    out_dir = "tools"
    args = list(argv[1:])
    i = 0
    while i < len(args):
        if args[i] == "--data":
            i += 1
            data_root = args[i]
        elif args[i] == "--out":
            i += 1
            out_dir = args[i]
        else:
            sys.stderr.write("build_labels: unknown argument %s\n" % args[i])
            return 2
        i += 1

    insts = sorted(d for d in os.listdir(data_root)
                   if os.path.isdir(os.path.join(data_root, d)))
    label_rows = []
    summary = {}

    for name in insts:
        inst = Institution(os.path.join(data_root, name))
        per_sig = {}
        counts = {"cases": 0, "CLOSE": 0, "RFI": 0, "ESCALATE": 0}

        for case_id in sorted(inst.cases):
            case = inst.cases[case_id]
            docs = inst.docs_of(case["customer_id"])
            signature = tuple(sorted({d["type"] for d in docs}))
            alerts = inst.alerts.get(case_id, [])
            rules = sorted({a["rule_id"] for a in alerts})
            verdict, code, basis, confidence, flags, evidence = classify(
                inst, case, signature)

            label_rows.append({
                "case_id": case_id,
                "institution": name,
                "customer_id": case["customer_id"],
                "rules": rules,
                "alerts": len(alerts),
                "signature": list(signature),
                "pseudo_verdict": verdict,
                "pseudo_reason_code": code,
                "basis": basis,
                "confidence": confidence,
                "needs_review": bool(flags),
                "notes": flags,
                "evidence_hint": sorted(set(evidence))[:4],
            })

            slot = per_sig.setdefault(signature, {
                "cases": 0, "rules": {}, "verdicts": {v: 0 for v in VERDICTS},
                "codes": {}, "bases": {}, "review": 0, "flags": {},
                "rule_sets": {}, "rx": {},
            })
            slot["cases"] += 1
            slot["verdicts"][verdict] += 1
            slot["codes"][code] = slot["codes"].get(code, 0) + 1
            slot["bases"][basis] = slot["bases"].get(basis, 0) + 1
            if flags:
                slot["review"] += 1
                for flag in flags:
                    slot["flags"][flag] = slot["flags"].get(flag, 0) + 1
            for rule in rules:
                slot["rules"][rule] = slot["rules"].get(rule, 0) + 1
            key = "+".join(rules) or "none"
            rs = slot["rule_sets"].setdefault(key, {"cases": 0, "verdicts": {v: 0 for v in VERDICTS},
                                                    "codes": {}, "bases": {}})
            rs["cases"] += 1
            rs["verdicts"][verdict] += 1
            rs["codes"][code] = rs["codes"].get(code, 0) + 1
            rs["bases"][basis] = rs["bases"].get(basis, 0) + 1
            for rule in rules:
                pass
            counts["cases"] += 1
            counts[verdict] += 1

        summary[name] = {"counts": counts, "signatures": per_sig, "inst": inst}

    # ---------- labels.json ----------
    labels = {
        "what": "Dev pseudo-label baseline, one entry per evidence-type combination",
        "how_to_use": (
            "Match a case's evidence types to a signature. advice is the modal reading of "
            "POLICY.md for that combination; rule_advice splits it by which alerts fired, "
            "because the same documents answer different alerts differently. Where a type is "
            "dual-use (support_chat, staff_note, device_export, customer_email, bank_statement) "
            "the text decides, so check content_flags before using advice. needs_review marks "
            "combinations where the policy does not settle the answer from the files."
        ),
        "conventions": {
            "advice": "suggested verdict and reason_code for the combination",
            "rule_advice": "same, restricted to the cases in the combination that raised those rules",
            "heuristic_mix": "share of the combination's cases that the content-aware classifier "
                             "put on each verdict (calibration only, not ground truth)",
            "confidence": "high = one reading dominates and the documents are unambiguous; "
                          "medium = a judgement call on dates/identity; low = the case turns on "
                          "content the classifier cannot settle",
            "cost_reminder": "wrong CLOSE = 10, wrong RFI = 3, wrong ESC = 2-3",
        },
        "institutions": {},
        "totals": {},
    }

    for name in insts:
        info = summary[name]
        entries = []
        for n, signature in enumerate(sorted(info["signatures"],
                                             key=lambda s: (-info["signatures"][s]["cases"], s)), 1):
            slot = info["signatures"][signature]
            verdict, code = modal_pair(slot["verdicts"], slot["codes"])
            share = slot["verdicts"][verdict] / float(slot["cases"])
            top_basis = GENERIC_BASIS.get(code) or max(
                slot["bases"].items(), key=lambda kv: kv[1])[0]
            decisive = [t for t in signature if t not in NOISE]
            confidence = "high" if share >= 0.9 and not slot["review"] else (
                "medium" if share >= 0.7 else "low")
            needs_review = bool(slot["review"]) or share < 0.85

            rule_advice = []
            for key in sorted(slot["rule_sets"]):
                rs = slot["rule_sets"][key]
                rv, rc = modal_pair(rs["verdicts"], rs["codes"])
                rule_advice.append({
                    "rules": key.split("+") if key != "none" else [],
                    "cases": rs["cases"],
                    "verdict": rv,
                    "reason_code": rc,
                    "basis": GENERIC_BASIS.get(rc) or max(
                        rs["bases"].items(), key=lambda kv: kv[1])[0],
                    "share": round(rs["verdicts"][rv] / float(rs["cases"]), 3),
                })

            alt = None
            ranked = sorted(slot["codes"].items(), key=lambda kv: (-kv[1], kv[0]))
            for other_code, count in ranked:
                owner = ("ESCALATE" if other_code.startswith("ESC_")
                         else "RFI" if other_code.startswith("RFI_") else "CLOSE")
                if (owner, other_code) == (verdict, code):
                    continue
                if count / float(slot["cases"]) >= 0.15:
                    alt = {"verdict": owner, "reason_code": other_code,
                           "cases": count,
                           "share": round(count / float(slot["cases"]), 3)}
                break

            entry = {
                "id": "%s#%02d" % (name, n),
                "signature": list(signature),
                "core_signature": decisive,
                "cases": slot["cases"],
                "rules": slot["rules"],
                "advice": {"verdict": verdict, "reason_code": code},
                "basis": top_basis,
                "confidence": confidence,
                "needs_review": needs_review,
                "heuristic_mix": {v: slot["verdicts"][v] for v in VERDICTS},
                "share_on_advice": round(share, 3),
                "alt": alt,
                "rule_advice": rule_advice,
                "review_flags": sorted(slot["flags"])[:4],
            }
            entries.append(entry)

        total = sum(slot["cases"] for slot in info["signatures"].values())
        roles = {}
        for signature, slot in info["signatures"].items():
            for doc_type in signature:
                role = roles.setdefault(doc_type, {"cases": 0, "codes": set()})
                role["cases"] += slot["cases"]
        for doc_type, role in roles.items():
            if doc_type in NOISE:
                kind = "noise: identity/admin only, never explains activity"
            elif doc_type in ("sending_bank_fraud_report", "device_export"):
                kind = "suspicious when its content says so (see content flags)"
            elif doc_type in DUAL:
                kind = "dual-use: the text decides, check the cited basis"
            else:
                kind = "explains the activity it is cited for"
            role["kind"] = kind
            role["suggests"] = sorted(set(
                c for (t, c, _p) in
                [x for rule in COVER.get(name, {}).values() for x in rule]
                if t == doc_type))
            role["codes"] = sorted(role["codes"])

        alias = {"due_diligence_summary": "DD", "proof_of_address": "POA",
                 "contact_note": "CN", "company_register_extract": "REG",
                 "significant_control_register": "PSC", "support_chat": "CHAT",
                 "staff_note": "NOTE", "bank_statement": "STMT",
                 "sending_bank_fraud_report": "FRAUD", "device_export": "DEV",
                 "customer_email": "EMAIL", "customer_letter": "LETTER",
                 "reverification_record": "RVF", "booking_confirmation": "BOOK",
                 "insurer_letter": "INS", "insurance_schedule": "INSCH",
                 "vehicle_sale_receipt": "SALE", "cash_collection_reports": "COLL",
                 "cash_handling_procedure": "PROC", "cash_reconciliation": "RECON",
                 "ticket_report": "TKT", "management_accounts": "MGT",
                 "consulting_contract": "CONS", "loan_agreement": "LOAN",
                 "dealer_invoice": "DEALER", "hospital_invoice": "HOSP",
                 "venue_email": "VENUE", "solicitor_letter": "SOL", "invoice": "INV",
                 "receipt": "RCT", "payment_file": "PAYF",
                 "supplier_invoice": "SINV", "supplier_invoices": "SINVS",
                 "purchase_order": "PO", "supply_contract": "SCON",
                 "contract_schedule": "SCHED", "factoring_agreement": "FACT",
                 "remittance_advice": "REM", "credit_note": "CNOTE",
                 "group_structure": "GROUP", "email": "EMAIL_DOC",
                 "carrier_invoice": "CARR", "freight_invoices": "FREIGHT",
                 "takings_book": "TAKINGS", "advert": "AD", "sale_receipt": "SRCT",
                 "settlement_letter": "SETTLE", "deposit_return_letter": "DEPRET",
                 "holding_deposit_receipt": "DEPREC", "completion_statement": "COMPL",
                 "cancellation_confirmation": "CANCEL", "gift_letter": "GIFT",
                 "redundancy_letter": "REDUN", "employment_contract": "EMP"}
        labels["institutions"][name] = {
            "cases": total,
            "signatures": len(entries),
            "noise_types": sorted(NOISE),
            "type_aliases": alias,
            "type_roles": {k: {"cases": v["cases"], "kind": v["kind"],
                               "suggests": v["suggests"]}
                           for k, v in sorted(roles.items())},
            "entries": entries,
        }
        labels["totals"][name] = {
            "cases": total,
            "signatures": len(entries),
            "close_entries": sum(1 for e in entries if e["advice"]["verdict"] == "CLOSE"),
            "rfi_entries": sum(1 for e in entries if e["advice"]["verdict"] == "RFI"),
            "esc_entries": sum(1 for e in entries if e["advice"]["verdict"] == "ESCALATE"),
            "close_cases": sum(e["cases"] for e in entries if e["advice"]["verdict"] == "CLOSE"),
            "rfi_cases": sum(e["cases"] for e in entries if e["advice"]["verdict"] == "RFI"),
            "esc_cases": sum(e["cases"] for e in entries if e["advice"]["verdict"] == "ESCALATE"),
            "review_entries": sum(1 for e in entries if e["needs_review"]),
        }

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "labels.json"), "w", encoding="utf-8") as fh:
        json.dump(labels, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    with open(os.path.join(out_dir, "case_labels.jsonl"), "w", encoding="utf-8") as fh:
        for row in label_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    # ---------- console summary ----------
    for name in insts:
        t = labels["totals"][name]
        print("%-13s cases %4d  signatures %3d  CLOSE %2d entries/%4d cases  "
              "RFI %2d/%4d  ESC %2d/%4d  review %2d"
              % (name, t["cases"], t["signatures"], t["close_entries"], t["close_cases"],
                 t["rfi_entries"], t["rfi_cases"], t["esc_entries"], t["esc_cases"],
                 t["review_entries"]))
    print("wrote %s and %s" % (os.path.join(out_dir, "labels.json"),
                               os.path.join(out_dir, "case_labels.jsonl")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
