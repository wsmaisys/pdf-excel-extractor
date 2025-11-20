"""FastAPI application for PDF → Excel extraction.

This module exposes a small REST API to upload PDFs, run the extraction
pipeline in the background, poll job status, and download generated Excel
files. It keeps a minimal in-memory job store (`JOBS`) for simplicity; for
production deployments a persistent job queue and storage should be used.
"""

import os
import uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from tools.pdf_detection import is_scanned
from pipeline.exporter import json_to_excel

load_dotenv()

# Root folder of the repository and a temporary directory for job artifacts
ROOT = Path(__file__).resolve().parent.parent
TMP = ROOT / 'tmp'
TMP.mkdir(exist_ok=True)

app = FastAPI(title='PDF→Excel Agent')
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')

# Simple in-memory job store. Keys are job_id and values hold status/logs/results.
# Note: this is intentionally lightweight for development/demo purposes.
JOBS = {}


@app.get('/', response_class=HTMLResponse)
async def index():
    html = (ROOT / 'static' / 'index.html').read_text(encoding='utf-8')
    return HTMLResponse(html)


@app.get('/favicon.ico')
async def favicon():
    """Serve a simple SVG favicon from the static directory to avoid 404 logs."""
    fav = ROOT / 'static' / 'favicon.svg'
    if fav.exists():
        return FileResponse(fav, media_type='image/svg+xml')
    # Fallback: no content to avoid 404 noise
    from fastapi import Response
    return Response(status_code=204)


@app.post('/upload')
async def upload(file: UploadFile = File(...), background: BackgroundTasks = None):
    """Endpoint to upload a PDF file and start background processing.

    Returns a `job_id` which can be used to poll `/status/{job_id}` and
    download the result when ready via `/download/{job_id}`.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail='Only PDF files supported')
    job_id = str(uuid.uuid4())
    job_dir = TMP / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = job_dir / file.filename
    content = await file.read()
    pdf_path.write_bytes(content)

    JOBS[job_id] = {'status': 'uploaded', 'logs': [], 'out': None}

    # enqueue background processing
    background.add_task(process_job, job_id, str(pdf_path))
    return {'job_id': job_id}


def log(job_id: str, message: str):
    JOBS[job_id]['logs'].append(message)


def extract_context_for_key(full_text: str, key: str, value: str) -> str:
    """Return a small text snippet from `full_text` that references `key` or `value`.

    This helper is used to provide context when computing evaluation metrics or
    displaying where an extracted value came from. It searches for the key first
    and falls back to searching for the value.
    """
    lines = full_text.split('\n')
    key_lower = key.lower().strip()

    # Search for a line mentioning the key and return a short window around it.
    for i, line in enumerate(lines):
        if key_lower in line.lower():
            start = max(0, i - 1)
            end = min(len(lines), i + 3)
            context = '\n'.join(lines[start:end])
            return context

    # Fallback: search for the value instead and return a nearby window.
    value_lower = value.lower().strip()
    for i, line in enumerate(lines):
        if value_lower in line.lower():
            start = max(0, i - 1)
            end = min(len(lines), i + 2)
            context = '\n'.join(lines[start:end])
            return context

    return None


def process_job(job_id: str, pdf_path: str):
    """Background worker that runs the extraction pipeline for a job.

    Steps performed (high-level):
      1. Detect PDF type (scanned vs digital)
      2. Extract text from PDF
      3. Detect dynamic schema using LLM
      4. Extract values using LLM batch extractor
      5. Compute n-gram metrics and evaluate quality
      6. Export results to Excel and register output path

    Any exception will mark the job as 'error' and the log will contain the
    exception message for debugging.
    """
    try:
        log(job_id, 'Detecting PDF type...')
        if is_scanned(pdf_path):
            log(job_id, 'PDF appears scanned. Stopping (no OCR path).')
            JOBS[job_id]['status'] = 'scanned'
            return

        # Extract full text from the PDF (simple concatenation of page text)
        log(job_id, 'Digital PDF detected; extracting text...')
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        full_text = '\n'.join([page.extract_text() or '' for page in reader.pages])
        log(job_id, f'Extracted {len(full_text)} characters from PDF.')

        # Dynamic schema detection using LLM
        log(job_id, 'Detecting schema from content...')
        from pipeline.schema_detector import get_dynamic_schema
        keys = get_dynamic_schema(full_text)
        if not keys:
            raise Exception('Failed to detect schema from content')
        log(job_id, f'Detected {len(keys)} fields from content.')

        # Semantic extraction (batch LLM call)
        log(job_id, 'Extracting values via LLM...')
        from pipeline.llm_extractor import extract_with_llm_mistral
        rows = extract_with_llm_mistral(full_text, keys)
        log(job_id, f'Extracted {len(rows)} key:value pairs via LLM.')

        # Compute n-gram metrics for each extracted field (optional enhancement)
        log(job_id, 'Computing n-gram metrics...')
        from evaluation.ngram_inspector import compare_ngrams
        ngram_metrics = {}
        for row in rows:
            key = row.get('key', '')
            value = row.get('value', '')
            if key and value:
                # Get a small reference text snippet around the key/value mention
                ref_text = extract_context_for_key(full_text, key, value)
                if ref_text:
                    metrics = compare_ngrams(ref_text, value, n_max=4)
                    # Keep a compact summary for UI and debugging
                    ngram_metrics[key] = {
                        'n1_precision': metrics[1]['precision'],
                        'n2_precision': metrics[2]['precision'],
                        'n3_precision': metrics[3]['precision'],
                        'n4_precision': metrics[4]['precision'],
                        'top_missing_3gram': metrics[3].get('top_missing', [])[:3],
                        'top_extra_3gram': metrics[3].get('top_extra', [])[:3],
                    }

        # Evaluate extraction quality (BLEU, coverage, etc.)
        log(job_id, 'Evaluating extraction quality...')
        from evaluation.bleu_scorer import evaluate_extraction_quality, format_confidence_score
        # Pass the full extracted text so the evaluator can derive reference
        # snippets when a gold standard is not available.
        eval_result = evaluate_extraction_quality(rows, full_text=full_text)
        confidence_str = format_confidence_score(eval_result)
        log(job_id, f'{confidence_str}')

        # Save results into the job record
        JOBS[job_id]['status'] = 'extracted'
        JOBS[job_id]['rows'] = rows
        JOBS[job_id]['eval_result'] = eval_result
        JOBS[job_id]['schema'] = keys
        JOBS[job_id]['ngram_metrics'] = ngram_metrics

        # Export to Excel and register output path
        out_xlsx = Path(pdf_path).with_name('Output_' + Path(pdf_path).stem + '.xlsx')
        json_to_excel(rows, str(out_xlsx))
        JOBS[job_id]['out'] = str(out_xlsx)

        # Keep extracted data for UI rendering
        JOBS[job_id]['data'] = rows
        JOBS[job_id]['status'] = 'done'
        log(job_id, f'Wrote Excel to {out_xlsx}')
    except Exception as e:
        JOBS[job_id]['status'] = 'error'
        log(job_id, f'Error: {e}')


@app.get('/status/{job_id}')
async def status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='job not found')
    return job


@app.get('/download/{job_id}')
async def download(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='job not found')
    out = job.get('out')
    if not out:
        raise HTTPException(status_code=404, detail='output not ready')
    return FileResponse(out, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=Path(out).name)
