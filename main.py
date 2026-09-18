"""
Runs the three example cases:
  (a) handwritten short answer
  (b) flowchart diagram evaluation
  (c) 8-mark long-form question

Formats terminal output into clear, human-readable report cards
and exports the entire evaluation to 'grading_report.txt'.
"""

import os
import sys
import time

from auto_marker import (
    ContentType,
    GradingRequest,
    RubricComponent,
    grade_submission,
)

ASSETS = os.path.join(os.path.dirname(__file__), "test_assets")


def format_report_card(title: str, res: dict) -> str:
    """Formats a grade result dictionary into a clean report card string."""
    lines = []
    bar = "=" * 70
    sub_bar = "-" * 70

    lines.append(bar)
    lines.append(f"  {title.upper()}")
    lines.append(bar)

    # Score Banner
    total = res.get("total_score", 0)
    max_m = res.get("max_score", 0)
    percentage = (total / max_m * 100) if max_m else 0
    lines.append(f"FINAL SCORE  : {total} / {max_m}  ({percentage:.1f}%)")
    lines.append(
        f"HUMAN REVIEW : {'REQUIRED [!]' if res.get('_needs_human_review') else 'PASSED [OK]'}"
    )

    if res.get("_validation_warnings"):
        lines.append(
            f"WARNINGS     : {', '.join(res['_validation_warnings'])}"
        )
    lines.append(sub_bar)

    # Transcription / Visual Inspection
    notes = res.get("transcription_or_diagram_notes", "").strip()
    if notes:
        lines.append("TRANSCRIPTION / VISUAL NOTES:")
        for line in notes.split("\n"):
            lines.append(f"  > {line}")
        lines.append(sub_bar)

    # Score Breakdown
    breakdown = res.get("score_breakdown", [])
    if breakdown:
        lines.append("MARK BREAKDOWN:")
        for item in breakdown:
            comp = item.get("component", "Criterion")
            awd = item.get("marks_awarded", 0)
            mx = item.get("max_marks", 0)
            just = item.get("justification", "")
            lines.append(f"  * [{awd}/{mx}] {comp}")
            lines.append(f"          Reason: {just}")
        lines.append(sub_bar)

    # Strengths
    strengths = res.get("strengths", [])
    if strengths:
        lines.append("STRENGTHS:")
        for s in strengths:
            lines.append(f"  + {s}")
        lines.append(sub_bar)

    # Improvement Feedback
    feedback = res.get("improvement_feedback", [])
    if feedback:
        lines.append("AREAS FOR IMPROVEMENT:")
        for f in feedback:
            lines.append(f"  - {f}")

    lines.append(bar)
    lines.append("\n")
    return "\n".join(lines)


def main():
    if not os.environ.get("GEMINI_API_KEY"):
        print(
            "No GEMINI_API_KEY set. Please set it in your environment and re-run."
        )
        sys.exit(1)

    all_reports = []

    # -------------------------------------------------------------
    # (a) Handwritten Short-Answer Question
    # -------------------------------------------------------------
    print("\n[1/3] Grading Handwritten Answer...")
    req_a = GradingRequest(
        question="Explain how blood is pumped through the heart. (2 marks)",
        content_type=ContentType.SHORT_ANSWER,
        max_marks=2,
        mark_scheme=(
            "1 mark for deoxygenated blood entering the right atrium/ventricle. "
            "1 mark for oxygenated blood being pumped from the left ventricle to the body."
        ),
        image_path=os.path.join(ASSETS, "handwritten_heart_answer.png"),
    )
    res_a = grade_submission(req_a)
    report_a = format_report_card(
        "(a) GCSE Biology: Handwritten Heart Question", res_a
    )
    print(report_a)
    all_reports.append(report_a)

    time.sleep(5)  # Free tier delay

    # -------------------------------------------------------------
    # (b) Flowchart Diagram Evaluation
    # -------------------------------------------------------------
    print("[2/3] Evaluating Flowchart Diagram...")
    req_b = GradingRequest(
        question="Draw a flowchart that inputs a number and prints whether it is even or odd. (5 marks)",
        content_type=ContentType.DIAGRAM,
        max_marks=5,
        mark_scheme=[
            RubricComponent(
                "Start terminator present", 1, "A clearly labelled Start symbol."
            ),
            RubricComponent(
                "Input step present",
                1,
                "A step that inputs/reads the number, correctly labelled.",
            ),
            RubricComponent(
                "Decision correctly formed",
                1,
                "A decision diamond testing n % 2 == 0 (or equivalent).",
            ),
            RubricComponent(
                "Both branches correct",
                1,
                "Yes/No branches lead to the correct Even/Odd outputs.",
            ),
            RubricComponent(
                "End terminator present",
                1,
                "A clearly labelled End symbol reached by both branches.",
            ),
        ],
        image_path=os.path.join(ASSETS, "even_odd_flowchart.png"),
    )
    res_b = grade_submission(req_b)
    report_b = format_report_card(
        "(b) Computer Science: Even/Odd Flowchart Diagram", res_b
    )
    print(report_b)
    all_reports.append(report_b)

    time.sleep(5)

    # -------------------------------------------------------------
    # (c) 8-Mark Extended Long-Form Response
    # -------------------------------------------------------------
    print("[3/3] Marking 8-Mark Long-Form Essay...")
    req_c = GradingRequest(
        question=(
            "A school is moving its student record system from paper files to a cloud-based "
            "database. Discuss the impact of this change on data security and data protection "
            "compliance. (8 marks)"
        ),
        content_type=ContentType.LONG_FORM,
        max_marks=8,
        mark_scheme=[
            RubricComponent(
                "AO1: Knowledge",
                3,
                "Accurate knowledge of encryption, access control, backups, GDPR.",
            ),
            RubricComponent(
                "AO2: Application",
                3,
                "Applies concepts specifically to a school moving student records to the cloud.",
            ),
            RubricComponent(
                "AO3: Analysis/Evaluation",
                2,
                "Weighs risks against benefits and reaches a justified conclusion.",
            ),
        ],
        student_answer_text=(
            "Moving to the cloud means the school no longer keeps paper files that could be lost "
            "or read by anyone walking past a filing cabinet. Cloud providers encrypt data in transit "
            "and at rest, mitigating interception risks. The school must enforce role-based access "
            "control so staff only access records relevant to their duties. Under GDPR, the school "
            "remains the data controller and requires a formal data processing agreement with the cloud "
            "host. Misconfiguration risks exist, but automated off-site backups offer superior resilience "
            "against disaster compared to paper storage. Overall, migration is justified provided proper access "
            "controls and encryption management are verified."
        ),
    )
    res_c = grade_submission(req_c)
    report_c = format_report_card(
        "(c) GCSE CS: 8-Mark Cloud Migration Response", res_c
    )
    print(report_c)
    all_reports.append(report_c)

    # -------------------------------------------------------------
    # Write to File
    # -------------------------------------------------------------
    output_filename = "grading_report.txt"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write("CS REVISE — AUTOMATED MULTIMODAL MARKING REPORT\n")
        f.write("Generated via Gemini 3.6 Flash Engine\n\n")
        for r in all_reports:
            f.write(r + "\n")

    print(
        f"[OK] Evaluation finished! Full readable report saved to '{output_filename}'."
    )


if __name__ == "__main__":
    main()