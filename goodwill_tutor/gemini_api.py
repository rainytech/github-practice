"""
GOODWILL TUITION CENTRE — Gemini API Layer
==========================================
All network traffic lives here. No Tkinter, no HTML.

Key differences from the old version:
  - the key travels in the x-goog-api-key HEADER, never in the URL
  - the model list is fetched live, so model IDs can never go stale
  - PDF input supported, inline for small files and via the Files API for large ones
  - maxOutputTokens raised, temperature dropped to 0 for arithmetic stability
  - a stop Event replaces the global flag, so it is safe on a worker thread
"""

import json
import mimetypes
import os
from datetime import date as _date

import requests

BASE = "https://generativelanguage.googleapis.com/v1beta"
UPLOAD_BASE = "https://generativelanguage.googleapis.com/upload/v1beta"

# Files at or above this size go through the Files API instead of inline base64.
INLINE_LIMIT_BYTES = 15 * 1024 * 1024

# Generation defaults. Temperature 0 — accounting arithmetic must not vary.
DEFAULT_TEMPERATURE = 0.0
DEFAULT_MAX_TOKENS = 32768

SUPPORTED_EXTS = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".heif": "image/heif",
    ".txt": "text/plain",
}

# ── Prices ───────────────────────────────────────────────────────────
# USD per 1M tokens, list price on the paid tier, checked September 2026.
# Google's own pricing page was unreachable from the machine this was written
# on, so these came from published secondary sources; spot-check them against
# a real bill before trusting the rupee figure to the paisa.
#
# ORDER MATTERS. The first pattern that appears in the model id wins, so
# "flash-lite" is listed before "flash" — matching on the longest substring
# instead would price gemini-3.5-flash-lite as a 3.5 Flash, which is six times
# too much.
#
# Each row is (pattern, introductory_rate, standard_rate). The Flash line runs
# at an introductory rate to 31 December 2026 and doubles on 1 January 2027;
# where standard_rate is None the price does not change.
INTRO_ENDS = _date(2027, 1, 1)

PRICING = [
    ("flash-lite",       (0.25, 1.50),   None),
    ("gemini-3.8-flash", (0.75, 3.75),   (1.50, 7.50)),
    ("gemini-3.7-flash", (0.75, 3.75),   (1.50, 7.50)),
    ("gemini-3.6-flash", (0.75, 3.75),   (1.50, 7.50)),
    ("gemini-3.5-flash", (1.50, 9.00),   None),
    ("gemini-3.1-pro",   (2.00, 12.00),  None),
    ("pro",              (2.00, 12.00),  None),
    ("flash",            (0.75, 3.75),   (1.50, 7.50)),
]

# Google serves the Gemma models on the Gemini API at no charge — there is no
# paid line for them, only rate limits. Priced at zero so the meter says "free"
# instead of "cost n/a", which reads like a fault.
FREE_MODELS = ("gemma",)

# A prompt over this size re-rates the WHOLE request on the Pro line.
LARGE_PROMPT_TOKENS = 200_000
LARGE_PROMPT_PRICING = [
    ("pro", (4.00, 18.00)),
]

PRICING_VERIFIED = True
USD_TO_INR = 88.0


class GeminiError(RuntimeError):
    """An API or configuration failure, with a message fit for the status bar."""


# ═══════════════════════════════════════════════════════════════
#  KEY
# ═══════════════════════════════════════════════════════════════

def get_api_key():
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise GeminiError(
            "GEMINI_API_KEY is not set.\n\n"
            "Windows:  setx GEMINI_API_KEY \"your-key-here\"  then reopen the terminal.\n"
            "Linux/Mac:  export GEMINI_API_KEY=\"your-key-here\""
        )
    return key


def _headers():
    return {
        "Content-Type": "application/json",
        "x-goog-api-key": get_api_key(),
    }


# ═══════════════════════════════════════════════════════════════
#  MODELS — fetched live, never hard-coded
# ═══════════════════════════════════════════════════════════════

# Models that cannot solve an accounting question in this app.
# They stay in the dropdown but sort to the bottom and are never auto-selected.
SPECIALIST_MARKERS = (
    "deep-research", "antigravity", "robotics", "computer-use",
    "nano-banana", "gemma", "imagen", "veo", "lyria",
    "-tts", "-image", "transcribe", "guard", "learnlm",
)


