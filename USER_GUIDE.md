# User Guide: Offline Engineering-Docs Assistant

## 1. Asking good questions
- Ask one thing at a time.
- Name the document or part number: "in MM-3300", "part number 7741-0032", "in MIL-STD-882E".
- If revisions matter, say which: "in Revision B of EQ-SPEC-1001".
- Use the document's own terms (e.g. "operating temperature", "severity category").
- Run: python ask.py "your question"

## 2. Checking a source
Every answer ends with a Sources list: file name, page, section, revision, marking.
1. Open that file at that page.
2. Confirm the value in the answer matches the page, including decimal points and units.
3. If a WARNING says several revisions were found, check the ECN to see which revision is current.

## 3. What the tool cannot do
- It answers only from indexed documents. "Not found in the documents." means nothing relevant was found, not that the fact is false.
- A small local model can make mistakes with decimals, tables and long documents. Always verify numbers.
- It cannot read documents that were not ingested, browse the internet, or replace engineering review.
- It does not decide which revision is current; use the ECN.

## 4. Traceability
Every question is logged in data/query_log.jsonl with the time, question, model name and sources used.