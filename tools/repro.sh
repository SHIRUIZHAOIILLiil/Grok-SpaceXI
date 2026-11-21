#!/bin/sh
# tools/repro.sh — prove the pipeline is byte-for-byte reproducible.
#
# Usage:
#   tools/repro.sh [runs]        (default 5 runs)
#
# For every institution it runs system/run <runs> times into a scratch dir,
# then compares each run against run 1 byte for byte. On a mismatch it prints
# the first differing byte, line and case_id. Exit code 1 on any difference or
# failed run, 0 when every run of every institution is identical.
#
# The scratch dir is $REPRO_DIR (default: ${TMPDIR:-/tmp}/repro.<pid>, removed on
# exit unless KEEP=1). It sits outside the repo on purpose: a watcher or another
# agent cleaning the working tree mid-run would otherwise delete the runs and
# make the comparison fail for the wrong reason. Runs are invoked from inside
# system/ with absolute paths, exactly as the grader does, so this also proves
# the entry point does not depend on cwd.
set -u

RUNS=${1:-5}
case "$RUNS" in
  ''|*[!0-9]*) echo "usage: tools/repro.sh [runs]" >&2; exit 2 ;;
esac
[ "$RUNS" -ge 2 ] || { echo "repro: need at least 2 runs to compare" >&2; exit 2; }

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
INSTS="bank payments_fx emoney investment"
WORK=${REPRO_DIR:-${TMPDIR:-/tmp}/repro.$$}
KEEP=${KEEP:-0}

rm -rf "$WORK"
mkdir -p "$WORK" || exit 2
if [ "$KEEP" != "1" ]; then
  trap 'rm -rf "$WORK"' EXIT INT TERM
fi

# Snapshot system/ so that an edit landing in the middle of the 20 runs cannot be
# mistaken for non-determinism, and so the reported hash names the code tested.
SNAP="$WORK/system"
cp -Rp "$ROOT/system" "$SNAP" 2>/dev/null || {
  echo "repro: cannot snapshot $ROOT/system" >&2
  exit 2
}
CODE_HASH=$(cat "$SNAP"/*.py "$SNAP"/policy/*.json 2>/dev/null | sha256sum | cut -c1-12)

echo "repro: $RUNS runs x 4 institutions"
echo "repro: root $ROOT"
echo "repro: work $WORK"
echo "repro: system snapshot $CODE_HASH"
echo ""

FAIL=0
START=$(date +%s)

n=1
while [ "$n" -le "$RUNS" ]; do
  mkdir -p "$WORK/run$n"
  for inst in $INSTS; do
    OUT="$WORK/run$n/$inst.jsonl"
    T0=$(date +%s)
    if ( cd "$SNAP" && ./run "$ROOT/data/institutions/$inst" "$OUT" ); then
      :
    else
      echo "FAIL run$n $inst: system/run exited non-zero"
      FAIL=1
    fi
    T1=$(date +%s)
    if [ ! -s "$OUT" ]; then
      echo "FAIL run$n $inst: no output written to $OUT"
      FAIL=1
      continue
    fi
    if [ "$n" = "1" ]; then
      echo "  run1 $inst: $(wc -l < "$OUT" | tr -d ' ') lines, $((T1 - T0))s"
    fi
  done
  n=$((n + 1))
done

echo ""
echo "byte comparison against run1:"
for inst in $INSTS; do
  BASE="$WORK/run1/$inst.jsonl"
  OK=1
  n=2
  while [ "$n" -le "$RUNS" ]; do
    CMP="$WORK/run$n/$inst.jsonl"
    if [ ! -s "$BASE" ] || [ ! -s "$CMP" ]; then
      echo "FAIL $inst: run$n output missing or empty ($CMP)"
      OK=0
      break
    fi
    if ! cmp -s "$BASE" "$CMP"; then
      OK=0
      echo "FAIL $inst: run$n differs from run1"
      python3 - "$BASE" "$CMP" "$n" "$inst" <<'PY'
import json, sys

base_path, cmp_path, run_no, inst = sys.argv[1:5]
with open(base_path, "rb") as fh:
    base = fh.read()
with open(cmp_path, "rb") as fh:
    other = fh.read()

limit = min(len(base), len(other))
offset = next((i for i in range(limit) if base[i] != other[i]), limit)
line_no = base[:offset].count(b"\n") + 1
line_start = base.rfind(b"\n", 0, offset) + 1
line_end = base.find(b"\n", offset)
if line_end < 0:
    line_end = len(base)
fragment = base[line_start:line_end].decode("utf-8", "replace")

try:
    case_id = json.loads(fragment).get("case_id", "?")
except ValueError:
    case_id = "?"
try:
    other_fragment = other[line_start:other.find(b"\n", offset) if other.find(b"\n", offset) >= 0 else len(other)]
    other_fragment = other_fragment.decode("utf-8", "replace")
except Exception:
    other_fragment = ""

print("      first difference: byte %d, line %d, case %s" % (offset, line_no, case_id))
print("      run1 : %s" % fragment[:300])
print("      run%d : %s" % (int(run_no), other_fragment[:300]))
if len(base) != len(other):
    print("      sizes: run1=%d bytes, run%d=%d bytes" % (len(base), int(run_no), len(other)))
PY
    fi
    n=$((n + 1))
  done
  if [ "$OK" = "1" ]; then
    LINES=$(wc -l < "$BASE" | tr -d ' ')
    EXPECT=$(wc -l < "$ROOT/data/institutions/$inst/cases.jsonl" | tr -d ' ')
    if [ "$LINES" != "$EXPECT" ]; then
      echo "FAIL $inst: $LINES output lines for $EXPECT cases"
      OK=0
    else
      printf 'PASS %-12s %s identical runs, %s lines\n' "$inst" "$RUNS" "$LINES"
    fi
  fi
  [ "$OK" = "1" ] || FAIL=1
done

END=$(date +%s)
echo ""
if [ "$FAIL" = "0" ]; then
  echo "REPRO PASS — $RUNS runs x 4 institutions byte-identical in $((END - START))s (system $CODE_HASH)"
else
  echo "REPRO FAIL — see the first difference above"
fi
exit "$FAIL"
