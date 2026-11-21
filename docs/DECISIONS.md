# Decisions, and the evidence behind them

Each entry: the decision, why, and what would change our mind.

## 1. The verdict is a deterministic function, not a model call

**Decision.** No language model participates in choosing a verdict or a reason code.

**Why.** Reproducibility is 20% of the score and the grader runs the system five times. A model in
the decision path makes a verdict depend on a third-party API being reachable and identical on all
five runs. It also spends from a $4 per 200-case budget and a 30-minute cap for no measured gain: on
this dataset the evidence is templated (785 bank contact notes collapse to 6 sentence templates), and
rules read templates more reliably than a sampler does.

**What we measured.** With the optional re-read enabled, the model promoted **0 of 236** fallback
cases across all 4,000 development cases. It is off by default for that reason.

**What would change it.** Evidence that a model closes cases the rules cannot, at a precision above
the cost break-even (a wrong close costs 10, a needless escalation 3).

## 2. Suspicion checks run before close grounds

**Decision.** Eight red-flag checks are evaluated first; a hit returns immediately and no close
ground is consulted.

**Why.** Some cases carry both a plausible invoice and a fraud report from the sending bank. Ordering
close grounds first lets a fabricated document close a mule account. The policy is explicit: once
there is suspicion you escalate, and you do not ask the customer, because asking can tip them off.

## 3. A close needs the money to reconcile

**Decision.** A close ground must find a document whose amount sits inside 72%–112% of what the alert
measured, and that ground must cover **every** rule that fired in the case.

**Why.** The band absorbs partial payments, VAT and fees (the median measured ratio is 1.000 and the
25th percentile 0.884), while refusing documents that merely look related. Requiring full coverage
prevents the commonest way to lose 10 points on a multi-alert case: explaining one alert and closing.

## 4. When nothing settles it, escalate — or ask, if one document would settle it

**Decision.** Fallback is RFI only when the case is otherwise unremarkable and one named document
would decide it; otherwise a specific escalation code; otherwise `ESC_UNEXPLAINED_FUNDS`.

**Why.** The cost matrix: a wrong close costs 10, a needless escalation 3, an RFI on a case that
should escalate 3. The asymmetry says never guess a close, and prefer escalation once "is this a
crime?" is more than ~40% likely.

## 5. No database in the pipeline

**Decision.** The store is the folder: JSONL plus Markdown, read once, decided in memory, written as
an append-only decision log. A database appears only downstream, in `tools/audit.py` and
`tools/neon_sync.py`.

**Why.** The contract says the system reads only the folder it is given and writes only its output
file. State between runs is also a source of nondeterminism, and the grader's machine has no database.

## 6. The model, where it is allowed

**Decision.** A model may only return a **verbatim quote** from a document already in the case. The
quote is checked against the text, must carry a birth cue, and is then parsed by the same local
parser.

**Why.** 46 of 140 gift letters state the giver's date of birth in a sentence rather than a field.
That is a parsing gap, not a judgement call, and a quote that is verified character for character
cannot fabricate a fact. Anything the model says that fails the check changes nothing.

## 7. Template fingerprints, not keyword lists

**Decision.** Documents are fingerprinted after amounts, dates, numbers and names are replaced by
placeholders, and the fingerprint maps to a semantic tag.

**Why.** The corpus is generated from a small set of sentence templates (632 families across 16,402
documents). A fingerprint generalises to unseen cases from the same generator, while a list of
keywords would drift. Unknown fingerprints fall through to escalation rather than being guessed.

## 8. Engineering parameters are labelled as ours

**Decision.** Anything not written in `POLICY.md` — the 72%–112% band, the 3.05× and £10,000 limits
inside `WITHIN_PROFILE`, the phrase lists behind the red-flag checks — is treated as an engineering
choice and documented as such.

**Why.** An auditor needs to know which numbers came from the institution and which came from us.
`system/policy/*.json` carries the `POLICY.md` sentence for every institutional threshold.
