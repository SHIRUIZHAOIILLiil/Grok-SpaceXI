"""Decision table. Owner: A.

Pure function: no disk reads, no randomness, no wall clock.
Signature frozen in CONTRACT.md.

BASELINE (HQ placeholder): every case escalates. This proves the pipeline and
scores 0 on verdicts by construction — replace rule by rule, starting with the
CLOSE paths you can prove from POLICY.md.
"""

FALLBACK = ("ESCALATE", "ESC_UNEXPLAINED_FUNDS")


def _money(value):
    try:
        return "£{:,.2f}".format(float(value))
    except (TypeError, ValueError):
        return "£0.00"


def decide(features, policy):
    rules = ", ".join(features["rules"]) or "no rule id"
    messages = [a.get("message", "").strip() for a in features["alerts"]]
    lead = messages[0] if messages else "The alert has no description."
    evidence_ids = []
    for alert in features["alerts"]:
        evidence_ids.extend(alert.get("transaction_ids", []))
    evidence_ids = sorted(dict.fromkeys(evidence_ids))[:8]

    verdict, code = FALLBACK
    reason = (
        "Case raised {n} alert(s) under {rules}: {lead} "
        "No document on file explains all of the activity the alerts raised, "
        "so the case goes to the MLRO for a reporting decision."
    ).format(n=len(features["alerts"]), rules=rules,
             lead=lead.rstrip(".") + ".")
    return {
        "verdict": verdict,
        "reason_code": code,
        "evidence_ids": evidence_ids,
        "reason": reason,
    }
