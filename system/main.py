"""Load one institution folder, decide every case, write one JSONL file."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import decide      # noqa: E402
import emit        # noqa: E402
import evidence   # noqa: E402
import features   # noqa: E402


def read_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_policy(institution):
    path = os.path.join(HERE, "policy", institution + ".json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main(argv):
    if len(argv) != 3:
        sys.stderr.write("usage: system/run <institution_dir> <output_file>\n")
        return 2
    institution_dir = os.path.abspath(argv[1])
    out_path = os.path.abspath(argv[2])
    institution = os.path.basename(institution_dir.rstrip(os.sep))

    index = evidence.Index(institution_dir)
    policy = load_policy(institution)
    alerts_by_case = {}
    for row in read_jsonl(os.path.join(institution_dir, "alerts.jsonl")):
        alerts_by_case.setdefault(row["case_id"], []).append(row)

    cases = read_jsonl(os.path.join(institution_dir, "cases.jsonl"))
    cases.sort(key=lambda c: c["case_id"])  # deterministic order

    lines = []
    for case in cases:
        case = dict(case)
        case["alerts"] = alerts_by_case.get(case["case_id"], [])
        built = features.build_case(institution_dir, case, index)
        decision = decide.decide(built, policy)
        lines.append(emit.to_line(built, decision))

    parent = os.path.dirname(out_path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    emit.write(out_path, lines)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
