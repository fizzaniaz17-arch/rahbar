# Corpus

<!-- STARTER-TODO(2): fill every row, then delete this comment. -->

Source: FAST-NUCES public website / our own documents (pick one) · Documents: ? · Pages: ?

| # | Required property | Document(s) that provide it | Evidence or notes |
| --- | --- | --- | --- |
| 1 | At least 6 documents, 40 pages | | |
| 2 | Two versions of one policy | | Which supersedes which, and how your metadata records it |
| 3 | Scanned, image-only PDF | | `pdffonts` output, or how you proved it has no text layer |
| 4 | A table with real information | | |
| 5 | Long definitions | | |
| 6 | A deliberately absent topic | | What you left out, and why a user would plausibly ask about it |
| 7 | Exact-term content | | Clause numbers, codes, thresholds, fees |

## FAST-NUCES source selection for the real evaluation

| Requirement | Selected source and verification status |
| --- | --- |
| At least six documents and 40 PDF pages | Six candidate sources are listed in `corpus/sources.yaml`. The June 2026 academic rules PDF has 58 pages. Verify the count against downloaded files. |
| Two editions of the same policy | August 2023 and June 2026 undergraduate academic rules. The historical edition is marked superseded. Compare the editions before writing version-sensitive golden questions. |
| Scanned PDF | ORIC Faculty Entrepreneurship and Technical Start-ups policy. Verify the page text layers and record OCR results after downloading. |
| Meaningful table | The official Fee Structure and Academic Grading pages are selected for fee and grade-point tables. |
| Long definitions | The June 2026 Student Handbook is selected for its GenAI policy. Verify that section in the downloaded file. |
| Deliberately absent topic | Detailed hostel eligibility and room allocation rules. The Transport and Hostel Facilities prospectus is excluded. Verify the indexed text has no answer before labeling these questions must-abstain. |
| Exact terms | The 2026 academic rules include clause 1.21 on attendance and clause 5.4 on the CGPA threshold. |

The university's Downloads and Islamabad Rules and Regulations pages list the
academic documents. The university's ORIC policies page lists the scanned PDF
candidate. Record successful downloads and SHA-256 hashes with
`python corpus/fetch.py` and `python corpus/fetch.py --verify` from the project
directory. The manifest and real-corpus results must reflect an actual run.
