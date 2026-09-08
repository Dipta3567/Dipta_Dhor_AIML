Install dependencies:

    pip install -r requirements.txt


Export Gemini API key and run the prototype:

    export GEMINI_API_KEY="api_key_here"
    python app.py


1. Research & Comparison of Auto-Marking Approaches: 

        Keyword / Regex Matching: Fast and zero-cost, but fails on synonyms, rephrasing, or spelling mistakes common in 11+ students.

        Embedding Similarity (SBERT): Captures semantic context well, but struggles to map multi-part rubrics to precise partial credit.

        LLM-Based Grading (Gemini 3.6 Flash): Evaluates responses directly against natural language rubrics, awards partial credit accurately, and generates actionable feedback.

2. Test Results & Evaluation:

        Tested against 10 synthetic GCSE/11+ short-answer test cases.

        High alignment between expected ground-truth scores and assigned model scores.

        Limitations: Strict LLM scoring may occasionally penalize valid responses if subtle details in the mark scheme are omitted.

3. Integration Architecture: 
    
        [Student UI (React/Next.js)] ──► [API Gateway / Cloud Function] ──► [PostgreSQL DB (Fetch Rubric)]
                                                      │
                                                      ▼
                                            [Gemini 3.6 Flash API]
                                                      │
        [Display Feedback & Mark] ◄───────────────────┘

4. Risks & Human Safeguards: 
    Risks: 
    
        Potential hallucination, misinterpreting child typos, or grade inflation.

    Safeguards:

        Confidence Flagging: Route low-confidence evaluations to human markers.

        One-Click Re-Marking: Allow students or parents to request a manual review.

        Random Audit Sampling: Send 5% of auto-marked answers to human staff to maintain model accuracy tracking.
