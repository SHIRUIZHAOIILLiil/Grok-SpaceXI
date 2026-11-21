#!/usr/bin/env python3
"""Single-page review console for Track 1 (stdlib only, no CDN, no network).

Run:
    cd /workspace && python3 ui/server.py            # http://127.0.0.1:8000
    python3 ui/server.py --port 8080 --host 0.0.0.0

Reads (read-only):  data/institutions/<inst>/{cases,alerts,customers,
                    transactions,evidence,evidence/<doc>.md,previous_reviews}
                    output/<inst>.jsonl  (system verdicts)
                    ui/benchmark.json    (measured throughput, see bench note)

Endpoints:
    GET /                     the page
    GET /api/summary          per-institution verdict mix, close rate, ms/case
    GET /api/cases?inst=NAME  case list rows
    GET /api/case?inst=NAME&case_id=ID   full case dossier
"""
import argparse
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "institutions")
OUT = os.path.join(ROOT, "output")
HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.join(HERE, "benchmark.json")

INSTITUTIONS = ("bank", "payments_fx", "emoney", "investment")
LABELS = {
    "bank": ("Bank", "Retail bank · individuals and small business"),
    "payments_fx": ("Payments & FX", "Cross-border business payments"),
    "emoney": ("E-money", "App wallets · individuals and small business"),
    "investment": ("Investment", "Broker and fund platform"),
}
VERDICTS = ("CLOSE", "RFI", "ESCALATE")

_LOCK = threading.Lock()
_STORE = {}


