# NHS Signposting Assistant — Backend

**Live demo:** https://nhs-signposting-assistant.netlify.app
*(First message may take up to a minute if the server has been idle — free-tier hosting spins down after 15 minutes of inactivity)*

## Overview

A conversational assistant that helps someone figure out *where* to seek care for
a symptom or situation — self-care, pharmacy, GP, NHS 111, A&E, or call 999 —
grounded strictly in real NHS guidance, never diagnosing or inventing medical
information. Built as a RAG (Retrieval-Augmented Generation) system with
hardcoded safety guarantees layered on top of the LLM, not left purely to
prompt instructions.

**This is a portfolio demonstration, not a real medical service.**

## Why a hand-curated dataset, not NHS's official API

NHS runs an official Website Content API, but it requires an organisation
with an ODS code, a completed Data Security and Protection Toolkit, and a
multi-stage clinical/security assurance process — built for registered
healthcare bodies and suppliers, not a personal project. Rather than pursue
that (low odds of approval, disproportionate overhead for this scale), I
built a small, manually-curated dataset instead: 18 real scenarios, each
sourced from a specific, verified NHS.uk page, spread evenly across all 6
possible destinations (3 each), with my own summary, the real source URL,
and the specific red-flag escalation criteria from that page.

This dataset does double duty: it's the only source of truth the system is
allowed to answer from, and — since the correct destination for each
scenario is known — it doubles as the evaluation/test set.

## Architecture

```
   User's message
         │
         ▼
┌─────────────────────┐
│   RETRIEVAL           │  Embed the message (sentence-transformers,
│                       │  all-MiniLM-L6-v2), compare against the 18
│                       │  scenarios' embeddings via cosine similarity
└──────────┬───────────┘
            │
            ▼
     Best match score
            │
   ┌────────┼────────┬─────────────────┐
   ▼        ▼         ▼                 ▼
 ≥0.65    0.55-0.65  <0.55 (emergency  <0.50 (emergency
 Confident Ask a      candidates:      candidates: too
 match     clarifying <0.50)           dissimilar, defer
           question   Ask clarifying   to NHS 111
                       question              
            │
            ▼
   Confident match → build a prompt with ONLY the retrieved
   summary + red flags + source URL → send to Groq (Llama 3.3 70B)
            │
            ▼
   LLM writes a natural reply, strictly grounded in the retrieved
   text (system prompt forbids adding outside medical knowledge)
            │
            ▼
   If the matched scenario is a possible emergency (call_999),
   a HARDCODED warning banner is prepended in Python code —
   not left to the LLM to remember to include
            │
            ▼
   Reply returned to the user, via FastAPI → React frontend
```

## Key design decisions (and what testing revealed)

