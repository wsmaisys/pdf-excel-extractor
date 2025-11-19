#!/usr/bin/env python
"""End-to-end pipeline: PDF → Excel with dynamic schema detection and BLEU evaluation."""

import json
import sys
from pathlib import Path
from tools.pdf_detection import is_scanned
from pipeline.exporter import json_to_excel
from evaluation.bleu_scorer import evaluate_extraction_quality, format_confidence_score

def run_pipeline(pdf_path: str, output_xlsx: str = None, gold_json: str = None):
    """Run full pipeline: detect, extract with dynamic schema, export, evaluate."""
    pdf_path = Path(pdf_path)
    
    print(f"[1] Checking if PDF is scanned...")
    if is_scanned(str(pdf_path)):
        print("  ✗ PDF appears scanned. Stopping.")
        return False
    print("  ✓ Digital PDF detected.")
    
    print(f"[2] Extracting text...")
    from pypdf import PdfReader
    reader = PdfReader(str(pdf_path))
    full_text = '\n'.join([page.extract_text() or '' for page in reader.pages])
    print(f"  ✓ Extracted {len(full_text)} characters from PDF.")
    
    print(f"[3] Detecting dynamic schema from content...")
    from pipeline.schema_detector import get_dynamic_schema
    keys = get_dynamic_schema(full_text)
    if not keys:
        print("  ✗ Failed to detect schema.")
        return False
    print(f"  ✓ Detected {len(keys)} fields from content.")
    
    print(f"[4] Extracting values via LLM...")
    from pipeline.llm_extractor import extract_with_llm_mistral
    rows = extract_with_llm_mistral(full_text, keys)
    print(f"  ✓ Extracted {len(rows)} key:value pairs.")
    
    print(f"[5] Evaluating extraction quality...")
    eval_result = evaluate_extraction_quality(rows)
    confidence_str = format_confidence_score(eval_result)
    print(f"  {confidence_str}")
    
    # Set output path
    if output_xlsx is None:
        output_xlsx = str(Path(pdf_path).with_name('Output_' + Path(pdf_path).stem + '.xlsx'))
    
    print(f"[6] Exporting to Excel...")
    json_to_excel(rows, output_xlsx)
    print(f"  ✓ Wrote {output_xlsx}")
    
    # Save JSON too
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
