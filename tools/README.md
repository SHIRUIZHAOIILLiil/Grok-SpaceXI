# tools/ — validation, reproducibility, reporting, pseudo-labels

Owner: C. Nothing here is imported by `system/`; these are the checks we run
against it. Python 3 standard library only.

| file | what it does | exit code |
|---|---|---|
| `validate.py` | checks one output file against docs/CONTRACT.md §2/§5 | 0 pass, 1 fail, 2 bad usage |
| `repro.sh` | runs all four institutions N times and byte-compares | 0 identical, 1 difference |
| `report.py` | verdict/rule/reason/evidence statistics, optional agreement with the labels | 0 |
| `labels.json` + `LABELS.md` | the dev pseudo-label table, by evidence-type combination | — |
| `build_labels.py` + `render_labels_md.py` | regenerate the two files above from `data/` | 0 |
| `selftest.py` | proves the tools themselves work (11 injected faults + a control) | 0 all checks pass |

## Typical loop

```sh
./system/run data/institutions/bank output/bank.jsonl
python3 tools/validate.py output/bank.jsonl --data data/institutions/bank
python3 tools/report.py --labels tools/case_labels.jsonl
```

Before the freeze:

```sh
tools/repro.sh 5                     # 5 runs x 4 institutions, byte-identical
python3 tools/selftest.py            # the tools still catch what they should
```

## validate.py

```sh
python3 tools/validate.py <output.jsonl> --data <institution_dir> [--strict] [--json] [--quiet]
```

Checks, per line: the six fields and their types; `verdict` in
`{CLOSE,RFI,ESCALATE}`; `reason_code` in that verdict's list (read from
`system/policy/<inst>.json`, so a policy edit is picked up automatically);
`alert_ids` exactly equal to the case's alerts; every case present exactly once;
every `evidence` ID real for that case (customer doc, alert transaction, or
internal-list entry); `reason` 2-4 sentences and naming at least one concrete
number or ID from the case, with boilerplate rejected.

Warnings (not errors) cover: extra fields, duplicate evidence IDs, an empty
evidence list, an RFI reason that never says what to ask for, and figures that
appear nowhere in the case. The figure check samples the alert `message` and
`measured` blocks, every transaction row of that customer (not only the alerted
ones) and the full text of every evidence document on file, with thousands
separators stripped, so an amount quoted from an invoice or a statement is not
mistaken for a fabricated one. `--strict` turns warnings into errors.

Sentence counting ignores quoted speech and abbreviations, so a reason that
quotes a customer ("yes, that's right. it is the £14,700…") or names
"Sp. z o.o" is not penalised.

## repro.sh

```sh
tools/repro.sh [runs]        # default 5; REPRO_DIR=… KEEP=1 to inspect the runs
```

Snapshots `system/` first (so an edit landing mid-run is not mistaken for
non-determinism), prints the snapshot hash, then runs the snapshot's `run` from
inside the snapshot with absolute paths — as the grader does, and from a
different directory, which also proves the entry point does not depend on cwd.
Every run is `cmp`ed against run 1 and the first differing byte, line and case_id
is printed. Also checks that the line count equals the case count. The scratch
dir defaults to `${TMPDIR:-/tmp}/repro.<pid>`, outside the repo, because a
watcher cleaning the working tree mid-run would otherwise delete the runs;
`REPRO_DIR=…` and `KEEP=1` override.

## report.py

```sh
python3 tools/report.py [--output output] [--data data/institutions] [--json]
                        [--labels tools/case_labels.jsonl] [--inst bank]
```

Prints verdict and reason_code distributions, institution x rule tables, CLOSE
and fallback rates, sentences per reason and words per sentence, the evidence
citation histogram, quality counters (invalid evidence, generic reasons, reasons
with no case fact, RFI without an ask, missing cases), and — with `--labels` —
agreement with the pseudo-labels plus the *risky closes*: cases the labels would
escalate and the pipeline closed.

## labels.json / LABELS.md

One entry per evidence-type combination (134 across the four institutions,
covering 4,000/4,000 cases). Each entry carries the suggested verdict and
reason_code, a one-line ground, the case count, the split by alert rule, the
classifier's per-case tally, a confidence, and a `needs_review` flag with the
question a human has to answer. `LABELS.md` is the readable view and explains how
to read it; the labels are a baseline, not ground truth.

Regenerate after a policy or data change:

```sh
python3 tools/build_labels.py && python3 tools/render_labels_md.py
```
