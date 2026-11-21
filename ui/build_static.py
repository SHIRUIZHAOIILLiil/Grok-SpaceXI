#!/usr/bin/env python3
"""Export the review console as a static site (no server, Vercel-ready).

    python3 ui/build_static.py                       # full export -> site/
    python3 ui/build_static.py --per-verdict 6 --out site-demo

Payload builders are reused from ui/server.py, so the static site and the live
console report exactly the same numbers. Case details are split into chunks so
the page loads a small index first and fetches one chunk per clicked case.

Document bodies are trimmed: a cited document keeps its full text, background
documents keep their head only.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import server  # noqa: E402

CITED_HEAD = 4000
OTHER_HEAD = 700
CHUNK = 100


def trim(detail, cited):
    for doc in detail.get("documents", []):
        text = doc.get("text") or ""
        cap = CITED_HEAD if doc.get("doc_id") in cited else OTHER_HEAD
        if len(text) > cap:
            doc["text"] = text[:cap].rstrip() + "\n\n[... trimmed for the static demo ...]"
    txs = detail.get("transactions") or []
    if len(txs) > 45:
        detail["transactions"] = txs[:45]
    return detail


SHIM = """
<script>
/* static-export shim: same /api shapes, served from sharded json files */
(function(){
  var orig = window.fetch.bind(window), rows = {}, chunks = {};
  function get(url){
    return orig(url).then(function(r){ if(!r.ok) throw new Error(url + ' ' + r.status); return r.json(); });
  }
  function rowsFor(inst){
    if (!rows[inst]) rows[inst] = get('data/' + inst + '.rows.json');
    return rows[inst];
  }
  function chunkFor(inst, n){
    var key = inst + '.' + n;
    if (!chunks[key]) chunks[key] = get('data/' + key + '.json');
    return chunks[key];
  }
  function pack(obj){
    return Promise.resolve(new Response(JSON.stringify(obj),
      {status:200, headers:{'Content-Type':'application/json'}}));
  }
  window.fetch = function(url, opts){
    var u = String(url), m;
    if (u.indexOf('/api/summary') === 0) return orig('data/summary.json', opts);
    if ((m = u.match(/\\/api\\/cases\\?inst=([a-z_]+)/))) {
      return rowsFor(m[1]).then(function(d){ return pack({institution:m[1], cases:d}); });
    }
    if ((m = u.match(/\\/api\\/case\\?inst=([a-z_]+)&case_id=([^&]+)/))) {
      var inst = m[1], want = m[2];
      return rowsFor(inst).then(function(list){
        var row = null, i;
        for (i = 0; i < list.length; i++) if (list[i].case_id === want) { row = list[i]; break; }
        if (!row) row = list[0];
        if (!row) return pack({error:'no cases'});
        return chunkFor(inst, row.chunk).then(function(c){
          return pack(c[row.case_id] || {error:'unknown case_id'});
        });
      });
    }
    return orig(url, opts);
  };
})();
</script>
"""

BANNER = ('<style>body{padding-bottom:46px}</style>'
          '<div style="position:fixed;left:0;right:0;bottom:0;z-index:99;'
          'background:#1b2233;border-top:1px solid #2c3550;color:#c8d3ee;'
          'font:12px/1.5 ui-sans-serif,system-ui;padding:7px 14px;text-align:center">'
          'All data is published with the organizers\' consent. '
          'Every case, customer and document is invented.</div>')


def pick(rows, per_verdict):
    keep, seen = [], {}
    for row in rows:
        verdict = row.get("verdict")
        if seen.get(verdict, 0) >= per_verdict:
            continue
        keep.append(row)
        seen[verdict] = seen.get(verdict, 0) + 1
    return keep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "site"))
    ap.add_argument("--per-verdict", type=int, default=0,
                    help="publish only N cases per verdict per institution")
    ap.add_argument("--chunk", type=int, default=CHUNK)
    args = ap.parse_args()
    out = args.out
    os.makedirs(os.path.join(out, "data"), exist_ok=True)

    summary = server.summary_payload()
    demo = args.per_verdict > 0
    totals = {"cases": 0, "alerts": 0, "docs": 0}

    for inst in summary["institutions"]:
        ident = inst["id"]
        model = server.get_inst(ident)
        all_rows = model.list_rows()
        rows = pick(all_rows, args.per_verdict) if demo else all_rows

        buckets = {}
        for i, row in enumerate(rows):
            row = dict(row)
            row["chunk"] = i // args.chunk
            buckets.setdefault(row["chunk"], {})[row["case_id"]] = model.detail(row["case_id"])
            rows[i] = row

        for n, cases in buckets.items():
            payload = {}
            for case_id, detail in cases.items():
                if detail is None:
                    continue
                payload[case_id] = trim(detail, set(detail.get("evidence") or []))
            with open(os.path.join(out, "data", "%s.%d.json" % (ident, n)), "w",
                      encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))

        with open(os.path.join(out, "data", ident + ".rows.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=False, separators=(",", ":"))

        counts = {"CLOSE": 0, "RFI": 0, "ESCALATE": 0}
        alerts = docs = 0
        for n, cases in buckets.items():
            for detail in cases.values():
                if detail is None:
                    continue
                alerts += len(detail.get("alerts") or [])
                docs += len(detail.get("documents") or [])
        for row in rows:
            counts[row.get("verdict")] = counts.get(row.get("verdict"), 0) + 1

        if demo:
            inst["verdicts"] = counts
            inst["cases"] = len(rows)
            inst["close_rate"] = counts["CLOSE"] / float(len(rows) or 1)
        totals["cases"] += len(rows)
        totals["alerts"] += alerts
        totals["docs"] += docs

    if demo:
        summary["totals"]["cases"] = totals["cases"]
        summary["totals"]["alerts"] = totals["alerts"]
        summary["totals"]["docs"] = totals["docs"]

    with open(os.path.join(out, "data", "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, separators=(",", ":"))

    page = server.PAGE.replace("<script>\nconst INSTS", SHIM + "<script>\nconst INSTS", 1)
    if page == server.PAGE:
        raise SystemExit("injection point not found in PAGE")
    page = page.replace('<meta charset="utf-8">',
                        '<meta charset="utf-8">\n'
                        '<meta name="viewport" content="width=device-width, initial-scale=1">', 1)
    page = page.replace("<body>", "<body>\n" + BANNER, 1)
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(page)

    size = 0
    for root, _dirs, files in os.walk(out):
        for name in files:
            size += os.path.getsize(os.path.join(root, name))
    print("  cases %d · alerts %d · docs %d" % (totals["cases"], totals["alerts"], totals["docs"]))
    print("  export %.1f MB -> %s" % (size / 1048576.0, out))


if __name__ == "__main__":
    main()
