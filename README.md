# CS Revise Auto-Marker v2 — Multimodal (Gemini / free-tier edition)

Upgrade of the Stage 2 prototype: handwriting recognition, diagram
evaluation, AO1/AO2/AO3 long-form breakdown, and MCQ — running on
**Gemini 3.6 Flash** via the free tier of Google AI Studio (no credit card
required), with Pydantic-enforced structured JSON output.

See `DESIGN_NOTE.md` for the architecture write-up.

## Files

- `auto_marker.py` — the grading engine (this is the deliverable module).
  `grade_submission()` takes an optional injected `client`, which decouples
  grading logic from client setup rather than hard-coding it internally.
- `run_demo.py` — runs the three required example cases (handwritten,
  diagram, 8-mark long-form), prints a human-readable report card for each,
  and writes the full set to `grading_report.txt`.
- `test_assets/` — the two submission images `run_demo.py` grades:
  - `handwritten_heart_answer.png` — a real photographed handwritten answer.
  - `even_odd_flowchart.png` — a scanned handwritten student flowchart diagram.

## Setup

1. Get a free API key — no credit card needed:
   - Go to **aistudio.google.com**, sign in with a Google account.
   - Click **Get API key** → **Create API key**.
   - Free-tier limits (subject to change): a daily request cap per model,
     shared per project — plenty for testing this pipeline.

```
pip install -r requirements.txt
export GEMINI_API_KEY="AIza..."          # Windows PowerShell: $env:GEMINI_API_KEY="AIza..."
python run_demo.py                        # real API calls against the 3 example cases
```

`test_assets/` already contains the two images graded above — there's
nothing to generate first.

## Using it in your own code

```python
from auto_marker import GradingRequest, ContentType, RubricComponent, grade_submission

request = GradingRequest(
    question="Define the term 'algorithm'. (1 mark)",
    content_type=ContentType.SHORT_ANSWER,
    max_marks=1,
    mark_scheme="1 mark for stating it is a step-by-step set of instructions to solve a problem.",
    student_answer_text="A set of step-by-step rules used to complete a task.",
)
result = grade_submission(request)
print(result["total_score"], "/", result["max_score"])
print(result["improvement_feedback"])
```

For an image (handwritten answer or diagram), pass `image_path=` instead of
(or alongside) `student_answer_text`. For long-form/diagram questions, pass
`mark_scheme=[RubricComponent(name, max_marks, criteria), ...]` instead of a
flat string.

## Known-good live run

The pipeline has been run end-to-end against the real Gemini 3.6 Flash
API — see `grading_report.txt` for a captured output. That first run
caught a genuine bug in the flowchart image itself (the Yes/No branches
were accidentally swapped), which was corrected at the source — the fixed
image is what's in `test_assets/` now. A good sign the grading is actually
reading the diagram's logic rather than pattern-matching on layout.

## A note on free-tier reliability

Because this runs on Gemini's free tier, you may occasionally see
`[Server busy / 503] Retrying in Ns...` in the output — that's Google's
servers being under high demand, not a bug here; `grade_submission()`'s
built-in retry/backoff handles most of these automatically. Very
occasionally a case can still come back with `HUMAN REVIEW: REQUIRED` and
a warning naming a local network error rather than a 503 — that's a
dropped connection on your end (unstable Wi-Fi, a firewall/antivirus
interrupting the request) rather than a grading failure. Simply re-running
`run_demo.py` resolves it; the current retry logic matches on 503/429-style
errors specifically and doesn't yet retry that class of local network
error, which is a known area for hardening (see `DESIGN_NOTE.md`).