def read_jsonl(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


class Institution(object):
    """Lazy index over one institution folder. Reads transactions by offset."""

    def __init__(self, name):
        self.name = name
        base = os.path.join(DATA, name)
        self.base = base
        self.error = None
        self.cases = []
        self.case_by_id = {}
        self.alerts_by_case = {}
        self.customers = {}
        self.docs_by_customer = {}
        self.reviews_by_customer = {}
        self.decisions = {}
        self._tx_index = {}
        self._tx_cache = {}
        self._tx_fh = None
        self._tx_path = ""
        self._doc_cache = {}
        self._read_lock = threading.Lock()
        if not os.path.isdir(base):
            self.error = "institution folder not found: %s" % base
            return

        self.cases = sorted(read_jsonl(os.path.join(base, "cases.jsonl")),
                            key=lambda c: c["case_id"])
        self.case_by_id = {c["case_id"]: c for c in self.cases}

        for row in read_jsonl(os.path.join(base, "alerts.jsonl")):
            self.alerts_by_case.setdefault(row["case_id"], []).append(row)
        for case_id in self.alerts_by_case:
            self.alerts_by_case[case_id].sort(key=lambda a: a["alert_id"])

        for row in read_jsonl(os.path.join(base, "customers.jsonl")):
            self.customers[row["customer_id"]] = row

        for row in read_jsonl(os.path.join(base, "evidence.jsonl")):
            self.docs_by_customer.setdefault(row["customer_id"], []).append(row)
        for cid in self.docs_by_customer:
            self.docs_by_customer[cid].sort(key=lambda d: (d.get("dated") or "",
                                                           d["doc_id"]))

        for row in read_jsonl(os.path.join(base, "previous_reviews.jsonl")):
            self.reviews_by_customer.setdefault(row["customer_id"], []).append(row)

        for row in read_jsonl(os.path.join(OUT, name + ".jsonl")):
            self.decisions[row["case_id"]] = row

        self._build_tx_index()

    # -- transactions -----------------------------------------------------
    def _build_tx_index(self):
        path = os.path.join(self.base, "transactions.jsonl")
        if not os.path.exists(path):
            return
        idx = {}
        offset = 0
        with open(path, "rb") as fh:
            for raw in fh:
                size = len(raw)
                if raw.strip():
                    try:
                        cid = json.loads(raw)["customer_id"]
                    except (ValueError, KeyError):
                        cid = None
                    if cid:
                        idx.setdefault(cid, []).append((offset, size))
                offset += size
        self._tx_index = idx
        self._tx_path = path

    def transactions(self, customer_id):
        cached = self._tx_cache.get(customer_id)
        if cached is not None:
            return cached
        spans = self._tx_index.get(customer_id, [])
        rows = []
        if spans:
            with self._read_lock:
                if self._tx_fh is None:
                    self._tx_fh = open(self._tx_path, "rb")
                for offset, size in spans:
                    self._tx_fh.seek(offset)
                    try:
                        rows.append(json.loads(self._tx_fh.read(size)))
                    except ValueError:
                        continue
        rows.sort(key=lambda r: (r.get("booked_at") or "", r["transaction_id"]))
        if len(self._tx_cache) < 400:
            self._tx_cache[customer_id] = rows
        return rows

    # -- evidence ---------------------------------------------------------
    def doc_text(self, meta):
        doc_id = meta.get("doc_id")
        text = self._doc_cache.get(doc_id)
        if text is None:
            path = os.path.join(self.base, meta.get("file") or "")
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    text = fh.read()
            except OSError:
                text = ""
            if len(self._doc_cache) < 4000:
                self._doc_cache[doc_id] = text
        return text

    # -- views ------------------------------------------------------------
    def list_rows(self):
        rows = []
        for case in self.cases:
            cid = case["customer_id"]
            cust = self.customers.get(cid) or {}
            alerts = self.alerts_by_case.get(case["case_id"], [])
            dec = self.decisions.get(case["case_id"]) or {}
            rows.append({
                "case_id": case["case_id"],
                "customer_name": cust.get("name") or cid,
                "kind": cust.get("kind") or "",
                "verdict": dec.get("verdict") or "MISSING",
                "reason_code": dec.get("reason_code") or "",
                "rules": sorted({a.get("rule_id") or "" for a in alerts} - {""}),
                "alerts": len(alerts),
                "held": bool(case.get("held_payment_id")),
            })
        return rows

    def counts(self):
        mix = {v: 0 for v in VERDICTS}
        mix["MISSING"] = 0
        for case in self.cases:
            dec = self.decisions.get(case["case_id"]) or {}
            v = dec.get("verdict") or "MISSING"
            mix[v] = mix.get(v, 0) + 1
        docs = sum(len(v) for v in self.docs_by_customer.values())
        alerts = sum(len(v) for v in self.alerts_by_case.values())
        return {
            "id": self.name,
            "label": LABELS[self.name][0],
            "subtitle": LABELS[self.name][1],
            "cases": len(self.cases),
            "alerts": alerts,
            "docs": docs,
            "verdicts": mix,
            "close_rate": (mix.get("CLOSE", 0) / len(self.cases)) if self.cases else 0.0,
            "error": self.error,
        }

    def detail(self, case_id):
        case = self.case_by_id.get(case_id)
        if not case:
            return None
        cust = self.customers.get(case["customer_id"]) or {}
        alerts = self.alerts_by_case.get(case_id, [])
        dec = self.decisions.get(case_id) or {}
        window = case.get("review_window") or {}
        start, end = window.get("from", ""), window.get("to", "")
        all_tx = self.transactions(case["customer_id"])
        in_window = [t for t in all_tx if start <= (t.get("booked_at") or "")[:10] <= end]
        by_id = {t["transaction_id"]: t for t in all_tx}

        wanted = []
        for alert in alerts:
            wanted.extend(alert.get("transaction_ids") or [])
        wanted.extend(dec.get("evidence") or [])
        extra = []
        for tid in wanted:
            if tid in by_id and by_id[tid] not in in_window:
                extra.append(by_id[tid])
        shown = sorted(in_window + extra,
                       key=lambda t: (t.get("booked_at") or "", t["transaction_id"]))

        docs = []
        for meta in self.docs_by_customer.get(case["customer_id"], []):
            item = dict(meta)
            item["text"] = self.doc_text(meta)
            docs.append(item)

        return {
            "case": case,
            "customer": cust,
            "alerts": alerts,
            "transactions": shown,
            "window_tx_count": len(in_window),
            "documents": docs,
            "decision": dec,
            "previous_reviews": self.reviews_by_customer.get(case["customer_id"], []),
        }


def get_inst(name):
    if name not in INSTITUTIONS:
        raise KeyError(name)
    with _LOCK:
        inst = _STORE.get(name)
        if inst is None:
            inst = Institution(name)
            _STORE[name] = inst
        return inst


def benchmark():
    try:
        with open(BENCH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def summary_payload():
    bench = benchmark()
    per = bench.get("institutions") or {}
    rows = [get_inst(n).counts() for n in INSTITUTIONS]
    for row in rows:
        b = per.get(row["id"]) or {}
        row["ms_per_case"] = b.get("ms_per_case")
        row["seconds"] = b.get("seconds")
    totals = {
        "cases": sum(r["cases"] for r in rows),
        "alerts": sum(r["alerts"] for r in rows),
        "docs": sum(r["docs"] for r in rows),
        "verdicts": {v: sum(r["verdicts"].get(v, 0) for r in rows) for v in VERDICTS},
        "total_seconds": bench.get("total_seconds"),
        "measured_at": bench.get("measured_at"),
    }
    totals["close_rate"] = (totals["verdicts"]["CLOSE"] / totals["cases"]) if totals["cases"] else 0.0
    return {"institutions": rows, "totals": totals}


class Handler(BaseHTTPRequestHandler):
    server_version = "TrackOneDemo/1.0"

    def log_message(self, fmt, *args):
        pass

    def _send(self, status, body, ctype):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, payload, status=200):
        self._send(status, json.dumps(payload, ensure_ascii=False),
                   "application/json; charset=utf-8")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        try:
            if path in ("/", "/index.html"):
                self._send(200, PAGE, "text/html; charset=utf-8")
            elif path == "/favicon.ico":
                self._send(204, "", "image/x-icon")
            elif path == "/api/summary":
                self._json(summary_payload())
            elif path == "/api/cases":
                inst = (query.get("inst") or ["bank"])[0]
                self._json({"institution": inst, "cases": get_inst(inst).list_rows()})
            elif path == "/api/case":
                inst = (query.get("inst") or ["bank"])[0]
                case_id = (query.get("case_id") or [""])[0]
                detail = get_inst(inst).detail(case_id)
                if detail is None:
                    self._json({"error": "unknown case_id", "case_id": case_id}, 404)
                else:
                    self._json(detail)
            else:
                self._json({"error": "not found", "path": path}, 404)
        except KeyError:
            self._json({"error": "unknown institution"}, 404)
        except Exception as exc:  # keep the demo alive, report honestly
            self._json({"error": "%s: %s" % (type(exc).__name__, exc)}, 500)


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Track 1 · Alert review console</title>
<style>
:root{
  --bg:#0a0e13; --panel:#111823; --panel2:#0d141c; --line:#1e2a37;
  --txt:#e6edf3; --dim:#8b9bad; --acc:#4c8dff;
  --close:#3fb950; --rfi:#d29922; --esc:#f85149;
}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--txt);font:13px/1.5 ui-sans-serif,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;display:flex;flex-direction:column;height:100vh;overflow:hidden}
header{flex:none}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace}
button{font:inherit;color:inherit;background:none;border:0;cursor:pointer}
header{padding:12px 16px 0;border-bottom:1px solid var(--line);background:linear-gradient(180deg,#0e151d,#0a0e13)}
.htop{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
h1{font-size:15px;margin:0;letter-spacing:.2px}
.htop .sub{color:var(--dim);font-size:12px}
.facts{margin-left:auto;color:var(--dim);font-size:11.5px}
.facts b{color:var(--txt);font-weight:600}
.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:10px 0 12px}
.mcard{background:var(--panel);border:1px solid var(--line);border-radius:7px;padding:8px 10px;cursor:pointer;transition:border-color .12s;min-width:0}
.mcard:hover{border-color:#2c3f56}
.mcard.on{border-color:var(--acc);box-shadow:0 0 0 1px rgba(76,141,255,.25)}
.mcard .name{font-size:12px;font-weight:600;display:flex;justify-content:space-between;gap:6px}
.mcard .name span{color:var(--dim);font-weight:400;font-size:11px}
.mcard .sub2{color:var(--dim);font-size:10.5px;margin-top:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar{display:flex;height:6px;border-radius:3px;overflow:hidden;background:#1b2431;margin:7px 0 5px}
.bar i{display:block;height:100%}
.mcard .nums{display:flex;gap:8px;font-size:11px;color:var(--dim);white-space:nowrap;overflow:hidden}
.mcard .nums b{color:var(--txt);font-weight:600}
.mcard .nums .r{flex:1 1 auto;text-align:right}
.toolbar{display:flex;align-items:center;gap:8px;padding:8px 16px;border-bottom:1px solid var(--line);background:var(--panel2);flex-wrap:wrap;flex:none}
.tabs{display:flex;gap:2px;background:#0a1119;border:1px solid var(--line);border-radius:7px;padding:2px}
.tab{padding:5px 11px;border-radius:5px;color:var(--dim);font-size:12px}
.tab.on{background:#1b2a3d;color:#cfe2ff;box-shadow:inset 0 0 0 1px #2d4666}
input[type=search]{background:#0a1119;border:1px solid var(--line);border-radius:6px;color:var(--txt);padding:6px 9px;width:230px;font:inherit;font-size:12px}
input[type=search]:focus{outline:none;border-color:var(--acc)}
.chips{display:flex;gap:4px;margin-left:auto}
.chip{padding:4px 9px;border-radius:5px;border:1px solid var(--line);color:var(--dim);font-size:11.5px}
.chip.on{background:#1b2a3d;color:#cfe2ff;border-color:#2d4666}
.chip .n{color:var(--dim);margin-left:4px;font-size:10.5px}
main{display:grid;grid-template-columns:352px minmax(0,1fr);flex:1 1 auto;min-height:0}
.list{overflow:auto;border-right:1px solid var(--line);background:var(--panel2)}
.row{display:grid;grid-template-columns:1fr auto;gap:2px 8px;padding:7px 12px;border-bottom:1px solid #131d28;cursor:pointer}
.row:hover{background:#131e2a}
.row.on{background:#16243a;box-shadow:inset 2px 0 0 var(--acc)}
.row .id{font-size:11.5px;color:#b9c8d8}
.row .who{font-size:11px;color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.row .rt{font-size:10px;color:#6f819a;letter-spacing:.2px}
.badge{font-size:10px;font-weight:700;letter-spacing:.4px;padding:2px 6px;border-radius:4px;white-space:nowrap;align-self:center}
.b-CLOSE{color:var(--close);background:rgba(63,185,80,.13);border:1px solid rgba(63,185,80,.35)}
.b-RFI{color:var(--rfi);background:rgba(210,153,34,.13);border:1px solid rgba(210,153,34,.35)}
.b-ESCALATE{color:var(--esc);background:rgba(248,81,73,.13);border:1px solid rgba(248,81,73,.35)}
.b-MISSING{color:var(--dim);background:#16202b;border:1px solid var(--line)}
.detail{overflow:auto;padding:14px 18px 60px}
.casehead{position:sticky;top:-14px;z-index:5;background:linear-gradient(180deg,#0a0e13 78%,rgba(10,14,19,.86));padding:10px 0 8px;margin:-10px 0 0;border-bottom:1px solid var(--line)}
.ch-top{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.ch-id{font-size:15px;font-weight:600}
.ch-who{color:#c2d0de;font-size:12.5px}
.ch-win{color:var(--dim);font-size:11.5px}
.ch-verdict{margin-left:auto;display:flex;align-items:center;gap:8px}
.code{font-size:11px;color:#cdd9e5;background:#16202b;border:1px solid var(--line);border-radius:4px;padding:2px 6px}
.chain{display:flex;align-items:center;gap:6px;margin-top:8px;font-size:11px;color:var(--dim);flex-wrap:wrap}
.chain b{color:#cfe2ff;background:#16243a;border:1px solid #24374d;border-radius:4px;padding:1px 6px;font-weight:600}
.chain .arr{color:#3f5a78}
section{margin-top:16px}
.sechead{display:flex;align-items:baseline;gap:8px;margin-bottom:7px}
.sechead .n{width:18px;height:18px;border-radius:50%;background:#1b2a3d;color:#9ec1ff;font-size:10.5px;display:inline-flex;align-items:center;justify-content:center;border:1px solid #2d4666;flex:none}
.sechead h2{font-size:12px;margin:0;text-transform:uppercase;letter-spacing:.7px;color:#a9bacd;font-weight:600}
.sechead .hint{color:#6f819a;font-size:11px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:7px;padding:10px 12px;margin-bottom:8px}
.alert .ahead{display:flex;align-items:center;gap:7px;flex-wrap:wrap}
.rule{font-size:10.5px;font-weight:700;color:#9ec1ff;background:#16243a;border:1px solid #24374d;border-radius:4px;padding:1px 5px;letter-spacing:.4px}
.rname{color:#c2d0de;font-size:12px}
.amsg{margin:6px 0 7px;color:#dbe5ee;font-size:12.5px}
.measured{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:4px 10px;border-top:1px dashed #1c2836;padding-top:6px}
.m{display:flex;justify-content:space-between;gap:8px;font-size:11px}
.m span{color:#7d90a6}
.m b{font-weight:600;color:#cfdbe7}
.m.wide{grid-column:1/-1;flex-direction:column;gap:1px}
.m.wide b{color:#dbe5ee;line-height:1.45}
.heldtag{font-size:9px;font-weight:700;letter-spacing:.4px;text-transform:uppercase;color:#e3b341;border:1px solid rgba(210,153,34,.45);background:rgba(210,153,34,.12);border-radius:3px;padding:0 4px;vertical-align:1px}
.kindtag{font-size:9.5px;text-transform:uppercase;letter-spacing:.4px;color:#8fa3b8;border:1px solid #24374d;border-radius:3px;padding:1px 4px;margin-left:5px}
.kv{display:grid;grid-template-columns:132px 1fr;gap:3px 10px;font-size:12px}
.kv dt{color:#7d90a6}
.kv dd{margin:0;color:#dbe5ee}
.subhead{font-size:10.5px;text-transform:uppercase;letter-spacing:.7px;color:#6f819a;margin:9px 0 5px}
table.tx{width:100%;border-collapse:collapse;font-size:11.5px}
table.tx th{text-align:left;color:#7d90a6;font-weight:500;font-size:10.5px;text-transform:uppercase;letter-spacing:.4px;border-bottom:1px solid var(--line);padding:4px 6px;position:sticky;top:0;background:var(--panel)}
table.tx td{padding:4px 6px;border-bottom:1px solid #131d28;vertical-align:top}
table.tx tr.hit td{background:rgba(76,141,255,.09)}
table.tx td.amt{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.in{color:var(--close)} .out{color:#e3989a}
.txwrap{max-height:300px;overflow:auto;border:1px solid var(--line);border-radius:7px;background:var(--panel)}
.doc{border:1px solid var(--line);border-radius:7px;background:var(--panel);margin-bottom:6px;overflow:hidden}
.doc.cited{border-color:#4176b4;background:#101d2b;box-shadow:inset 3px 0 0 #4c8dff}
.doc.open{border-color:#2d4666}
.dhead{display:flex;gap:9px;align-items:flex-start;padding:8px 11px;cursor:pointer}
.dhead:hover{background:#131e2a}
.dtype{font-size:9.5px;color:#9ec1ff;background:#16243a;border:1px solid #24374d;border-radius:3px;padding:2px 5px;white-space:nowrap;letter-spacing:.3px}
.dtitle{font-size:12px;color:#dbe5ee}
.dmeta{color:#7d90a6;font-size:10.5px;margin-top:1px}
.citedtag{font-size:9.5px;color:#8ec1ff;border:1px solid #2f4d70;border-radius:3px;padding:1px 4px;margin-left:6px;white-space:nowrap}
.chev{margin-left:auto;color:#5f7286;font-size:11px;padding-top:2px}
.dbody{display:none;border-top:1px solid var(--line);padding:9px 12px;background:#0b1219}
.doc.open .dbody{display:block}
.docmd{font-size:12px;color:#cfdbe7}
.docmd p{margin:0 0 5px}
.docmd h4{margin:0 0 6px;font-size:12px;color:#eaf2fa}
.docmd table{border-collapse:collapse;width:100%;margin:4px 0 6px;font-size:11.5px}
.docmd th,.docmd td{border:1px solid #1e2a37;padding:3px 6px;text-align:left}
.docmd th{color:#8fa3b8;font-weight:500}
.decision{border:1px solid var(--line);border-radius:8px;background:var(--panel);padding:12px 14px}
.decision.v-CLOSE{border-color:rgba(63,185,80,.4);background:linear-gradient(180deg,rgba(63,185,80,.07),var(--panel) 55%)}
.decision.v-RFI{border-color:rgba(210,153,34,.4);background:linear-gradient(180deg,rgba(210,153,34,.07),var(--panel) 55%)}
.decision.v-ESCALATE{border-color:rgba(248,81,73,.4);background:linear-gradient(180deg,rgba(248,81,73,.07),var(--panel) 55%)}
.dtop{display:flex;align-items:center;gap:9px;flex-wrap:wrap}
.vbig{font-size:15px;font-weight:700;letter-spacing:.5px}
.v-CLOSE .vbig{color:var(--close)} .v-RFI .vbig{color:var(--rfi)} .v-ESCALATE .vbig{color:var(--esc)}
.reason{margin:9px 0 0;color:#dfe8f1;font-size:13px;line-height:1.62}
mark.evref{background:rgba(76,141,255,.22);color:#cfe2ff;border-bottom:1px solid #4c8dff;padding:0 1px;border-radius:2px;cursor:pointer}
.evlist{margin-top:9px;display:flex;gap:5px;flex-wrap:wrap;border-top:1px dashed #1c2836;padding-top:8px;align-items:center}
.evlist .lab{font-size:10.5px;color:#7d90a6;text-transform:uppercase;letter-spacing:.5px;margin-right:2px}
.evc{font-size:10.5px;border-radius:4px;padding:2px 6px;border:1px solid #2f4d70;background:#16243a;color:#a9cdf5;cursor:pointer}
.evc.doc{background:#172a1c;border-color:#2f5b36;color:#9ad6a5}
.evc.tx{background:#16243a;border-color:#2f4d70;color:#a9cdf5}
.evc:hover{filter:brightness(1.35)}
.emptynote{color:#7d90a6;font-size:12px;padding:12px;border:1px dashed var(--line);border-radius:7px}
details.raw{margin-top:10px}
details.raw summary{color:#7d90a6;font-size:11px;cursor:pointer}
pre.rawjson{margin:6px 0 0;background:#0a1119;border:1px solid var(--line);border-radius:6px;padding:8px 10px;font-size:11px;color:#b9c8d8;white-space:pre-wrap;word-break:break-all}
.flash{animation:fl 1.2s ease-out}
@keyframes fl{0%{box-shadow:0 0 0 2px #4c8dff}100%{box-shadow:0 0 0 0 rgba(76,141,255,0)}}
.revs{font-size:11.5px;color:#8b9bad}
.revs div{padding:3px 0;border-bottom:1px solid #131d28;display:flex;gap:8px}
.revs .rv{color:#9ad6a5}
@media (max-width:1180px){.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.mcard .sub2{display:none}}
@media (max-height:640px){body{overflow:auto}main{min-height:520px}}
::-webkit-scrollbar{width:9px;height:9px}
::-webkit-scrollbar-thumb{background:#233141;border-radius:5px}
::-webkit-scrollbar-track{background:transparent}
</style>
</head>
<body>
<header>
  <div class="htop">
    <h1>Track 1 · Suspicious payment alert review</h1>
    <span class="sub">alert → evidence → verdict → reason, every claim clickable</span>
    <span class="facts" id="facts"></span>
  </div>
  <div class="metrics" id="metrics"></div>
</header>
<div class="toolbar">
  <div class="tabs" id="tabs"></div>
  <input id="q" type="search" placeholder="Search case ID or customer…" autocomplete="off" spellcheck="false">
  <div class="chips" id="chips"></div>
</div>
<main>
  <div class="list" id="list"><div class="emptynote" style="margin:10px">Loading…</div></div>
  <div class="detail" id="detail"><div class="emptynote">Pick a case.</div></div>
</main>
<script>
const INSTS = ["bank","payments_fx","emoney","investment"];
const state = {inst:"bank", cases:[], filter:"ALL", q:"", caseId:null, summary:null, detail:null};

const esc = s => String(s==null?"":s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const money = v => "£" + Number(v||0).toLocaleString("en-GB",{minimumFractionDigits:2,maximumFractionDigits:2});
const pct = v => (v*100).toFixed(1) + "%";

function jsonFetch(url){ return fetch(url).then(r => r.json()); }

function fmtLabel(k){
  let t = k.replace(/_gbp$/,"").replace(/_/g," ");
  if (t === "distinct counterparties") return "distinct parties";
  if (t === "window days") return "window (days)";
  return t;
}
function fmtVal(k, v){
  if (typeof v === "number"){
    if (/_gbp$/.test(k) || (k === "limit" && v >= 100)) return money(v);
    return String(v);
  }
  if (typeof v === "boolean") return v ? "yes" : "no";
  if (v === null || v === "") return "—";
  return String(v);
}

/* ---------- metrics ---------- */
function renderMetrics(){
  const s = state.summary;
  if (!s) return;
  const t = s.totals;
  document.getElementById("facts").innerHTML =
    "<b>" + t.cases.toLocaleString() + "</b> cases · <b>" + t.alerts.toLocaleString() +
    "</b> alerts · <b>" + t.docs.toLocaleString() + "</b> evidence documents · 4 institutions";
  const cards = s.institutions.map(inst => {
    const n = inst.cases || 1;
    const seg = k => (inst.verdicts[k]||0) / n * 100;
    const ms = inst.ms_per_case == null ? "—" : inst.ms_per_case.toFixed(2) + " ms";
    return '<div class="mcard' + (inst.id===state.inst?' on':'') + '" data-inst="' + inst.id + '">' +
      '<div class="name">' + esc(inst.label) + '<span>' + inst.cases.toLocaleString() + ' cases</span></div>' +
      '<div class="sub2">' + esc(inst.subtitle) + '</div>' +
      '<div class="bar"><i style="width:' + seg("CLOSE") + '%;background:var(--close)"></i>' +
        '<i style="width:' + seg("RFI") + '%;background:var(--rfi)"></i>' +
        '<i style="width:' + seg("ESCALATE") + '%;background:var(--esc)"></i></div>' +
      '<div class="nums"><span><b>' + (inst.verdicts.CLOSE||0) + '</b> close</span>' +
        '<span><b>' + (inst.verdicts.RFI||0) + '</b> rfi</span>' +
        '<span><b>' + (inst.verdicts.ESCALATE||0) + '</b> esc</span></div>' +
      '<div class="nums" style="margin-top:3px"><span>CLOSE rate <b>' + pct(inst.close_rate) + '</b></span>' +
        '<span class="r"><b>' + ms + '</b>/case</span></div>' +
      '</div>';
  }).join("");
  document.getElementById("metrics").innerHTML = cards;
  document.querySelectorAll(".mcard").forEach(el => el.onclick = () => selectInst(el.dataset.inst));
}

/* ---------- tabs / list ---------- */
function renderTabs(){
  const s = state.summary; if (!s) return;
  document.getElementById("tabs").innerHTML = s.institutions.map(i =>
    '<button class="tab' + (i.id===state.inst?' on':'') + '" data-inst="' + i.id + '">' + esc(i.label) + '</button>'
  ).join("");
  document.querySelectorAll(".tab").forEach(b => b.onclick = () => selectInst(b.dataset.inst));
}

function renderChips(){
  const counts = {ALL: state.cases.length, CLOSE:0, RFI:0, ESCALATE:0, MISSING:0};
  state.cases.forEach(c => counts[c.verdict] = (counts[c.verdict]||0)+1);
  const order = ["ALL","CLOSE","RFI","ESCALATE"];
  document.getElementById("chips").innerHTML = order.map(k =>
    '<button class="chip' + (state.filter===k?' on':'') + '" data-f="' + k + '">' +
    (k==="ALL"?"All":k) + '<span class="n">' + (counts[k]||0).toLocaleString() + '</span></button>'
  ).join("");
  document.querySelectorAll(".chip").forEach(b => b.onclick = () => { state.filter = b.dataset.f; renderChips(); renderList(); });
}

function visible(){
  const q = state.q.trim().toLowerCase();
  return state.cases.filter(c => {
    if (state.filter !== "ALL" && c.verdict !== state.filter) return false;
    if (!q) return true;
    return c.case_id.toLowerCase().includes(q) || (c.customer_name||"").toLowerCase().includes(q);
  });
}

function renderList(){
  const rows = visible();
  const list = document.getElementById("list");
  if (!rows.length){ list.innerHTML = '<div class="emptynote" style="margin:10px">No case matches.</div>'; return; }
  list.innerHTML = rows.map(c =>
    '<div class="row' + (c.case_id===state.caseId?' on':'') + '" data-id="' + esc(c.case_id) + '">' +
      '<div class="id mono">' + esc(c.case_id) + (c.held?' <span class="heldtag" title="outgoing payment held pending this review">held</span>':'') + '</div>' +
      '<div class="badge b-' + esc(c.verdict) + '">' + esc(c.verdict) + '</div>' +
      '<div class="who">' + esc(c.customer_name) + '</div>' +
      '<div class="rt">' + (c.rules||[]).join(" · ") + ' · ' + c.alerts + ' alert' + (c.alerts>1?'s':'') + '</div>' +
    '</div>').join("");
  list.querySelectorAll(".row").forEach(r => r.onclick = () => selectCase(r.dataset.id));
}

/* ---------- detail ---------- */
function mdLite(text){
  const lines = String(text||"").split("\n");
  let out = [], table = null;
  const closeTable = () => { if (table){ out.push("<table>" + table.join("") + "</table>"); table = null; } };
  lines.forEach(raw => {
    const line = raw.replace(/\r$/,"");
    let s = esc(line);
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    if (/^\s*\|/.test(line)){
      const cells = line.trim().replace(/^\|/,"").replace(/\|$/,"").split("|");
      if (cells.every(c => /^\s*:?-{2,}:?\s*$/.test(c))) return;
      const tag = (table && table.length) ? "td" : "th";
      table = table || [];
      table.push("<tr>" + cells.map(c => "<" + tag + ">" + esc(c.trim()).replace(/\*\*([^*]+)\*\*/g,"<strong>$1</strong>") + "</" + tag + ">").join("") + "</tr>");
      return;
    }
    closeTable();
    const t = line.trim();
    if (!t) return;
    if (/^#{1,3}\s/.test(t)){ out.push("<h4>" + esc(t.replace(/^#{1,3}\s+/,"")) + "</h4>"); return; }
    out.push("<p>" + s + "</p>");
  });
  closeTable();
  return out.join("") || '<p style="color:#7d90a6">(empty document)</p>';
}

function docCard(d, cited){
  const id = d.doc_id;
  return '<div class="doc' + (cited?' cited':'') + '" id="ref-' + esc(id) + '" data-doc="' + esc(id) + '">' +
    '<div class="dhead" data-toggle="1">' +
      '<span class="dtype">' + esc((d.type||"").replace(/_/g," ")) + '</span>' +
      '<div style="min-width:0"><div class="dtitle">' + esc(d.title) + (cited?'<span class="citedtag">cited</span>':'') + '</div>' +
      '<div class="dmeta mono">' + esc(id) + ' · dated ' + esc(d.dated||"—") + '</div></div>' +
      '<span class="chev">&#9662;</span></div>' +
    '<div class="dbody"><div class="docmd">' + mdLite(d.text) + '</div></div></div>';
}

function renderDetail(){
  const d = state.detail;
  if (!d) return;
  const c = d.case, cust = d.customer || {}, dec = d.decision || {}, alerts = d.alerts || [];
  const evIds = dec.evidence || [];
  const docIds = new Set((d.documents||[]).map(x => x.doc_id));
  const txIds = new Set((d.transactions||[]).map(x => x.transaction_id));
  const citedDocs = evIds.filter(x => docIds.has(x));
  const citedTx = evIds.filter(x => txIds.has(x));
  const kind = cust.kind || "";
  const isBiz = kind !== "individual";
  const nameRow = isBiz
    ? '<dt>Legal name</dt><dd>' + esc(cust.name) + ' <span class="kindtag">' + esc(kind) + '</span></dd>' +
      '<dt>Company number</dt><dd class="mono">' + esc(cust.company_number||"—") + '</dd>' +
      '<dt>Incorporated</dt><dd>' + esc(cust.incorporated_on||"—") + '</dd>' +
      '<dt>Business activity</dt><dd>' + esc(cust.business_activity||"—") + '</dd>'
    : '<dt>Name</dt><dd>' + esc(cust.name) + ' <span class="kindtag">' + esc(kind) + '</span></dd>' +
      '<dt>Date of birth</dt><dd>' + esc(cust.date_of_birth||"—") + '</dd>' +
      '<dt>Occupation</dt><dd>' + esc(cust.occupation||"—") + '</dd>' +
      '<dt>Employer</dt><dd>' + esc(cust.employer||"—") + '</dd>';
  const decl = cust.declared || {};
  const declRows = Object.keys(decl).map(k => {
    let v = decl[k];
    if (Array.isArray(v)) v = v.join(", ");
    else if (typeof v === "number" && /_gbp$/.test(k)) v = money(v);
    return '<dt>' + esc(k.replace(/_gbp$/,"").replace(/_/g," ")) + '</dt><dd>' + esc(v==null?"—":v) + '</dd>';
  }).join("");

  const alertHtml = alerts.map(a => {
    const measured = Object.keys(a.measured||{}).map(k => {
      const shown = fmtVal(k, a.measured[k]);
      const wide = String(shown).length > 30 ? ' wide' : '';
      return '<div class="m' + wide + '"><span>' + esc(fmtLabel(k)) + '</span><b>' + esc(shown) + '</b></div>';
    }).join("");
    return '<div class="card alert">' +
      '<div class="ahead"><span class="rule">' + esc(a.rule_id) + '</span>' +
      '<span class="rname">' + esc(a.rule_name) + '</span>' +
      '<span class="code mono" style="margin-left:auto">' + esc(a.alert_id) + '</span></div>' +
      '<div class="amsg">' + esc(a.message) + '</div>' +
      (measured ? '<div class="measured">' + measured + '</div>' : '') +
      ((a.transaction_ids||[]).length ? '<div class="dmeta mono" style="margin-top:6px">fired on ' + (a.transaction_ids||[]).map(esc).join(" · ") + '</div>' : '') +
      '</div>';
  }).join("") || '<div class="emptynote">No alert rows attached to this case.</div>';

  const txRows = (d.transactions||[]).map(t => {
    const hit = alerts.some(a => (a.transaction_ids||[]).includes(t.transaction_id)) || evIds.includes(t.transaction_id);
    return '<tr class="' + (hit?'hit':'') + '" id="ref-' + esc(t.transaction_id) + '">' +
      '<td class="mono">' + esc((t.booked_at||"").slice(0,10)) + '</td>' +
      '<td class="' + (t.direction==="in"?"in":"out") + '">' + esc(t.direction) + '</td>' +
      '<td class="amt">' + money(t.amount_gbp) + '</td>' +
      '<td>' + esc(t.counterparty_name||"—") + '</td>' +
      '<td>' + esc(t.channel||"") + '</td>' +
      '<td>' + esc(t.counterparty_country||"") + '</td>' +
      '<td class="mono" style="color:#6f819a">' + esc(t.reference||"") + '</td></tr>';
  }).join("");

  const docsHtml = (d.documents||[]).map(x => docCard(x, citedDocs.includes(x.doc_id))).join("")
    || '<div class="emptynote">No documents on file for this customer.</div>';

  let reason = esc(dec.reason || "");
  evIds.forEach(id => { reason = reason.split(esc(id)).join('<mark class="evref" data-id="' + esc(id) + '">' + esc(id) + '</mark>'); });

  const evChips = evIds.map(id => {
    const cls = docIds.has(id) ? "doc" : (txIds.has(id) ? "tx" : "");
    const lab = docIds.has(id) ? "document" : (txIds.has(id) ? "transaction" : "id not in case files");
    return '<span class="evc ' + cls + '" data-id="' + esc(id) + '" title="' + lab + '">' + esc(id) + '</span>';
  }).join("") || '<span style="color:#7d90a6;font-size:11px">none</span>';

  const revs = d.previous_reviews || [];
  const revHtml = revs.length ? '<div class="subhead">Earlier reviews (context only — they do not explain new activity)</div>' +
    '<div class="revs">' + revs.slice(0,6).map(r =>
      '<div><span class="mono" style="color:#7d90a6">' + esc(r.reviewed_on) + '</span>' +
      '<span class="rv">' + esc(r.verdict) + '</span>' +
      '<span>' + esc(r.note||"") + '</span></div>').join("") + '</div>' : "";

  const verdict = dec.verdict || "MISSING";
  const html =
    '<div class="casehead"><div class="ch-top">' +
      '<span class="ch-id mono">' + esc(c.case_id) + '</span>' +
      '<span class="ch-who">' + esc(cust.name||"—") + '</span>' +
      '<span class="ch-win">window ' + esc((c.review_window||{}).from||"?") + ' → ' + esc((c.review_window||{}).to||"?") +
        ' · opened ' + esc((c.opened_at||"").slice(0,10)) + '</span>' +
      '<span class="ch-verdict"><span class="badge b-' + esc(verdict) + '">' + esc(verdict) + '</span>' +
        '<span class="code mono">' + esc(dec.reason_code||"no decision line") + '</span></span>' +
    '</div>' +
    '<div class="chain">' +
      '<b>' + alerts.length + '</b> alert' + (alerts.length===1?'':'s') + ' <span class="arr">→</span> ' +
      '<b>' + (d.window_tx_count||0) + '</b> transactions in window <span class="arr">→</span> ' +
      '<b>' + (d.documents||[]).length + '</b> documents on file <span class="arr">→</span> ' +
      '<b>' + evIds.length + '</b> evidence ID' + (evIds.length===1?'':'s') + ' cited <span class="arr">→</span> verdict <b>' + esc(verdict) + '</b>' +
    '</div></div>' +

    '<section><div class="sechead"><span class="n">1</span><h2>Alerts raised</h2>' +
      '<span class="hint">what the monitoring rules measured</span></div>' + alertHtml + '</section>' +

    '<section><div class="sechead"><span class="n">2</span><h2>Customer profile</h2>' +
      '<span class="hint">declared at onboarding — the baseline the alert is measured against</span></div>' +
      '<div class="card"><dl class="kv">' + nameRow +
      '<dt>Risk rating</dt><dd>' + esc(cust.risk_rating||"—") + '</dd>' +
      '<dt>Onboarded</dt><dd>' + esc(cust.onboarded_on||"—") + '</dd>' +
      '<dt>Address</dt><dd>' + esc(cust.address||"—") + '</dd>' +
      '</dl><div class="subhead">Declared profile</div><dl class="kv">' + (declRows||'<dd>—</dd>') + '</dl></div>' +
      revHtml + '</section>' +

    '<section><div class="sechead"><span class="n">3</span><h2>Transactions in the review window</h2>' +
      '<span class="hint">' + (d.window_tx_count||0) + ' rows · rows touched by an alert are highlighted</span></div>' +
      (txRows ? '<div class="txwrap"><table class="tx"><thead><tr><th>Date</th><th>Dir</th><th style="text-align:right">Amount</th><th>Counterparty</th><th>Channel</th><th>Country</th><th>Reference</th></tr></thead><tbody>' + txRows + '</tbody></table></div>'
              : '<div class="emptynote">No transactions book in this window.</div>') +
      '</section>' +

    '<section><div class="sechead"><span class="n">4</span><h2>Evidence documents</h2>' +
      '<span class="hint">' + (d.documents||[]).length + ' on file · ' + citedDocs.length + ' cited by the decision · click a title to read it</span></div>' +
      docsHtml + '</section>' +

    '<section><div class="sechead"><span class="n">5</span><h2>Verdict and reason</h2>' +
      '<span class="hint">generated by system/run — one verdict settles every alert in the case</span></div>' +
      '<div class="decision v-' + esc(verdict) + '">' +
        '<div class="dtop"><span class="vbig">' + esc(verdict) + '</span>' +
        '<span class="code mono">' + esc(dec.reason_code||"—") + '</span>' +
        '<span style="margin-left:auto;color:#7d90a6;font-size:11px">' + evIds.length + ' cited: ' +
          citedDocs.length + (citedDocs.length===1?' document':' documents') + ', ' +
          citedTx.length + (citedTx.length===1?' transaction':' transactions') + '</span></div>' +
        '<p class="reason">' + (reason || '<span style="color:#7d90a6">No decision line for this case in output/.</span>') + '</p>' +
        '<div class="evlist"><span class="lab">Evidence</span>' + evChips + '</div>' +
        '<details class="raw"><summary>output line (contract shape)</summary><pre class="rawjson mono">' +
          esc(JSON.stringify(dec, null, 2)) + '</pre></details>' +
      '</div></section>';

  document.getElementById("detail").innerHTML = html;
  document.getElementById("detail").scrollTop = 0;
  document.querySelectorAll("#detail .dhead").forEach(h => h.onclick = () => h.parentElement.classList.toggle("open"));
  document.querySelectorAll("#detail .evc, #detail .evref").forEach(el => el.onclick = () => jumpTo(el.dataset.id));
}

function jumpTo(id){
  const el = document.getElementById("ref-" + id);
  if (!el) return;
  if (el.classList.contains("doc")) el.classList.add("open");
  el.scrollIntoView({block:"center", behavior:"smooth"});
  el.classList.remove("flash");
  void el.offsetWidth;
  el.classList.add("flash");
}

/* ---------- flow ---------- */
function loadCases(inst, after){
  jsonFetch("/api/cases?inst=" + encodeURIComponent(inst)).then(d => {
    state.cases = d.cases || [];
    renderChips();
    if (after) after();
  });
}

function selectInst(inst){
  state.inst = inst;
  state.filter = "ALL";
  state.q = "";
  document.getElementById("q").value = "";
  renderMetrics(); renderTabs();
  loadCases(inst, () => {
    const first = visible()[0];
    if (first) selectCase(first.case_id, true); else renderList();
  });
}

function selectCase(id, fromList){
  state.caseId = id;
  renderList();
  const row = document.querySelector('#list .row[data-id="' + id + '"]');
  if (row && fromList) row.scrollIntoView({block:"nearest"});
  location.hash = state.inst + "/" + id;
  jsonFetch("/api/case?inst=" + encodeURIComponent(state.inst) + "&case_id=" + encodeURIComponent(id))
    .then(d => {
      if (d.error){ document.getElementById("detail").innerHTML = '<div class="emptynote">' + esc(d.error) + '</div>'; return; }
      state.detail = d;
      renderDetail();
    });
}

document.getElementById("q").addEventListener("input", e => { state.q = e.target.value; renderList(); });
document.getElementById("q").addEventListener("keydown", e => {
  if (e.key === "Enter"){ const first = visible()[0]; if (first) selectCase(first.case_id, true); }
  if (e.key === "Escape"){ e.target.value = ""; state.q = ""; renderList(); }
});

jsonFetch("/api/summary").then(s => {
  state.summary = s;
  const h = (location.hash||"").replace(/^#/,"");
  const parts = h.split("/");
  if (INSTS.includes(parts[0])) state.inst = parts[0];
  renderMetrics(); renderTabs();
  loadCases(state.inst, () => {
    if (parts[1]) selectCase(parts[1]);
    else { const first = visible()[0]; if (first) selectCase(first.case_id, true); }
  });
});
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description="Track 1 demo console")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()

    def preload():
        for name in INSTITUTIONS:
            try:
                get_inst(name)
            except Exception as exc:  # keep serving; the page shows the error
                print("warn: could not index %s: %s" % (name, exc))

    threading.Thread(target=preload, daemon=True).start()

    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    srv.daemon_threads = True
    print("Track 1 demo console -> http://%s:%d" % (args.host, args.port))
    print("data: %s   output: %s" % (DATA, OUT))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
