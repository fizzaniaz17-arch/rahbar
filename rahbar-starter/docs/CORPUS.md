# Corpus

The corpus consists of six public FAST-NUCES documents, including four PDFs
with 156 PDF pages in total. The two HTML pages are separate documents. All
six files matched the SHA-256 hashes in `corpus/MANIFEST.md`.

| # | Required property | Source and verification |
| --- | --- | --- |
| 1 | Six documents and at least 40 pages | Academic Rules 2023 (26 pages), Academic Rules 2026 (58 pages), Student Handbook 2026 (64 pages), ORIC Faculty Entrepreneurship policy (8 pages), Fee Structure (HTML) and Academic Grading (HTML). |
| 2 | Two editions of a policy | Undergraduate Academic Rules, August 2023 and June 2026. Metadata records versions `2023-08` and `2026-06`, with `superseded: true` on the 2023 edition. |
| 3 | Image-only scan | ORIC Faculty Entrepreneurship policy. `pdffonts` returned no fonts, and `pdftotext` returned only page separators. The indexer used OCR on all eight pages. The August 2023 academic rules also needed OCR on 24 of 26 pages. |
| 4 | Meaningful table | Fall 2026 Fee Structure links BS tuition to PKR 12,000 per credit hour. The grading page has grade-to-point tables. |
| 5 | Long definitions | The ORIC policy on PDF page 1 defines faculty entrepreneurship through several kinds of involvement, including governance and equity. The Student Handbook's AI policy also explains acceptable and unacceptable use across multiple pages. |
| 6 | Deliberately absent topic | Islamabad hostel room allocation and room changes. The Student Handbook mentions hostel facilities. The indexed sources provide neither a room-allocation points formula nor a room-change form number and deadline. |
| 7 | Exact terms | Clause 1.21 of Academic Rules 2026 sets the attendance requirement and its HoD exception. The grading table gives 3.33 points for a BS B+. |

The August 2023 rules describe an optional summer semester of eight to nine
weeks and permit a new elective when needed to graduate (PDF page 20). The
June 2026 edition specifies eight weeks and limits summer offerings to repeat
courses (PDF page 28, clauses 6.1 and 6.2). These differences support q09 and q10
in `eval/golden.yaml`, which ask about the current edition.

Run `python corpus/fetch.py` from the project root to fetch the six configured
sources and `python corpus/fetch.py --verify` to check their hashes. The source
files live in the gitignored `corpus/raw/` directory.