def is_general_model(model_id):
    """True for an ordinary Gemini chat model — the kind that solves problems."""
    mid = model_id.lower()
    if not mid.startswith("gemini"):
        return False
    return not any(marker in mid for marker in SPECIALIST_MARKERS)


def _rank(model_id):
    """Sort key: ordinary chat models first, newest first, Pro before Flash."""
    mid = model_id.lower()
    group = 0 if is_general_model(mid) else 1

    # Tier first, then newest within the tier: every Pro is listed before any
    # Flash. Sorting by version first would push Flash above Pro, because the
    # Flash line carries higher numbers than the Pro line.
    if "flash-lite" in mid:
        tier = 3
    elif "flash" in mid:
        tier = 2
    elif "pro" in mid:
        tier = 1
    else:
        tier = 4

    # A '-latest' alias can change model under you without warning, which is
    # wrong for arithmetic that must be reproducible. It sorts last in its
    # tier and is never auto-selected, but stays available.
    if "latest" in mid:
        version = -1.0
    else:
        version = 0.0
        for token in mid.replace("-", " ").split():
            try:
                version = max(version, float(token))
            except ValueError:
                continue

    preview = 1 if ("preview" in mid or "exp" in mid) else 0
    return (group, tier, -version, preview, mid)


def list_models(timeout=30):
    """Return [(model_id, display_name)] for models that can generate content.

    Live from the API, so the dropdown is always current.
    """
    try:
        res = requests.get(f"{BASE}/models", headers=_headers(), timeout=timeout)
    except requests.RequestException as exc:
        raise GeminiError(f"Could not reach the Gemini API: {exc}")

    if res.status_code != 200:
        raise GeminiError(f"Model list failed [{res.status_code}]: {res.text[:300]}")

    out = []
    for m in res.json().get("models", []):
        if "generateContent" not in m.get("supportedGenerationMethods", []):
            continue
        mid = m.get("name", "").replace("models/", "")
        if not mid or "embedding" in mid or "aqa" in mid:
            continue
        out.append((mid, m.get("displayName", mid)))

    out.sort(key=lambda t: _rank(t[0]))
    return out


def price_for(model_id, in_tok=0, on=None):
    """(input_usd_per_1M, output_usd_per_1M), or None when the model is unknown.

    in_tok decides the large-prompt tier; `on` is the date to price for, so the
    introductory rates can be tested either side of their expiry.
    """
    mid = model_id.lower()
    today = on or _date.today()

    if any(marker in mid for marker in FREE_MODELS):
        return (0.0, 0.0)

    if in_tok > LARGE_PROMPT_TOKENS:
        for pattern, rates in LARGE_PROMPT_PRICING:
            if pattern in mid:
                return rates

    for pattern, intro, standard in PRICING:
        if pattern in mid:
            if standard is not None and today >= INTRO_ENDS:
                return standard
            return intro
    return None


CACHED_INPUT_DISCOUNT = 0.10      # cached prompt tokens bill at a tenth


def cost_inr(model_id, in_tok, out_tok, cached_tok=0, on=None):
    """Rupee cost of one call, or None when the model's rate is unknown.

    cached_tok is the part of in_tok that Gemini served from its cache; it is
    included in in_tok by the API and bills at a tenth of the input rate.
    """
    prices = price_for(model_id, in_tok, on)
    if prices is None:
        return None
    cached = max(0, min(cached_tok, in_tok))
    fresh = in_tok - cached
    usd = (
        (fresh / 1_000_000) * prices[0]
        + (cached / 1_000_000) * prices[0] * CACHED_INPUT_DISCOUNT
        + (out_tok / 1_000_000) * prices[1]
    )
    return usd * USD_TO_INR


def format_inr(value):
    """Render a rupee amount, flagged as an estimate while the rates are unverified."""
    if value is None:
        return "cost n/a"
    prefix = "~" if PRICING_VERIFIED else "est. "
    if value <= 0:
        return "free"
    if value < 1:
        return f"{prefix}{value * 100:.0f} paise"
    return f"{prefix}Rs. {value:.2f}"


