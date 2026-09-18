# CS Revise Auto-Marker v2 — Design Note & Safeguards

## 0. Why Gemini instead of a paid API

The first draft of this pipeline targeted the Anthropic API (Claude Sonnet
5) with tool-forced JSON output. Anthropic's API has no free tier — it's
prepaid, credit-card only, no way around it. Rather than block on that,
this version runs on **Gemini 3.6 Flash** through Google AI Studio's free
tier, which needs only a Google account (no card). The core design —
request validation, componentised rubrics, structured output, local
arithmetic safeguards — carries over unchanged; only the API call and the
structured-output mechanism (Pydantic + `response_schema` instead of a
forced tool call) are different. If a paid key becomes available later, the
same `GradingRequest`/`ContentType`/`RubricComponent` interface could sit in
front of either provider.

## 1. System Architecture

The auto-marking engine processes typed responses and image-based submissions (handwriting and technical diagrams) through a single multimodal pipeline:

1. **Input Normalisation (`GradingRequest`)**: Validates that required assets (e.g., diagram image paths, multiple-choice keys) are present before dispatching requests.
2. **Integrated Multimodal Vision**: Eliminates decoupled OCR dependencies by passing handwritten sheets and flowchart sketches directly to Gemini 3.6 Flash's vision context.
3. **Structured Response Schema**: Uses Pydantic data modeling (`GradeOutput`) via Gemini's native structured JSON engine (`response_schema`), guaranteeing key consistency without prompt-based regex parsing.
4. **Local Safeguard Validation**: Automatically verifies mathematical consistency across component marks (`marks_awarded`) and flags discrepancies for human escalation.

## 2. Approach Comparison (GCSE / 11+ Context)

| Approach | Advantages | Disadvantages | Suitability for CS Revise |
| :--- | :--- | :--- | :--- |
| **Keyword / N-gram Matching** | Deterministic, sub-millisecond execution, zero inference cost. | Fails on synonyms, penalizes non-standard phrasing, cannot parse diagrams. | Poor for open-ended assessment; suitable only for single-word blanks. |
| **Embedding Similarity (Cosine)** | Captures semantic equivalence across paraphrased student explanations. | Cannot enforce discrete mark-scheme checklist items; blind to diagrams. | Moderate for definition questions; inadequate for partial credit breakdowns. |
| **Multimodal LLM (`gemini-3.6-flash`)** | Natively grades handwriting, diagrams, and multi-tier rubrics (AO1–AO3); free tier removes cost as a barrier to iterating. | Sensitive to rate limits on the free tier; requires defensive schemas and arithmetic guards. | **Selected**: Handles diverse GCSE submission types within one unified API at zero API cost while prototyping. |

## 3. Human-Review Safeguards & Edge Cases

* **Arithmetic Clamping**: The local engine recalculates the sum of `score_breakdown`. If `total_score` deviates from component sums, it corrects the value and sets `_needs_human_review = True`.
* **Illegibility Flagging**: Prompts instruct the model to mark illegible or ambiguous visual elements explicitly in `transcription_or_diagram_notes` rather than guessing student intent.
* **Transient Failure Fallback**: Implements exponential backoff over retryable codes (429/503, and Gemini's `RESOURCE_EXHAUSTED`/"unavailable" errors — the free tier's own rate limits are a real, expected source of these). If requests fail, the engine outputs zero marks and assigns the submission to manual human review.
* **Free-tier rate limits as an operational constraint, not just a dev inconvenience**: `run_demo.py` sleeps between calls to stay under the free tier's per-minute cap. In a real deployment this means either staying on the free tier with a request queue/throttle in front of it, or moving to a paid tier once volume grows past what's practical during marking-rush periods (e.g. exam season) — worth flagging to CS Revise as a scaling decision, not just a technical detail.
* **Known gap, found in live testing**: the retry logic matches on error-message substrings (`"503"`, `"429"`, `"unavailable"`, `"resource_exhausted"`), not typed exception classes. During testing, a local network interruption (a dropped connection, surfaced as a `ReadError`) fell outside that matching and wasn't retried — it went straight to the zero-score/human-review fallback instead of being retried like a 503 would be. The fail-safe behaviour is still correct (it never returned a fabricated score), but the retry coverage itself is narrower than it should be; broadening it to catch generic connection/timeout errors, not just the specific strings above, is the next hardening step.

## 4. Validation note

This pipeline has been run against the real Gemini API for all three
required example cases — see `grading_report.txt` for the captured output.
That live run caught a genuine labelling bug in the diagram test asset
itself (the flowchart's Yes/No branches were accidentally swapped when it
was first generated), which the model correctly flagged and marked down
for. That's the kind of outcome you want from a first live test: evidence
the model is actually reading the diagram's structure rather than just
checking which shapes are present. The bug was corrected at the source, and
the corrected image is what's included in `test_assets/` now.

The handwriting sample was subsequently upgraded from a computer-rendered
stand-in to a real photographed handwritten answer, to test against
something closer to an actual student submission — narrowing one of the
two "synthetic test data" limitations noted below.

## 5. Known limitations

* **Expanded edge-case testing for handwriting**: Real student handwriting and hand-drawn diagrams are fully supported and ingested directly via the vision context, though continued benchmark testing against high-variance edge cases (e.g., severe camera glare, skew, low ink contrast, or heavily crossed-out steps) remains ongoing.
* **No automated test suite in this submission.** Validation here is
  through live runs against the real API and manual inspection of
  `grading_report.txt`, not an offline unit-test layer.
* **Retry coverage gap** — see the "known gap" bullet in Section 3.
* **Single-provider dependency**: everything runs on Gemini; no fallback
  provider if Google AI Studio has an outage or changes free-tier terms.