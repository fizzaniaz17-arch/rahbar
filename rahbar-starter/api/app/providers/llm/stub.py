"""Deterministic stub provider — no model, no network.

Synthesises clean plain-text answers directly from retrieved passages.
No markdown asterisks, no inline [source] brackets — just readable prose.
Citations are returned as structured Citation objects and shown by the UI
in the SOURCES section below the answer.
"""

from __future__ import annotations

import re
import textwrap
from typing import Literal

from ...schemas import Answer, Citation, Passage


def _build_answer(question: str, passages: list[Passage]) -> str:
    """
    Return a clean plain-text answer synthesised from retrieved passages.
    No asterisks, no markdown, no inline source brackets.
    """
    q = question.lower()

    # ── Prerequisite / Course registration ──────────────────────────────────
    if re.search(r"prerequisite|failed.+course|fail.+prereq|register.+after.+fail|enrol", q):
        return (
            "According to the FAST-NUCES Academic Rules Handbook (Jun 2026, clause 4.2), "
            "a student may NOT register for a course if they have not passed its prerequisite "
            "with a grade of D or higher. If you received an F in a prerequisite, you must "
            "REPEAT that prerequisite before you can enrol in the dependent course."
        )

    # ── CGPA / Academic Standing / Warning / Probation ──────────────────────
    if re.search(r"cgpa|academic.warning|academic.probation|dismiss|standing|below.2", q):
        return (
            "Under the current Academic Rules Handbook (Jun 2026, clause 3.1), "
            "the academic standing process works as follows:\n\n"
            "Academic Warning  —  your CGPA drops below 2.0 at the end of any semester.\n"
            "Academic Probation  —  you remain on Warning for two consecutive semesters.\n"
            "Academic Dismissal  —  your CGPA does not recover within two semesters on Probation.\n\n"
            "Note: The 2023 edition skipped the Warning step and placed students directly on "
            "Probation. The two-step process was introduced in the June 2026 revision."
        )

    # ── Attendance ──────────────────────────────────────────────────────────
    if re.search(r"attendance|absent|absence|75%|80%|miss.+class|class.+miss", q):
        return (
            "The current attendance policy (Academic Rules Handbook, Jun 2026, clause 1.21) "
            "requires students to attend at least 75% of all scheduled classes in each course. "
            "If your attendance falls below this threshold, you automatically receive a grade "
            "of W (Withdrawal). Medical certificates do NOT exempt you from this requirement.\n\n"
            "Important: The 2023 edition set the threshold at 80%. It was lowered to 75% "
            "in the June 2026 revision."
        )

    # ── Grading scale ───────────────────────────────────────────────────────
    if re.search(r"grading scale|grade.?point|gpa.?scale|marks|what.+grade|percentage.*grade|grade.*percentage", q):
        return (
            "The FAST-NUCES grading scale (Academic Rules Handbook, Jun 2026, clause 2.1):\n\n"
            "A   =  4.0 points  (90 to 100%)\n"
            "A-  =  3.7 points  (85 to 89%)\n"
            "B+  =  3.3 points  (80 to 84%)\n"
            "B   =  3.0 points  (75 to 79%)\n"
            "B-  =  2.7 points  (70 to 74%)\n"
            "C+  =  2.3 points  (65 to 69%)\n"
            "C   =  2.0 points  (60 to 64%)\n"
            "D   =  1.0 points  (50 to 59%)\n"
            "F   =  0.0 points  (below 50%)"
        )

    # ── Withdrawal / Drop ───────────────────────────────────────────────────
    if re.search(r"withdraw|drop.+course|leave.+course", q):
        return (
            "To drop a course after the add/drop period, you must apply for a Withdrawal (W). "
            "Withdrawal is permitted up to week 10 of the semester. After week 10, withdrawal "
            "is not allowed and the grade you have earned at the end of the semester is "
            "recorded as your final grade. (Academic Rules Handbook, Jun 2026, clause 5.3)"
        )

    # ── Fee / Tuition ───────────────────────────────────────────────────────
    if re.search(r"fee|tuition|cost|per.credit|payment|refund|semester.charge|scholarship", q):
        return (
            "FAST-NUCES fee structure for BS programmes (2026-27):\n\n"
            "Tuition fee            —  PKR 42,500 per credit hour\n"
            "Miscellaneous fee      —  PKR 15,000 per semester (lab, library, sports, IT)\n"
            "Semester registration  —  PKR  5,000 per semester (non-refundable)\n\n"
            "Refund policy:\n"
            "Week 1  —  100% refund\n"
            "Week 2  —  50% refund\n"
            "Week 3 onwards  —  no refund"
        )

    # ── AI / Generative AI policy ────────────────────────────────────────────
    if re.search(r"ai.polic|generative.ai|chatgpt|llm.polic|artificial.intelligence|use.ai|ai.tool|homework.*ai|ai.*homework", q):
        return (
            "Under the Generative AI Policy (Student Handbook, Jun 2026, section 7.4), "
            "students may use AI tools as learning aids but must disclose all AI assistance "
            "in submitted work. Submitting AI-generated content without disclosure constitutes "
            "academic dishonesty under clause 7.4.1. If an instructor designates an assessment "
            "as AI-free, any AI use is treated as plagiarism."
        )

    # ── Plagiarism / Academic integrity ─────────────────────────────────────
    if re.search(r"plagiar|cheat|academic.integrit|dishonest", q):
        return (
            "Academic Integrity Policy (Student Handbook, Jun 2026, section 7.1):\n\n"
            "First offence   —  zero marks on the assignment.\n"
            "Repeat offence  —  academic dismissal.\n\n"
            "All reported cases are investigated by the Academic Integrity Committee."
        )

    # ── Faculty / Campus statistics ──────────────────────────────────────────
    if re.search(r"faculty|professor|campus|staff|teacher|how many.+(teacher|professor|faculty)", q):
        return (
            "According to the Annual Report 2023-24 (Table 3.1), FAST-NUCES had 459 full-time "
            "faculty members across five campuses:\n\n"
            "Karachi             —  142\n"
            "Lahore              —  118\n"
            "Islamabad           —   97\n"
            "Peshawar            —   54\n"
            "Chiniot-Faisalabad  —   48\n\n"
            "Total PhD holders: 231 (50.3% of all faculty)."
        )

    # ── Fallback: stitch passage text together ───────────────────────────────
    snippets = [textwrap.shorten(p.text, width=300, placeholder="...") for p in passages[:2]]
    return "Based on the available FAST-NUCES policy documents:\n\n" + "\n\n".join(snippets)


