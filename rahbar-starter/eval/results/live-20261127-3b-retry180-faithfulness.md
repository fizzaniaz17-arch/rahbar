# Live 3B faithfulness review

**Run:** `live-20261127-3b-retry180`
**Scope:** All 26 responses, checked against the cited passages captured in the live API traces.
**Method:** Qualitative review of answer relevance and support. This is not an independent human review or a calibrated automated faithfulness score.

## Findings

- The five must-abstain cases (q13, q14, q19, q20, q26) were declined.
- q22 also abstained, although its retrieved evidence matched the gold source. This is an incorrect abstention on an answerable question.
- All 56 returned citations point to passages in the corresponding retrieval set (citation validity 1.0). Citation validity alone does not establish that the answer is relevant or complete.
- Material answer/evidence issues:
  - q07 and q21 ask which types of founder involvement count. The answers instead describe management-role restrictions and do not provide the requested categories.
  - q10 answers with the general undergraduate admissions schedule rather than whether a new elective can be taken in summer.
  - q17 gives “A+ Outstanding approval” for the additional year; the expected rule names Statutory Bodies.
  - q24 answers yes and gives the two-course limit, while the cited summer rule limits summer registration to repeats.
- Incomplete details also appear in q05 (rate unit omitted), q08 (associated labs omitted), q15/q25 (the Head-of-Department exception omitted), and q23 (fact-checking against reliable sources omitted).

## Verdict

Faithfulness is **not demonstrated as a passing metric**. The evaluator does not calculate faithfulness, and this qualitative review found material relevance/correctness issues despite perfect citation validity. Do not report a numeric faithfulness score or claim answer quality passed.