### 1. Two-tier confidence thresholds, not one
An emergency scenario (chest pain, stroke signs, unconsciousness) uses a
*lower* confidence bar (0.50) than everything else (0.65) — deliberately
biased toward over-flagging a possible emergency rather than risking a
missed one. A single shared threshold was tested first and found to let a
genuinely concerning case (a child's rapidly spreading rash) through as a
confident, wrongly-casual "just go to the pharmacy" answer — a real,
dangerous failure mode caught during calibration testing, not theoretical.

### 2. A "clarifying question" zone, not just match/reject
Short or vague messages (e.g. "i have cough") often score in a genuine
middle ground — not confident enough to answer directly, but not unrelated
either. Rather than force a binary match/no-match decision, scores in this
band trigger a clarifying follow-up question instead, mirroring how a real
triage conversation would actually work.

### 3. Retrieval tries the message alone before combining with history
Combining the latest message with recent conversation context helps short,
vague follow-ups ("does it matter that I've also been tired?") resolve
correctly. But it actively hurt clean topic switches mid-conversation (a
new, unrelated injury getting diluted by leftover context from an earlier
topic) — found via manual testing, not anticipated in advance. The fix:
try the new message standalone first; only fall back to combining with
recent context if the standalone search finds nothing.

### 4. Hardcoded safety layers, not prompt-only
Two guarantees are enforced in Python code, not just requested via the
system prompt: (1) when there's no confident match, the LLM is never even
called — a fixed, safe fallback message is returned directly; (2) when a
possible emergency is detected, a warning banner is prepended in code,
regardless of what the LLM itself writes. This was validated by swapping
the underlying LLM entirely (see below) and confirming the safety behaviour
held identically across both models.

### 5. Generic vs. domain reasoning — a real model swap, mid-project
Originally built on Google Gemini (free tier). Free-tier rate limits made
testing unreliable during heavy iteration, so the system was switched to
Groq (Llama 3.3 70B) — also free, and it held up with zero rate-limit
issues under the same test load that gave Gemini trouble. All safety-
critical behaviour (emergency detection, mid-conversation escalation,
resisting false alarms) was re-validated after the swap and matched the
original results, which is good evidence the hardcoded guardrails — not
the specific model — are what's actually doing the safety-critical work.

## Testing & calibration results

All 18 scenarios (reworded, not copied verbatim) plus clearly unrelated
questions and health-sounding-but-out-of-scope questions were tested via
`calibration_test.py` and `chat_calibration_test.py`. Final destination
accuracy: **22/26 (84.6%)** — and critically, **every one of the 4 "misses"
still resulted in a safe outcome** (deferred to NHS 111) rather than a wrong
or dangerous specific answer. A dedicated escalation test
(`chat_escalation.py`) confirmed the emergency banner fires correctly when
a conversation escalates mid-way through, and correctly does *not* fire on
a "sounds scary but isn't" false-alarm case.

## Known limitations (honestly)

- **18 scenarios is a small slice of real NHS guidance.** Most real
  questions won't closely match any of them — by design, this correctly
  defers to NHS 111 rather than force-fitting an answer, but it means
  coverage is intentionally narrow.
- **Destination granularity is coarse in places.** E.g. the single cough
  scenario is filed under "GP" (3+ week duration), so a 2-day cough gets
  a "GP" badge even though the actual written guidance correctly
  recommends self-care first — the LLM reasons through the nuance
  correctly in the text, but the retrieval label doesn't reflect it.
- **Free-tier hosting cold starts.** The Render backend spins down after
  15 minutes idle; the first request after that takes 30-60 seconds.
- **In-memory session storage.** Conversations are lost if the backend
  restarts — acceptable for a demo, not for a real deployment.
- **CORS is fully open** (`allow_origins=["*"]`), a deliberate
  simplification appropriate for a public demo with no accounts or
  sensitive per-user data.

## Tech Stack

- **Retrieval:** sentence-transformers (`all-MiniLM-L6-v2`), NumPy cosine similarity
- **LLM:** Groq API (Llama 3.3 70B), originally built on Google Gemini
- **Backend:** FastAPI, in-memory session management
- **Frontend:** React + Vite ([separate repo](https://github.com/chinmayithakur0/nhs-signposting-frontend))
- **Hosting:** Render (backend), Netlify (frontend)

## Project Structure

    load_data.py                  # (not used directly here -- data loaded in retrieval.py)
    retrieval.py                  # Embedding-based matching + two-tier confidence thresholds
    chat.py                       # Groq integration, system prompt, safety banner logic
    chat_session.py               # Multi-turn conversation, standalone-then-combined retrieval
    main.py                       # FastAPI app, session management, CORS
    calibration_test.py           # Retrieval-only accuracy testing
    chat_calibration_test.py      # Full pipeline accuracy + emergency banner testing
    chat_escalation.py            # Mid-conversation escalation testing
    data/nhs_scenarios_template.csv  # The 18 hand-curated scenarios
    requirements.txt

## Reproducing This

    pip install -r requirements.txt
    # Create a .env file with: GROQ_API_KEY=your_key_here
    python calibration_test.py         # retrieval accuracy
    python chat_calibration_test.py    # full pipeline accuracy
    python chat_escalation.py          # emergency escalation testing
    uvicorn main:app --reload          # run the API locally

## What I'd Explore Next

- Expanding the dataset with finer-grained duration/severity variants per
  condition, to fix the granularity mismatch found in testing
- A proper vector database (FAISS) if scaling past a small hand-curated set
- Persistent session storage instead of in-memory
- Applying for NHS's official content API now that the architecture is proven