def format_cost(model_id, in_tok, out_tok, cached_tok=0):
    """Human-readable cost of a single call."""
    return format_inr(cost_inr(model_id, in_tok, out_tok, cached_tok))


# ═══════════════════════════════════════════════════════════════
#  ATTACHMENTS — PDF and images
# ═══════════════════════════════════════════════════════════════

def mime_for(path):
    """The media type Gemini should be told, or an error naming what is accepted."""
    ext = os.path.splitext(path)[1].lower()
    if ext in SUPPORTED_EXTS:
        return SUPPORTED_EXTS[ext]
    guess = mimetypes.guess_type(path)[0] or ""
    if guess.startswith("image/") or guess in ("application/pdf", "text/plain"):
        return guess
    raise GeminiError(
        f"'{os.path.basename(path)}' cannot be sent to Gemini.\n"
        "Attach a PDF, an image (JPG, PNG, WEBP, HEIC) or a text file."
    )


def _upload_file(path, timeout=300):
    """Resumable upload to the Files API. Returns the file URI."""
    mime = mime_for(path)
    size = os.path.getsize(path)
    key = get_api_key()

    start = requests.post(
        f"{UPLOAD_BASE}/files",
        headers={
            "x-goog-api-key": key,
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(size),
            "X-Goog-Upload-Header-Content-Type": mime,
            "Content-Type": "application/json",
        },
        data=json.dumps({"file": {"display_name": os.path.basename(path)}}),
        timeout=timeout,
    )
    if start.status_code != 200:
        raise GeminiError(f"Upload start failed [{start.status_code}]: {start.text[:300]}")

    upload_url = start.headers.get("X-Goog-Upload-URL")
    if not upload_url:
        raise GeminiError("Upload start returned no upload URL.")

    with open(path, "rb") as fh:
        done = requests.post(
            upload_url,
            headers={
                "Content-Length": str(size),
                "X-Goog-Upload-Offset": "0",
                "X-Goog-Upload-Command": "upload, finalize",
            },
            data=fh,
            timeout=timeout,
        )
    if done.status_code != 200:
        raise GeminiError(f"Upload failed [{done.status_code}]: {done.text[:300]}")

    uri = done.json().get("file", {}).get("uri")
    if not uri:
        raise GeminiError("Upload finished but returned no file URI.")
    return uri, mime


def build_parts(text, file_paths=None):
    """Build the 'parts' array for one user turn: the text plus any attachments."""
    parts = [{"text": text}] if text else []
    for path in (file_paths or []):
        if not os.path.exists(path):
            raise GeminiError(f"Attached file is missing: {path}")
        if os.path.getsize(path) >= INLINE_LIMIT_BYTES:
            uri, mime = _upload_file(path)
            parts.append({"file_data": {"mime_type": mime, "file_uri": uri}})
        else:
            import base64
            with open(path, "rb") as fh:
                data = base64.standard_b64encode(fh.read()).decode("utf-8")
            parts.append({"inline_data": {"mime_type": mime_for(path), "data": data}})
    return parts


# ═══════════════════════════════════════════════════════════════
#  GENERATION
# ═══════════════════════════════════════════════════════════════

def _body(contents, system_prompt, max_tokens, temperature, thinking_budget):
    cfg = {
        "temperature": temperature,
        "maxOutputTokens": max_tokens,
    }
    if thinking_budget is not None:
        cfg["thinkingConfig"] = {"thinkingBudget": int(thinking_budget)}
    payload = {"contents": contents, "generationConfig": cfg}
    if system_prompt:
        payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
    return payload


def _is_thinking_complaint(text):
    return "thinking" in text.lower() and ("unknown" in text.lower() or "invalid" in text.lower())


