"""Seeded stub retriever: returns question-matched passages from a built-in
FAST-NUCES corpus snapshot.

Covers the assignment's seven corpus properties so the dev server gives
meaningful answers while the real Chroma index is being built.
Switch to RETRIEVER=chroma in the ConfigMap once your index exists.
"""

from __future__ import annotations

import re

from ..schemas import Passage

# ---------------------------------------------------------------------------
# Seeded corpus: representative passages from FAST-NUCES public documents.
# Each entry covers one or more assignment corpus properties (noted in comments).
# ---------------------------------------------------------------------------

_CORPUS: list[Passage] = [
    # ── Academic Rules Handbook 2026 (current) ──────────────────────────────
    Passage(
        chunk_id="arh26-001",
        text=(
            "A student whose CGPA falls below 2.0 at the end of any semester is placed on "
            "Academic Warning. A student on Academic Warning for two consecutive semesters "
            "is placed on Academic Probation. A student on Academic Probation whose CGPA "
            "does not reach 2.0 within the next two semesters is academically dismissed. "
            "(Academic Rules Handbook, Jun 2026, clause 3.1)"
        ),
        source="academic-rules-handbook-2026.pdf",
        section="3.1 Academic Standing",
        page=12,
        score=0.0,
    ),
    Passage(
        chunk_id="arh26-002",
        text=(
            "A student may not register for a course if they have not passed its prerequisite "
            "with a grade of D or higher. A grade of F in a prerequisite requires the student "
            "to repeat the prerequisite before registering for the dependent course. "
            "(Academic Rules Handbook, Jun 2026, clause 4.2)"
        ),
        source="academic-rules-handbook-2026.pdf",
        section="4.2 Prerequisite Policy",
        page=18,
        score=0.0,
    ),
    Passage(
        chunk_id="arh26-003",
        text=(
            "Attendance below 75% in any course results in a grade of W (Withdrawal) being "
            "awarded automatically. The 75% threshold is calculated on total scheduled classes "
            "up to the last day of the semester. Medical certificates do not exempt a student "
            "from the attendance requirement. (Academic Rules Handbook, Jun 2026, clause 1.21)"
        ),
        source="academic-rules-handbook-2026.pdf",
        section="1.21 Attendance",
        page=7,
        score=0.0,
    ),
    Passage(
        chunk_id="arh26-004",
        text=(
            "The grading scale is: A (4.0, 90–100%), A- (3.7, 85–89%), B+ (3.3, 80–84%), "
            "B (3.0, 75–79%), B- (2.7, 70–74%), C+ (2.3, 65–69%), C (2.0, 60–64%), "
            "D (1.0, 50–59%), F (0.0, below 50%). "
            "(Academic Rules Handbook, Jun 2026, clause 2.1)"
        ),
        source="academic-rules-handbook-2026.pdf",
        section="2.1 Grading Scale",
        page=9,
        score=0.0,
    ),
    Passage(
        chunk_id="arh26-005",
        text=(
            "A student wishing to drop a course after the add/drop period must apply for "
            "Withdrawal (W). Withdrawal is permitted up to week 10 of the semester. "
            "After week 10 no withdrawal is allowed; the grade earned at the end of the "
            "semester is recorded. (Academic Rules Handbook, Jun 2026, clause 5.3)"
        ),
        source="academic-rules-handbook-2026.pdf",
        section="5.3 Course Withdrawal",
        page=22,
        score=0.0,
    ),
    # ── Academic Rules Handbook 2023 (superseded) ───────────────────────────
    Passage(
        chunk_id="arh23-001",
        text=(
            "A student whose CGPA falls below 2.0 is placed on Academic Probation. "
            "A student on Academic Probation for two consecutive semesters is dismissed. "
            "Note: this clause was revised in the Jun 2026 edition which introduced a "
            "two-step Warning→Probation process. "
            "(Undergraduate Academic Rules, Aug 2023, clause 3.1) [SUPERSEDED]"
        ),
        source="undergraduate-academic-rules-2023.pdf",
        section="3.1 Academic Standing",
        page=10,
        score=0.0,
    ),
    Passage(
        chunk_id="arh23-002",
        text=(
            "Attendance below 80% in any course results in automatic Withdrawal. "
            "Note: the threshold was lowered to 75% in the Jun 2026 handbook. "
            "(Undergraduate Academic Rules, Aug 2023, clause 1.5) [SUPERSEDED]"
        ),
        source="undergraduate-academic-rules-2023.pdf",
        section="1.5 Attendance",
        page=5,
        score=0.0,
    ),
    # ── Prospectus 2026: Academic Rules and Regulations ─────────────────────
    Passage(
        chunk_id="prosp26-001",
        text=(
            "Attendance: A student must attend at least 75% of lectures in each course "
            "to be eligible for the final examination (clause 1, Prospectus 2026). "
            "Note: in the full Academic Rules Handbook this is clause 1.21."
        ),
        source="prospectus-2026-academic-rules.pdf",
        section="1 Attendance",
        page=2,
        score=0.0,
    ),
    # ── Fee Structure ────────────────────────────────────────────────────────
    Passage(
        chunk_id="fee-001",
        text=(
            "Tuition fee for BS programmes: PKR 42,500 per credit hour (2026–27). "
            "Miscellaneous fee: PKR 15,000 per semester (lab, library, sports, IT). "
            "Semester registration fee: PKR 5,000 (non-refundable). "
            "Refund policy: 100% within week 1; 50% in week 2; 0% from week 3 onward."
        ),
        source="fee-structure-2026-27.pdf",
        section="Undergraduate Fee Schedule",
        page=1,
        score=0.0,
    ),
    # ── Student Handbook 2026 ────────────────────────────────────────────────
    Passage(
        chunk_id="sh26-001",
        text=(
            "Generative AI Policy (Student Handbook, Jun 2026, section 7.4): Students may "
            "use generative AI tools as learning aids but must disclose all AI assistance in "
            "submitted work. Submitting AI-generated content without disclosure constitutes "
            "academic dishonesty under clause 7.4.1. Instructors may require AI-free "
            "assessments, in which case any AI use is treated as plagiarism."
        ),
        source="student-handbook-2026.pdf",
        section="7.4 Generative AI Policy",
        page=41,
        score=0.0,
    ),
    Passage(
        chunk_id="sh26-002",
        text=(
            "Disciplinary action for plagiarism ranges from a zero on the assignment (first "
            "offence) to academic dismissal (repeat offence). The Academic Integrity Committee "
            "investigates all reported cases. (Student Handbook, Jun 2026, section 7.1)"
        ),
        source="student-handbook-2026.pdf",
        section="7.1 Academic Integrity",
        page=38,
        score=0.0,
    ),
    # ── Annual Report 2023-24 (tables) ──────────────────────────────────────
    Passage(
        chunk_id="ar24-001",
        text=(
            "FAST-NUCES faculty count by campus (2023–24): Karachi 142, Lahore 118, "
            "Islamabad 97, Peshawar 54, Chiniot-Faisalabad 48. Total full-time faculty: 459. "
            "PhD holders: 231 (50.3%). (Annual Report 2023-24, Table 3.1)"
        ),
        source="annual-report-2023-24.pdf",
        section="3.1 Faculty Statistics",
        page=24,
        score=0.0,
    ),
]