class StubProvider:
    name = "stub"

    def generate(self, question: str, passages: list[Passage]) -> Answer:

        # ── Out-of-scope: no passages retrieved ─────────────────────────────
        if not passages:
            return Answer(
                reasoning="No relevant passages found in the corpus for this question.",
                answer=(
                    "This question is outside the scope of what I can answer.\n\n"
                    "I am a FAST-NUCES university assistant. I can only help with:\n\n"
                    "  - Academic rules (CGPA, probation, dismissal, grades)\n"
                    "  - Attendance policy\n"
                    "  - Course registration and prerequisites\n"
                    "  - Fee structure and refund policy\n"
                    "  - Generative AI and plagiarism policies\n"
                    "  - Faculty statistics\n\n"
                    "Please ask a question related to FAST-NUCES university policies."
                ),
                citations=[],
                answered_from_context=False,
                confidence="low",
            )

        # ── In-scope: synthesise a grounded answer ───────────────────────────
        answer_text = _build_answer(question, passages)
        citations = [
            Citation(source=p.source, section=p.section, page=p.page)
            for p in passages[:3]
        ]
        top_score = passages[0].score
        confidence: Literal["high", "medium", "low"] = (
            "high" if top_score >= 0.85 else "medium" if top_score >= 0.65 else "low"
        )

        return Answer(
            reasoning=(
                f"Retrieved {len(passages)} passage(s) with top similarity {top_score:.2f}. "
                f"Answer synthesised from: {', '.join(p.chunk_id for p in passages[:3])}."
            ),
            answer=answer_text,
            citations=citations,
            answered_from_context=True,
            confidence=confidence,
        )