def stream_generate(
    contents,
    model_id,
    system_prompt="",
    on_chunk=None,
    stop_event=None,
    max_tokens=DEFAULT_MAX_TOKENS,
    temperature=DEFAULT_TEMPERATURE,
    thinking_budget=None,
    timeout=600,
):
    """Stream a response. Calls on_chunk(text) as pieces arrive.

    Returns (full_text, input_tokens, output_tokens).
    Raises GeminiError on failure so the caller can show one clear message.
    """
    url = f"{BASE}/models/{model_id}:streamGenerateContent?alt=sse"
    payload = _body(contents, system_prompt, max_tokens, temperature, thinking_budget)

    full, in_tok, out_tok, cached_tok = "", 0, 0, 0
    finish_reason = None

    try:
        with requests.post(
            url, headers=_headers(), data=json.dumps(payload), stream=True, timeout=timeout
        ) as res:
            if res.status_code != 200:
                detail = res.text[:500]
                # The thinking field is not accepted by every model — retry without it.
                if thinking_budget is not None and _is_thinking_complaint(detail):
                    return stream_generate(
                        contents, model_id, system_prompt, on_chunk, stop_event,
                        max_tokens, temperature, None, timeout,
                    )
                raise GeminiError(f"Gemini returned {res.status_code}: {detail}")

            for line in res.iter_lines():
                if stop_event is not None and stop_event.is_set():
                    break
                if not line:
                    continue
                text = line.decode("utf-8", errors="replace")
                if text.startswith("data: "):
                    text = text[6:]
                if text.strip() in ("", "[DONE]"):
                    continue
                try:
                    chunk = json.loads(text)
                except json.JSONDecodeError:
                    continue

                for cand in chunk.get("candidates", []):
                    finish_reason = cand.get("finishReason") or finish_reason
                    for part in cand.get("content", {}).get("parts", []):
                        piece = part.get("text")
                        if piece:
                            full += piece
                            if on_chunk:
                                on_chunk(piece)
                usage = chunk.get("usageMetadata")
                if usage:
                    in_tok = usage.get("promptTokenCount", in_tok)
                    out_tok = usage.get("candidatesTokenCount", out_tok)
                    cached_tok = usage.get("cachedContentTokenCount", cached_tok)

    except GeminiError:
        raise
    except requests.RequestException as exc:
        raise GeminiError(f"Network error: {exc}")

    if finish_reason == "MAX_TOKENS":
        raise GeminiError(
            "The answer hit the output limit and is incomplete. "
            "Raise Max output tokens in Settings, or split the question."
        )
    if finish_reason in ("SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT"):
        raise GeminiError(f"Gemini stopped the response early (reason: {finish_reason}).")
    if not full.strip() and not (stop_event and stop_event.is_set()):
        raise GeminiError("Gemini returned an empty response.")

    return full, in_tok, out_tok, cached_tok


def generate(
    contents,
    model_id,
    system_prompt="",
    max_tokens=DEFAULT_MAX_TOKENS,
    temperature=DEFAULT_TEMPERATURE,
    thinking_budget=None,
    timeout=600,
):
    """Single non-streaming call. Used for the verification pass."""
    url = f"{BASE}/models/{model_id}:generateContent"
    payload = _body(contents, system_prompt, max_tokens, temperature, thinking_budget)

    try:
        res = requests.post(url, headers=_headers(), data=json.dumps(payload), timeout=timeout)
    except requests.RequestException as exc:
        raise GeminiError(f"Network error: {exc}")

    if res.status_code != 200:
        detail = res.text[:500]
        if thinking_budget is not None and _is_thinking_complaint(detail):
            return generate(contents, model_id, system_prompt, max_tokens, temperature, None, timeout)
        raise GeminiError(f"Gemini returned {res.status_code}: {detail}")

    data = res.json()
    usage = data.get("usageMetadata", {})
    for cand in data.get("candidates", []):
        parts = cand.get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts)
        if text:
            return (
                text,
                usage.get("promptTokenCount", 0),
                usage.get("candidatesTokenCount", 0),
                usage.get("cachedContentTokenCount", 0),
            )
    raise GeminiError("Gemini returned no usable content.")


# ═══════════════════════════════════════════════════════════════
#  OUTPUT CLEANUP
# ═══════════════════════════════════════════════════════════════

def strip_code_fence(text):
    """Remove a ```html ... ``` wrapper if the model added one despite instructions."""
    t = text.strip()
    if t.startswith("```"):
        first = t.find("\n")
        if first != -1:
            t = t[first + 1:]
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()
