# Runbook

Python 3.8+ and nothing else. No packages, no build step, no server for the system itself.

## Decide a folder

```sh
./system/run data/institutions/bank output/bank.jsonl
```

The grader calls it the same way, with absolute paths, from inside `system/`. One JSON line per case.

## Decide everything, then check it

```sh
for i in bank payments_fx emoney investment; do ./system/run data/institutions/$i output/$i.jsonl; done
python3 tools/validate.py output/bank.jsonl --data data/institutions/bank   # 0 error, 0 warning
bash tools/repro.sh                                                          # 5 runs x 4, byte-identical
python3 tools/report.py                                                      # distribution, fallback share
python3 tools/selftest.py                                                    # 43 checks on the tooling
```

## Look at one decision

```sh
python3 tools/report.py --labels tools/case_labels.jsonl     # agreement with the pseudo-labels
python3 tools/audit.py build && python3 tools/audit.py why BK-CS109535
```

`tools/audit.py` builds a SQLite index of the decisions, their alerts and every cited record, and
answers questions the JSONL cannot: which document types carry the most closes, how each rule splits
across verdicts, arbitrary SQL.

## The console

```sh
python3 ui/server.py                  # http://127.0.0.1:8000
python3 ui/build_static.py --out site  # static export, no server needed
```

`site/` is a full export (40 MB, gitignored). The public deployment serves `site-demo/`, which is
regenerated from the same payloads.

## The deck and the video

```sh
open submission/deck.html     # arrow keys, P narration, C captions, F fullscreen
```

`submission/casefile-2min.mp4` is built from nine rendered frames plus the nine narration clips:
`screenshots -> frames -> ffmpeg per slide -> concat`. Re-render by exporting the deck with
`body.export` (hides the player, page number and hint) and re-running the same pipeline.

## The audit database (optional, outside the scored path)

```sh
echo 'postgresql://...' > .neon_url     # never committed
python3 tools/neon_sync.py load
python3 tools/neon_sync.py why BK-CS109535
```

Neon speaks SQL over HTTPS, so this needs nothing beyond `urllib` and `json`.
