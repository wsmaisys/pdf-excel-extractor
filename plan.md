# AI Agent Plan: PDF → Structured Excel (Key/Value/Comment)

## Overview

Build a reproducible, auditable AI Agent that:

- Detects whether an uploaded PDF is digital (text-layer) or scanned image-based.
- If scanned: stop and inform the user (no OCR path required per spec).
- If digital: extract exact page-by-page text (use `extract_pdf_text.py`).
- Convert text into a strictly extractive JSON array of rows with three fields: `key`, `value`, `comment`.
- Convert JSON into a pandas DataFrame and export as `Output.xlsx`.
- Provide end-to-end transparency via a FastAPI app with realtime UI (progress + logs + preview) and a LangChain agent orchestrator using the Mistral LLM as a constrained fallback for ambiguous mappings.

> Important constraint: Extraction must be exact. Avoid LLM hallucination. Use deterministic parsing first and only call LLM in a tightly constrained, extractive mode showing quoted excerpts and asking for explicit verbatim outputs.

---

## Assumptions

- `.env` contains `API_KEY` and `MODEL_NAME` for Mistral.
- `extract_pdf_text.py` exists and reliably extracts text for digital PDFs (page-by-page).
- The client expects exact text preservation; minimal transformation (trimming whitespace, normalize line breaks) only to enable key:value mapping.

---

## Architecture (High Level)

1. Ingest (FastAPI upload endpoint)
2. PDF Type Detection (digital vs scanned)
3. Text Extraction (`extract_pdf_text.py` tool)
4. Key:Value Extraction (rule-based parser + LLM fallback)
5. JSON output (array of {key,value,comment})
6. Convert → DataFrame → Excel (downloadable)
7. Evaluation Module (metrics + diff report)
8. Orchestration via LangChain agent; UI streams status via WebSocket or Server-Sent Events (SSE)

---

## Component Details

### 1) PDF Type Detection

- Goal: deterministically decide scanned vs digital PDF.
- Method:
  - Use `pypdf` (PdfReader) and for each page check `page.extract_text()` output length. If `extract_text()` returns None or empty for most pages AND resources show image XObjects, treat as scanned.
  - If scanned: agent returns a short apology + message "file is scanned — cannot proceed" and stops.
- File: `tools/pdf_detection.py` (function `is_scanned(pdf_path) -> bool`)

### 2) Text Extraction Tool

- Reuse and wrap `extract_pdf_text.py` into a callable tool for the agent.
- Interface: `extract_text(pdf_path) -> List[ {page: int, text: str} ]`.
- Keep original wording and line breaks. Add metadata: original page number, character offsets if helpful.
- File: `tools/extract_pdf_tool.py` (wraps your existing script)

### 3) Key:Value Extraction Pipeline (core requirement)

- Primary approach: deterministic, rule-based extraction pipeline. Steps:
  1. Preprocess: preserve line breaks, normalize only for consistent handling (e.g., unify CRLF). Don't change sentences.
  2. Heuristic block segmentation: split document into logical blocks using blank lines, headings (ALL CAPS or bold markers), bullets, or colon-based lines (`Key: Value`).
  3. Patterns to extract key:value pairs:
     - Lines matching `^\s*([^:\n]{1,200}?)\s*:\s*(.+)$` → key = group1, value = group2.
     - Paired lines where a line looks like a key label and the next line(s) are the value (e.g. label on one line, value on next) — capture multi-line values until next label or blank line.
     - Tables: detect if the PDF text contains tabular separators or consistent columns; fallback to per-cell extraction preserving text.
  4. Comments: any surrounding textual context (one preceding and one following sentence/line) or explicit notes in the same paragraph; store as `comment` verbatim.
  5. Edge cases: duplicate keys, keys spanning lines — capture fully and add a `comment` noting the original page and line numbers.
- Output schema (JSON array):
  [
  { "key": "<exact key text>", "value": "<exact value text>", "comment": "<contextual text or empty>" },
  ...
  ]
- LLM fallback (Mistral via LangChain):
  - ONLY for blocks the rule-based parser fails to convert (e.g., ambiguous structure).
  - Use a constrained prompt: show the minimal original text block, explicit instruction to extract exact verbatim Key and Value only, and to return JSON following the exact schema. Include examples. Do not allow paraphrase. If LLM cannot provide exact extracts, mark the row `needs_review: true` and include raw block in `comment`.
  - Always log LLM outputs and show them in UI for human review.
- File: `pipeline/extract_kv.py`

### 4) JSON → DataFrame → Excel

- Use `pandas.DataFrame` with columns `key`, `value`, `comment`.
- Export with `df.to_excel(output_path, index=False, engine='openpyxl')`.
- Keep encoding and formatting simple; preserve multiline cells.
- File: `pipeline/exporter.py`

