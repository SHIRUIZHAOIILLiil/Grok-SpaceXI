"""Evidence access for one institution folder. Standard library only."""
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


class Index(object):
    """Lazily reads the evidence documents of one institution folder."""

    def __init__(self, institution_dir):
        self.dir = institution_dir
        self._by_customer = {}
        self._text = {}
        for row in _read_jsonl(os.path.join(institution_dir, "evidence.jsonl")):
            self._by_customer.setdefault(row["customer_id"], []).append(row)
        self._internal = _read_jsonl(os.path.join(institution_dir, "internal_list.jsonl"))
        self._reviews = {}
        for row in _read_jsonl(os.path.join(institution_dir, "previous_reviews.jsonl")):
            self._reviews.setdefault(row["customer_id"], []).append(row)

    def _doc(self, row):
        doc_id = row["doc_id"]
        text = self._text.get(doc_id)
        if text is None:
            path = os.path.join(self.dir, row.get("file", ""))
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    text = fh.read()
            except OSError:
                text = ""
            self._text[doc_id] = text
        return {
            "doc_id": doc_id,
            "type": row.get("type"),
            "title": row.get("title"),
            "dated": row.get("dated"),
            "text": text,
            "skeleton": skeleton(text),
            "amounts": _amounts(text),
        }

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
        return [d for d in self.docs(customer_id) if needle in d["text"].lower()]
