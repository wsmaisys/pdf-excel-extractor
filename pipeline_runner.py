#!/usr/bin/env python
"""End-to-end pipeline runner: PDF → Excel with dynamic schema detection.

This lightweight CLI runs the same pipeline used by the web server and is
useful for offline testing and batch processing. It orchestrates detection,
schema discovery, LLM-based extraction, evaluation and export.
"""

import json
import sys
from pathlib import Path
from tools.pdf_detection import is_scanned
from pipeline.exporter import json_to_excel
from evaluation.bleu_scorer import evaluate_extraction_quality, format_confidence_score


def run_pipeline(pdf_path: str, output_xlsx: str = None, gold_json: str = None):
    """Run the full pipeline for a single PDF file.

    Returns True on success, False on recoverable failure (e.g., scanned PDF or
    schema detection failure). Exceptions may propagate for unexpected errors.
    """
    pdf_path = Path(pdf_path)

    # 1) PDF type detection
    print(f"[1] Checking if PDF is scanned...")
    if is_scanned(str(pdf_path)):
        print("  ✗ PDF appears scanned. Stopping.")
        return False
    print("  ✓ Digital PDF detected.")

    # 2) Text extraction (naive page-wise extraction)
    print(f"[2] Extracting text...")
    from pypdf import PdfReader
    reader = PdfReader(str(pdf_path))
    full_text = '\n'.join([page.extract_text() or '' for page in reader.pages])
    print(f"  ✓ Extracted {len(full_text)} characters from PDF.")

    # 3) Dynamic schema detection
    print(f"[3] Detecting dynamic schema from content...")
    from pipeline.schema_detector import get_dynamic_schema
    keys = get_dynamic_schema(full_text)
    if not keys:
        print("  ✗ Failed to detect schema.")
        return False
    print(f"  ✓ Detected {len(keys)} fields from content.")

    # 4) Semantic extraction via LLM
    print(f"[4] Extracting values via LLM...")
    from pipeline.llm_extractor import extract_with_llm_mistral
    rows = extract_with_llm_mistral(full_text, keys)
    print(f"  ✓ Extracted {len(rows)} key:value pairs.")

    # 5) Evaluation
    print(f"[5] Evaluating extraction quality...")
    eval_result = evaluate_extraction_quality(rows)
    confidence_str = format_confidence_score(eval_result)
    print(f"  {confidence_str}")

    # Determine output path if not provided
    if output_xlsx is None:
        output_xlsx = str(Path(pdf_path).with_name('Output_' + Path(pdf_path).stem + '.xlsx'))

    # 6) Export to Excel and save artifacts
    print(f"[6] Exporting to Excel...")
    json_to_excel(rows, output_xlsx)
    print(f"  ✓ Wrote {output_xlsx}")

    # Save JSON of extracted rows
    json_out = Path(output_xlsx).with_suffix('.json')
    json_out.write_text(json.dumps(rows, indent=2, ensure_ascii=False))
    print(f"  ✓ Wrote {json_out}")

    # Save evaluation metrics
    eval_out = Path(output_xlsx).with_stem(Path(output_xlsx).stem + '_evaluation').with_suffix('.json')
    eval_out.write_text(json.dumps(eval_result, indent=2, ensure_ascii=False))
    print(f"  ✓ Wrote {eval_out}")
    print(f"\n  Evaluation Details:")
    print(f"    - Average BLEU: {eval_result['avg_bleu']*100:.1f}%")
    print(f"    - Coverage: {eval_result['coverage']*100:.1f}% ({eval_result['non_empty_fields']}/{eval_result['total_fields']} fields)")

    return True


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python pipeline_runner.py input.pdf [gold.json]')
        raise SystemExit(1)

    pdf = sys.argv[1]
    gold = sys.argv[2] if len(sys.argv) > 2 else None
    out = Path(pdf).with_name('Output_' + Path(pdf).stem + '.xlsx')
    run_pipeline(pdf, str(out), gold)
