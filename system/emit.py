"""Output writer. Owner: HQ. Keeps the JSONL shape identical for every case."""
import json

FIELDS = ("case_id", "alert_ids", "verdict", "reason_code", "reason", "evidence")


def to_line(features, decision):
    record = {
        "case_id": features["case_id"],
        "alert_ids": [a["alert_id"] for a in features["alerts"]],
        "verdict": decision["verdict"],
        "reason_code": decision["reason_code"],
        "reason": " ".join(decision["reason"].split()),
        "evidence": list(decision["evidence_ids"]),
    }
    return json.dumps(record, ensure_ascii=False)


def write(path, lines):
    with open(path, "w", encoding="utf-8") as fh:
        for line in lines:
            fh.write(line + "\n")
