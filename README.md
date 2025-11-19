# Semantic PDF Data Extraction Agent

**Production-ready AI agent that extracts structured data from unstructured PDF documents using LLM-powered semantic analysis.**

Converts narrative text PDFs into Excel spreadsheets with:

- **Dynamic schema detection**: LLM analyzes document to determine relevant fields (no hardcoded schema)

# Semantic PDF Data Extraction Agent — Final README

This README is the concise, non-redundant project reference: purpose, quick start, an important note about outputs, the workflow diagram, and a short file map.

## Important: download the output Excel immediately

The application generates an Excel file for each job and serves it for download, but Excel files are not persisted permanently on the server. Please download the Excel result immediately after the job completes. The UI table is provided for visual inspection only and is not a stored copy of the Excel file.

## Quick Start

1.  Create and activate a Python venv and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2.  Copy `.env.example` to `.env` and add your `MISTRAL_API_KEY`.

```powershell
cp .env.example .env
# edit .env
```

3.  Run the server and open the UI:

```powershell
uvicorn app.main:app --reload --port 8000
# open http://localhost:8000
```

---

## Workflow (compact)

```mermaid
flowchart TD
  A[Upload PDF] --> B[PDF Type Detection]
  B -- Digital --> C[Text Extraction]
  B -- Scanned --> X[Stop (OCR not supported)]
  C --> D[Dynamic Schema Detection (LLM)]
  D --> E[Batch LLM Extraction (all keys)]
  E --> F[Parse JSON → DataFrame]
  F --> G[Export Excel (Key | Value | Comment)]
  E --> H[Evaluation: BLEU + Coverage]
  H --> I[Confidence Score]
  G --> J[Download]
  I --> K[UI Display (badge, logs, table)]
```

---

## Minimal API overview (also see `API_DOCUMENTATION.md`)

- `POST /upload` — upload a PDF (multipart/form-data). Returns `{ job_id }`.
- `GET /status/{job_id}` — poll job status and logs; when done returns `data` and `eval_result`.
- `GET /download/{job_id}` — download the generated Excel file for the job.

See `API_DOCUMENTATION.md` for complete examples (curl and Python requests) and response schemas.

---

## Short file map

- `app/main.py` — FastAPI server and job orchestration (entrypoint).
- `static/index.html` — UI (upload, poll, render table, confidence badge).
- `pipeline/schema_detector.py` — LLM-based schema/key detection.
- `pipeline/llm_extractor.py` — Builds batch prompt, calls LLM, retry/backoff.
- `pipeline/exporter.py` — Converts extraction JSON to `pandas.DataFrame` and writes Excel.
- `tools/pdf_detection.py` — Checks whether PDF is digital or scanned.
- `evaluation/bleu_scorer.py` — BLEU score and coverage to compute confidence.
- `pipeline_runner.py` — CLI runner for offline/batch execution.
- `requirements.txt`, `.env.example`, `Dockerfile`, `plan.md` — environment and deployment aids.

---

## End-to-end processing (brief)

1.  Upload PDF via UI or `pipeline_runner.py`.
2.  `app/main.py` runs `tools/pdf_detection.py` (digital vs scanned).
3.  Extract text (if digital) and detect schema via `pipeline/schema_detector.py`.
4.  Run `pipeline/llm_extractor.py` (single batch LLM call) to extract values for detected keys.
5.  Optionally post-process with `pipeline/extract_kv.py` heuristics.
6.  Evaluate with `evaluation/bleu_scorer.py` and compute confidence.
7.  Export to Excel with `pipeline/exporter.py` and serve via `/download/{job_id}`.

---

If you'd like, I can:

- generate a PNG of the Mermaid workflow and add it to the repo,
- add client snippets to `API_DOCUMENTATION.md` (curl/Python already included),
- add unit tests for `bleu_scorer.py`.

Reply which one you want next and I'll proceed.
Ready for the next step — which of the above would you like me to do next?
