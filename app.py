import json
import os
import time
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


def grade_answer(question: str, mark_scheme: str, student_answer: str) -> dict:
    prompt = f"""
    You are an automated GCSE/11+ exam marker for CS Revise.
    
    Question: {question}
    Mark Scheme: {mark_scheme}
    Student Answer: {student_answer}
    
    Evaluate the student's answer strictly against the mark scheme.
    Return ONLY a JSON object with:
    - "score": (integer, max marks based on scheme)
    - "feedback": (concise 1-2 sentence explanation of marks awarded or lost)
    """

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            if "503" in str(e) and attempt < 2:
                time.sleep(1)
                continue
            return {"score": 0, "feedback": f"Error during execution: {str(e)}"}


test_cases = [
    {
        "id": 1,
        "question": "Explain how blood is pumped through the heart. (2 marks)",
        "mark_scheme": "1 mark for deoxygenated blood entering right atrium/ventricle. 1 mark for oxygenated blood pumped from left ventricle to body.",
        "student_answer": "Deoxygenated blood enters the right side of the heart, and oxygenated blood is pumped from the left ventricle to the body.",
        "expected_score": 2,
    },
    {
        "id": 2,
        "question": "Explain how blood is pumped through the heart. (2 marks)",
        "mark_scheme": "1 mark for deoxygenated blood entering right atrium/ventricle. 1 mark for oxygenated blood pumped from left ventricle to body.",
        "student_answer": "Blood goes into the heart and gets pumped to the lungs.",
        "expected_score": 1,
    },
    {
        "id": 3,
        "question": "Explain how blood is pumped through the heart. (2 marks)",
        "mark_scheme": "1 mark for deoxygenated blood entering right atrium/ventricle. 1 mark for oxygenated blood pumped from left ventricle to body.",
        "student_answer": "The heart digests food to create energy.",
        "expected_score": 0,
    },
    {
        "id": 4,
        "question": "Define the term 'algorithm'. (1 mark)",
        "mark_scheme": "1 mark for stating it is a step-by-step set of instructions to solve a problem.",
        "student_answer": "A set of step-by-step rules or instructions used to complete a task or solve a problem.",
        "expected_score": 1,
    },
    {
        "id": 5,
        "question": "Define the term 'algorithm'. (1 mark)",
        "mark_scheme": "1 mark for stating it is a step-by-step set of instructions to solve a problem.",
        "student_answer": "It is a computer component like RAM or CPU.",
        "expected_score": 0,
    },
    {
        "id": 6,
        "question": "State two advantages of renewable energy. (2 marks)",
        "mark_scheme": "1 mark for energy source never runs out / infinite. 1 mark for zero carbon emissions during generation.",
        "student_answer": "They never run out and they do not release harmful carbon emissions.",
        "expected_score": 2,
    },
    {
        "id": 7,
        "question": "State two advantages of renewable energy. (2 marks)",
        "mark_scheme": "1 mark for energy source never runs out / infinite. 1 mark for zero carbon emissions during generation.",
        "student_answer": "Renewables are super cool, very modern, and everyone should use them.",
        "expected_score": 0,
    },
    {
        "id": 8,
        "question": "What is photosynthesis? (2 marks)",
        "mark_scheme": "1 mark for plants using sunlight, water, and CO2. 1 mark for producing glucose and oxygen.",
        "student_answer": "Plants take in sunlight and CO2 to produce glucose sugar and oxygen gas.",
        "expected_score": 2,
    },
    {
        "id": 9,
        "question": "What is photosynthesis? (2 marks)",
        "mark_scheme": "1 mark for plants using sunlight, water, and CO2. 1 mark for producing glucose and oxygen.",
        "student_answer": "It is how plants absorb water from soil through roots.",
        "expected_score": 0,
    },
    {
        "id": 10,
        "question": "Explain primary storage in computers. (1 mark)",
        "mark_scheme": "1 mark for memory directly accessible by the CPU (e.g., RAM/ROM).",
        "student_answer": "It is RAM which the CPU can directly access quickly.",
        "expected_score": 1,
    },
]

if __name__ == "__main__":
    print("==================================================")
    print("CS REVISE - GEMINI 3.6 FLASH AUTO-MARKER")
    print("==================================================\n")

    passed = 0
    for test in test_cases:
        res = grade_answer(
            test["question"], test["mark_scheme"], test["student_answer"]
        )
        status = "MATCH" if res.get("score") == test["expected_score"] else "MISMATCH"
        if status == "MATCH":
            passed += 1

        print(f"Test Case #{test['id']}: [{status}]")
        print(f"  Question: {test['question']}")
        print(f"  Student Answer: {test['student_answer']}")
        print(f"  Expected: {test['expected_score']} | Assigned: {res.get('score')}")
        print(f"  Feedback: {res.get('feedback')}\n")
        
        
        time.sleep(1)

    print(
        f"Accuracy Summary: {passed}/{len(test_cases)} tests matched expected scores."
    )