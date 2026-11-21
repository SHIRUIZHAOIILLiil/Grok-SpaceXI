"""Optional model-assisted field extraction.

The decision is made by `decide.py`, which is a pure deterministic function.
This module only fills gaps in *parsing*: where the document states a fact in
prose that the local parsers cannot read, a model is asked for a verbatim quote
and the quote is then parsed with the same local parser. A quote that does not
occur in the document is thrown away, so the model cannot inject a fact.

Rules this respects (data/README.md):
  * a language model is called only through OpenRouter, key in OPENROUTER_API_KEY
  * a run of 200 cases stays under 30 minutes and about four US dollars, so the
    number of calls and the wall clock are both capped
  * with no key (or with HACKATHON_DISABLE_LLM=1) every function returns None and
    the system behaves exactly as it did without this module
"""
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request

ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
MODEL = os.environ.get("HACKATHON_LLM_MODEL", "openai/gpt-4o-mini")
MAX_CALLS = int(os.environ.get("HACKATHON_LLM_CALLS", "400"))
MAX_SECONDS = float(os.environ.get("HACKATHON_LLM_SECONDS", "120"))
TIMEOUT = 20

_state = {"calls": 0, "spent": 0.0, "started": None, "dead": False}
_cache = {}
_WS = re.compile(r"\s+")


def enabled():
    if _state["dead"]:
        return False
    if os.environ.get("HACKATHON_DISABLE_LLM"):
        return False
    if not os.environ.get("OPENROUTER_API_KEY"):
        return False
    if _state["calls"] >= MAX_CALLS:
        return False
    if _state["started"] is not None and time.monotonic() - _state["started"] > MAX_SECONDS:
        return False
    return True


def stats():
    return {"calls": _state["calls"], "seconds": round(_state["spent"], 2),
            "enabled": enabled()}


def _call(system, user):
    key = os.environ.get("OPENROUTER_API_KEY")
    if not enabled() or not key:
        return None
    started = time.monotonic()
    if _state["started"] is None:
        _state["started"] = started
    _state["calls"] += 1
    body = json.dumps({
        "model": MODEL,
        "temperature": 0,
        "max_tokens": 200,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
    }).encode("utf-8")
    request = urllib.request.Request(ENDPOINT, data=body, headers={
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/SHIRUIZHAOIILLiil/Grok-SpaceXI",
        "X-Title": "casefile-alert-review",
    })
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8"))
        text = payload["choices"][0]["message"]["content"]
    except (urllib.error.URLError, KeyError, IndexError, ValueError, OSError):
        # One failure is enough: stop calling the model for the rest of the run
        # rather than paying the timeout on every case.
        _state["dead"] = True
        return None
    finally:
        _state["spent"] += time.monotonic() - started
    return text


def _norm(text):
    return _WS.sub(" ", text or "").strip()


def _json_from(text):
    if not text:
        return None
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except ValueError:
        return None


def quote_containing(text, question, max_words=24):
    """Ask for a verbatim quote from `text` that answers `question`.

    The quote is returned only when it really occurs in the document, so it can
    be handed to a deterministic parser with no risk of a fabricated value.
    """
    if not enabled() or not text:
        return None
    digest = hashlib.sha256((question + "\x00" + text).encode("utf-8")).hexdigest()
    if digest in _cache:
        return _cache[digest]
    system = ("You read compliance documents. You answer with JSON only, and you "
              "never paraphrase: the value you return must be copied character for "
              "character from the document.")
    user = ("Document:\n---\n%s\n---\n\n%s\n\n"
            "Return {\"quote\": \"...\"} where quote is the shortest verbatim span "
            "(at most %d words) from the document that answers the question, or "
            "{\"quote\": null} if the document does not say. Do not guess."
            % (text[:6000], question, max_words))
    payload = _json_from(_call(system, user))
    answer = (payload or {}).get("quote")
    if not isinstance(answer, str):
        _cache[digest] = None
        return None
    answer = _norm(answer).strip(' "\'')
    if len(answer) < 4 or _norm(answer) not in _norm(text):
        _cache[digest] = None
        return None
    _cache[digest] = answer
    return answer


def date_of_birth(text):
    """Return the ISO date of birth a document states for the person it names."""
    quote = quote_containing(
        text, "What is the date of birth of the person this document is about?",
        max_words=18)
    if not quote:
        return None
    # Only accept a quote that is visibly about a birth date, so a document date
    # the model happened to quote cannot be read as one.
    if not re.search(r"\b(born|date of birth|d\.o\.b|dob)\b", quote, re.I):
        return None
    import evidence  # local import: keeps this module importable on its own
    return evidence.parse_dob(quote) or evidence.parse_dob("born " + quote)