### 5) Evaluation Module (suggestions & approach)

I recommend a combination of automated metrics and human-review tooling. Automated metrics:

- Exact Match Rate (EMR): fraction of extracted `value` strings that exactly match ground-truth `value` strings. This is strict and aligns with "exact extraction" requirement.
- Key Coverage (Recall): fraction of ground-truth keys present in the agent output.
- Precision: fraction of output key:value pairs that exist in ground-truth (avoids spurious extractions).
- String Similarity Metrics for near-misses: normalized Levenshtein distance or token-level Jaccard to show how close a non-exact match is.
- Row-level Diff Report: for every ground-truth row, show extracted row, EM-match boolean, distance metric, and link to source page/block.

Human-in-the-loop:

- UI view with a side-by-side diff (original block, extracted key/value, ground-truth) with accept/reject.
- Export an evaluation report `evaluation_report.json` and `evaluation_report.xlsx`.

Automated test harness:

- Add a directory `tests/samples/` with pairs of `Data Input.pdf` + `expected_output.json/xlsx` and run the evaluation automatically in CI.

### 6) LangChain / Agent Orchestration

- Tools to register with the agent:
  - `detect_pdf_type(pdf_path)`
  - `extract_text(pdf_path)`
  - `extract_kv_from_text(block)` (the parser)
  - `export_json_to_excel(json, out_path)`
  - `evaluate_output(gold_path, out_path)`
- Agent flow:
  1. Call `detect_pdf_type`.
  2. If digital: call `extract_text`.
  3. Feed pages into the deterministic parser in streaming mode.
  4. For each ambiguous block, optionally call LLM with strict instruction and capture response.
  5. Assemble final JSON and export to Excel.
- Keep the agent's LLM calls minimal and audited.

### 7) FastAPI app & Realtime UI

- Endpoints:
  - `POST /upload` → accepts PDF, returns `job_id`.
  - `GET /status/{job_id}` → job progress + basic logs.
  - `WS /ws/{job_id}` or `GET /events/{job_id}` (SSE) → realtime log stream and step-level events.
  - `GET /download/{job_id}` → download resulting `Output.xlsx`.
  - `GET /preview/{job_id}` → preview JSON or small HTML table.
- Background worker: use `concurrent.futures.ThreadPoolExecutor` or `BackgroundTasks` in FastAPI to run the agent asynchronously.
- UI: minimal HTML + JS showing a timeline of steps and streaming logs; preview table using DataTables or simple table. Provide a manual "flag for review" control.
- Files: `app/main.py`, `app/static/*`, `app/templates/*`

---

## Security & Operational Notes

- Load `API_KEY` and `MODEL_NAME` from `.env` (do not commit `.env`).
- Sanitize file uploads and store temporarily (e.g., `tmp/{job_id}/`).
- Keep LLM usage logged (inputs + outputs) for audit; store only minimal logs for privacy.

---

## Development Roadmap & Estimated Effort

(Assuming 3–4 full workdays available — adjust as needed)

1. Day 0.5 — Project scaffold, venv/requirements, basic FastAPI skeleton, wire `extract_pdf_text.py` as a tool.
2. Day 1 — Implement PDF detection + deterministic key:value parser (core). Unit tests for common patterns.
3. Day 0.5 — JSON → DataFrame → Excel exporter + download endpoint.
4. Day 0.5 — LangChain agent wiring, minimal LLM fallback with strict prompting.
5. Day 0.5 — Build evaluation module (automated metrics + report generation).
6. Day 0.5 — UI with realtime logs + preview and polish; README and sample tests.

Total: ~3–4 days to reach a polished MVP.

---

## Deliverables (per your original assignment)

- GitHub repo with full source code and `README.md`.
- Live demo hostable temporarily (e.g., `uvicorn` run on a VM or temporary cloud instance) — instructions provided.
- Final generated `Output.xlsx` for any sample `Data Input.pdf`.

---

## Next Steps I can take now

- Implement the deterministic parser (`pipeline/extract_kv.py`) and unit tests using the existing `Assignement Details.pdf` and `Data Input.pdf` sample (if you want me to proceed now I will start with the parser and exports).

---

## Appendices: Prompt Template (if LLM fallback is used)

System prompt (strict):

"You are an extractive assistant. Given the EXACT block of text (below) return a JSON array of objects with fields `key`, `value`, and `comment`. Use the text verbatim — do NOT paraphrase or add new information. If a `key` cannot be reliably identified, return an empty array. If the output is empty, return `[]`. Always return valid JSON and nothing else. Example: [{\"key\":\"Invoice No\",\"value\":\"12345\",\"comment\":\"page 2 context\"}]"

User content: the original block to parse (quoted)

---

End of plan.md