# ---------------------------------------------------------------------------
# Positive whitelist: question must contain at least one university-related
# keyword to get any passages back. This prevents personal / off-topic
# questions ("what is my friend's name?", "how to cook biryani?", etc.)
# from accidentally matching the generic fallback and getting corpus passages.
# ---------------------------------------------------------------------------

_UNIVERSITY_TOPIC = re.compile(
    r"cgpa|gpa|grade|grading|marks|score|semester|credit|course|subject|"
    r"prerequisite|registr|enrol|enroll|attend|absent|absence|75%|80%|"
    r"withdraw|drop|probation|warning|dismiss|academic|university|nuces|fast|"
    r"fee|tuition|refund|payment|scholarship|"
    r"ai.polic|generative.ai|chatgpt|plagiar|cheat|integrit|dishonest|"
    r"faculty|professor|campus|staff|teacher|department|dean|rector|"
    r"handbook|rules|regulation|policy|clause|section|prospectus|"
    r"exam|test|quiz|assignment|project|thesis|report|result|transcript|"
    r"hostel|transport|canteen|library|lab|"
    r"stub|document|rahbar|system|assistant|what.+say",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Topic→chunk_id index for keyword matching.
# Each entry is (regex_pattern, [chunk_ids in relevance order]).
# ---------------------------------------------------------------------------

_INDEX: list[tuple[str, list[str]]] = [
    # prerequisite / failing / registration
    (r"prerequisite|failed.+course|fail.+prereq|register.+after.+fail|course.+registr|enrol",
     ["arh26-002", "arh26-001"]),
    # CGPA / academic warning / probation / dismissal
    (r"cgpa|academic.warning|academic.probation|dismiss|standing|below.2",
     ["arh26-001", "arh26-004", "arh23-001"]),
    # attendance / absence / 75%
    (r"attendance|absent|absence|75%|80%|miss.+class|class.+miss",
     ["arh26-003", "prosp26-001", "arh23-002"]),
    # grading / grade / GPA / marks
    (r"grad(e|ing)|gpa|marks|score|what.+grade|grade.+point",
     ["arh26-004", "arh26-001"]),
    # withdrawal / drop / W grade
    (r"withdraw|drop.+course|W.grade|leave.+course",
     ["arh26-005"]),
    # fee / tuition / cost / refund
    (r"fee|tuition|cost|per.credit|payment|refund|semester.charge|scholarship",
     ["fee-001"]),
    # AI policy / generative AI / ChatGPT
    (r"ai.polic|generative.ai|chatgpt|llm.polic|artificial.intelligence|use.ai|ai.tool",
     ["sh26-001", "sh26-002"]),
    # plagiarism / academic integrity / cheating
    (r"plagiar|cheat|academic.integrit|dishonest",
     ["sh26-002", "sh26-001"]),
    # faculty / staff / campus
    (r"faculty|professor|campus|staff|teacher|how many.+(teacher|professor|faculty)",
     ["ar24-001"]),
    # version-sensitive: old rules vs new
    (r"old.rule|2023.rule|previous.polic|supersed|before.2026",
     ["arh23-001", "arh23-002", "arh26-001", "arh26-003"]),
    # exam / result / transcript
    (r"exam|result|transcript|pass.+course|fail.+course",
     ["arh26-004", "arh26-001", "arh26-002"]),
]

_corpus_by_id: dict[str, Passage] = {p.chunk_id: p for p in _CORPUS}


def _score(question: str) -> list[Passage]:
    """
    Return relevant passages for the question.

    Logic:
    1. If the question does NOT contain any university-related keyword → return []
       (triggers honest abstention, never return random corpus passages).
    2. Try each topic pattern; collect matching chunk ids with scores.
    3. If topic patterns match → return ranked results.
    4. If question looks like a university question but no specific topic matches
       → return a small generic set at low confidence so the user gets
         a helpful "here's what I do cover" answer instead of silence.
    """
    q = question.lower()

    # Step 1: gate — must look like a university question
    if not _UNIVERSITY_TOPIC.search(q):
        return []  # personal / off-topic → abstain

    # Step 2: topic matching
    seen: dict[str, float] = {}
    for pattern, ids in _INDEX:
        if re.search(pattern, q, re.IGNORECASE):
            for rank, cid in enumerate(ids):
                seen[cid] = max(seen.get(cid, 0.0), 0.95 - rank * 0.05)

    if not seen:
        # Step 4: vague university question (e.g. "tell me about FAST rules")
        # Return generic passages at LOW score — below high confidence but above floor
        return [
            _corpus_by_id["arh26-001"].model_copy(update={"score": 0.55}),
            _corpus_by_id["arh26-003"].model_copy(update={"score": 0.52}),
            _corpus_by_id["arh26-004"].model_copy(update={"score": 0.51}),
        ]

    ranked = sorted(seen.items(), key=lambda kv: kv[1], reverse=True)
    return [_corpus_by_id[cid].model_copy(update={"score": s}) for cid, s in ranked]


class StubRetriever:
    name = "stub"

    def retrieve(self, question: str, k: int) -> list[Passage]:
        return _score(question)[:k]

