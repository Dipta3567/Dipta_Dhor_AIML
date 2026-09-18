"""
CS Revise — Multimodal Auto-Marking Engine (v2 - Free Tier Edition)
==================================================================
Multimodal assessment pipeline powered by Gemini 3.6 Flash:
  1. Handwritten answer recognition (Vision -> transcription -> marking)
  2. Diagram / sketch evaluation    (Vision -> element checklist -> marking)
  3. Extended long-form answers     (AO1/AO2/AO3 level-based breakdown)
  4. Flexible question types        (Short answer, MCQ, Technical, Essay)
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Union
from google import genai
from google.genai import types
from PIL import Image
from pydantic import BaseModel, Field

MODEL = "gemini-3.5-flash"


def get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    return genai.Client(api_key=api_key)


# ---------------------------------------------------------------------------
# 1. Question / content types & Rubric
# ---------------------------------------------------------------------------


class ContentType(str, Enum):
    SHORT_ANSWER = "short_answer"
    LONG_FORM = "long_form"
    DIAGRAM = "diagram"
    MCQ = "mcq"
    TECHNICAL = "technical"


@dataclass
class RubricComponent:
    name: str
    max_marks: int
    criteria: str


@dataclass
class GradingRequest:
    question: str
    content_type: ContentType
    max_marks: int
    mark_scheme: Union[str, list[RubricComponent]]
    student_answer_text: Optional[str] = None
    image_path: Optional[str] = None
    mcq_options: Optional[dict[str, str]] = None
    mcq_correct_option: Optional[str] = None

    def __post_init__(self):
        if self.image_path is None and self.student_answer_text is None:
            raise ValueError("Provide student_answer_text and/or image_path.")
        if self.content_type == ContentType.DIAGRAM and self.image_path is None:
            raise ValueError("DIAGRAM questions require an image_path.")
        if self.content_type == ContentType.MCQ and not self.mcq_correct_option:
            raise ValueError("MCQ questions require mcq_correct_option.")


# ---------------------------------------------------------------------------
# 2. Structured Output Schema (Pydantic)
# ---------------------------------------------------------------------------


class ScoreComponent(BaseModel):
    component: str = Field(
        description="e.g. 'AO1: Knowledge', 'Required label: CPU', or 'Mark point 1'"
    )
    marks_awarded: int = Field(description="Marks awarded for this component")
    max_marks: int = Field(
        description="Total marks available for this component"
    )
    justification: str = Field(
        description="Evidence from answer/diagram that earned or lost marks"
    )


class GradeOutput(BaseModel):
    transcription_or_diagram_notes: str = Field(
        description="Verbatim transcription of handwriting or visual breakdown of diagram elements."
    )
    total_score: int = Field(description="Sum of marks awarded")
    max_score: int = Field(description="Total marks available")
    score_breakdown: List[ScoreComponent] = Field(
        description="Itemized grading breakdown per rubric component"
    )
    strengths: List[str] = Field(
        description="Specific strengths in the submission"
    )
    improvement_feedback: List[str] = Field(
        description="Actionable next steps to address lost marks"
    )


# ---------------------------------------------------------------------------
# 3. Prompt Construction & Image Processing
# ---------------------------------------------------------------------------

BASE_SYSTEM_PROMPT = """You are an expert AI examination grader and multimodal assessment engine built for CS Revise, marking GCSE/11+ work.

