#!/usr/bin/env python3
"""Export the review console as a static site (no server, Vercel-ready).

    python3 ui/build_static.py [--out site]

Reuses ui/server.py's payload builders so the static site and the live console
show exactly the same numbers. Document bodies are trimmed to keep the bundle
small: a cited document keeps its full text, background documents keep a head.
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
/* static-export shim: same /api shapes, served from json files */
(function(){
  var orig = window.fetch.bind(window), cache = {};
  function inst(id){
    if (!cache[id]) cache[id] = orig('data/' + id + '.json').then(function(r){ return r.json(); });
    return cache[id];
  }
  function pack(obj){
    return Promise.resolve(new Response(JSON.stringify(obj), {status:200, headers:{'Content-Type':'application/json'}}));
  }
  window.fetch = function(url, opts){
    var u = String(url);
    if (u.indexOf('/api/summary') === 0) return orig('data/summary.json', opts);
    var m1 = u.match(/\\/api\\/cases\\?inst=([a-z_]+)/);
    if (m1) return inst(m1[1]).then(function(d){ return pack({institution:m1[1], cases:d.rows}); });
    var m2 = u.match(/\\/api\\/case\\?inst=([a-z_]+)&case_id=([^&]+)/);
    if (m2) return inst(m2[1]).then(function(d){
      var hit = d.details[m2[2]];
      if (!hit) { var first = d.rows[0]; hit = first ? d.details[first.case_id] : null; }
      return pack(hit || {error:'unknown case_id'});
    });
    return orig(url, opts);
  };
})();
</script>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "site"))
    ap.add_argument("--per-verdict", type=int, default=0,
                    help="publish only N cases per verdict per institution (demo subset)")
    args = ap.parse_args()
    out = args.out
    os.makedirs(os.path.join(out, "data"), exist_ok=True)

    summary = server.summary_payload()
    demo = args.per_verdict > 0

    total = 0
    subset_counts = {}
    for inst in summary["institutions"]:
        ident = inst["id"]
        model = server.get_inst(ident)
        rows = model.list_rows()
        if demo:
            keep, seen = [], {}
            for row in rows:
                verdict = row.get("verdict")
                if seen.get(verdict, 0) >= args.per_verdict:
                    continue
                keep.append(row)
                seen[verdict] = seen.get(verdict, 0) + 1
            rows = keep
        details = {}
        for row in rows:
            detail = model.detail(row["case_id"])
            if detail is None:
                continue
            cited = {e for e in (detail.get("evidence") or [])}
            details[row["case_id"]] = trim(detail, cited)
        payload = {"institution": ident, "rows": rows, "details": details}
        path = os.path.join(out, "data", ident + ".json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
        subset_counts[ident] = (
            len(details),
            sum(len(d.get("alerts") or []) for d in details.values()),
            sum(len(d.get("documents") or []) for d in details.values()),
        )
        mb = os.path.getsize(path) / 1048576.0
        total += mb
        print("  %-13s %5.1f MB  (%d cases)" % (ident, mb, len(rows)))

    if demo:
        kept = {i["id"]: i for i in summary["institutions"]}
        for ident, inst in kept.items():
            model = server.get_inst(ident)
            rows = model.list_rows()
            picks, seen = [], {}
            for row in rows:
                verdict = row.get("verdict")
                if seen.get(verdict, 0) >= args.per_verdict:
                    continue
                picks.append(row)
                seen[verdict] = seen.get(verdict, 0) + 1
            counts = {"CLOSE": 0, "RFI": 0, "ESCALATE": 0}
            for row in picks:
                counts[row.get("verdict")] = counts.get(row.get("verdict"), 0) + 1
            inst["verdicts"] = counts
            inst["cases"] = len(picks)
            inst["close_rate"] = (counts["CLOSE"] / float(len(picks))) if picks else 0.0
        summary["totals"]["cases"] = sum(c[0] for c in subset_counts.values())
        summary["totals"]["alerts"] = sum(c[1] for c in subset_counts.values())
        summary["totals"]["docs"] = sum(c[2] for c in subset_counts.values())

    with open(os.path.join(out, "data", "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, separators=(",", ":"))

    page = server.PAGE.replace("<script>\nconst INSTS", SHIM + "<script>\nconst INSTS", 1)
    if page == server.PAGE:
        raise SystemExit("injection point not found in PAGE")
    page = page.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">', 1)
    if demo:
        banner = ('<div style="position:fixed;left:0;right:0;bottom:0;z-index:99;'
                  'background:#1b2233;border-top:1px solid #2c3550;color:#c8d3ee;'
                  'font:12px/1.5 ui-sans-serif,system-ui;padding:7px 14px;text-align:center">'
                  'Demo subset &middot; a sample of cases per institution, published for review. '
                  'The full console runs locally over all 4,000 cases.</div>')
        page = page.replace("<body>", "<body>\n" + banner, 1)
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(page)
    print("  index.html    %.0f KB" % (os.path.getsize(os.path.join(out, "index.html")) / 1024.0))
    print("  total data   %.1f MB -> %s" % (total, out))


if __name__ == "__main__":
    main()