Rules:
1. Handwritten & Diagram Inputs: Transcribe handwriting verbatim or inspect diagram shapes/arrows in transcription_or_diagram_notes. Explicitly flag illegible sections.
2. Mark strictly against criteria. Do not infer points not clearly stated or drawn.
3. Long-form / Component questions: Grade each rubric component independently with granular partial credit.
4. Feedback must be actionable and reference specific criteria."""

CONTENT_TYPE_GUIDANCE = {
    ContentType.SHORT_ANSWER: (
        "Short-answer question (1-3 marks). Evaluate discrete points in the scheme. "
        "Create one score_breakdown entry per mark point."
    ),
    ContentType.LONG_FORM: (
        "Extended long-form question (5-10 marks). Produce exactly one score_breakdown "
        "entry per component (AO1, AO2, AO3), evaluating application and evaluation depth."
    ),
    ContentType.DIAGRAM: (
        "Diagram/flowchart evaluation. Visually check shapes, terminators, labels, and flow directions. "
        "Create one score_breakdown entry per required checklist component."
    ),
    ContentType.MCQ: (
        "Multiple-choice question. Award marks if selection matches correct option; otherwise 0."
    ),
    ContentType.TECHNICAL: (
        "Structured technical response. Check each required technical step or calculation against scheme."
    ),
}


def _format_mark_scheme(request: GradingRequest) -> str:
    if request.content_type == ContentType.MCQ:
        options = "\n".join(
            f"  {k}) {v}" for k, v in (request.mcq_options or {}).items()
        )
        return (
            f"Options:\n{options}\n"
            f"Correct option: {request.mcq_correct_option}\n"
            f"Student selected: {request.student_answer_text}"
        )
    if isinstance(request.mark_scheme, list):
        return "\n".join(
            f"- {c.name} (max {c.max_marks} marks): {c.criteria}"
            for c in request.mark_scheme
        )
    return str(request.mark_scheme)


def _prepare_image(image_path: str) -> Image.Image:
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image not found at path: {image_path}")
    img = Image.open(image_path)
    if img.mode != "RGB":
        img = img.convert("RGB")
    max_dim = 1024
    if max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
    return img


# ---------------------------------------------------------------------------
# 4. Grading Execution with Safeguards & Backoff
# ---------------------------------------------------------------------------


def grade_submission(
    request: GradingRequest, max_retries: int = 5, client: Optional[genai.Client] = None
) -> dict:
    if client is None:
        client = get_client()

    system_instruction = (
        BASE_SYSTEM_PROMPT + "\n" + CONTENT_TYPE_GUIDANCE[request.content_type]
    )

    text_parts = [
        f"Question Type: {request.content_type.value}",
        f"Question: {request.question}",
        f"Max marks: {request.max_marks}",
        f"Mark Scheme / Rubric:\n{_format_mark_scheme(request)}",
    ]
    if request.student_answer_text and request.content_type != ContentType.MCQ:
        text_parts.append(
            f"Student typed answer: {request.student_answer_text}"
        )
    if request.image_path:
        label = (
            "diagram"
            if request.content_type == ContentType.DIAGRAM
            else "handwritten answer"
        )
        text_parts.append(f"(Inspect the attached {label} image directly.)")

    contents = []
    if request.image_path:
        contents.append(_prepare_image(request.image_path))
    contents.append("\n\n".join(text_parts))

    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=GradeOutput,
                    temperature=0.0,
                    ),
                )
            

            if hasattr(response, "parsed") and response.parsed:
                result_dict = response.parsed.model_dump()
            else:
                import json

                result_dict = json.loads(response.text)

            return _validate_and_correct(result_dict)

        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            # Retry on high demand spikes (503) or rate limits (429)
            if (
                "503" in err_str
                or "429" in err_str
                or "unavailable" in err_str
                or "resource_exhausted" in err_str
            ) and attempt < max_retries - 1:
                wait_time = 5 * (2**attempt)
                print(
                    f"    [Server busy / 503] Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})..."
                )
                time.sleep(wait_time)
                continue
            break

    return {
        "transcription_or_diagram_notes": "",
        "total_score": 0,
        "max_score": request.max_marks,
        "score_breakdown": [],
        "strengths": [],
        "improvement_feedback": [],
        "_validation_warnings": [f"grading_failed: {last_error!r}"],
        "_needs_human_review": True,
    }


def _validate_and_correct(result: dict) -> dict:
    warnings = []
    breakdown = result.get("score_breakdown", [])

    if breakdown:
        recomputed_total = sum(int(c.get("marks_awarded", 0)) for c in breakdown)
        recomputed_max = sum(int(c.get("max_marks", 0)) for c in breakdown)

        if recomputed_total != result.get("total_score"):
            warnings.append(
                f"total_score mismatch: model said {result.get('total_score')}, "
                f"components summed to {recomputed_total}. Corrected."
            )
            result["total_score"] = recomputed_total

        if recomputed_max and recomputed_max != result.get("max_score"):
            warnings.append(
                f"max_score mismatch: model said {result.get('max_score')}, "
                f"components summed to {recomputed_max}. Corrected."
            )
            result["max_score"] = recomputed_max

        for c in breakdown:
            if int(c.get("marks_awarded", 0)) > int(c.get("max_marks", 0)):
                warnings.append(
                    f"component '{c.get('component')}' exceeded max_marks; clamped."
                )
                c["marks_awarded"] = c["max_marks"]

    result["_validation_warnings"] = warnings
    result["_needs_human_review"] = bool(warnings) or not breakdown
    return result