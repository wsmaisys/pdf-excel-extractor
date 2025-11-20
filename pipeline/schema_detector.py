"""Dynamic schema detection using an LLM.

This module asks the LLM to analyze a document's text and return a JSON
array of suggested field names. The returned list is used as the extraction
schema for downstream components.
"""

import json
import os
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()


def detect_schema_from_text(text: str, max_keys: int = 40) -> List[str]:
    """
    Use LLM to analyze text and determine what schema keys should be extracted.
    Returns list of suggested field names based on content analysis.
    """
    try:
        # Use the LangChain Mistral adapter when available
        from langchain_mistralai import ChatMistralAI
        from langchain_core.messages import HumanMessage
    except ImportError:
        print("  ERROR: langchain_mistralai not installed")
        return []
    
    api_key = os.getenv('MISTRAL_API_KEY')
    model = os.getenv('MODEL', 'mistral-small-latest')
    
    if not api_key:
        print("  ERROR: MISTRAL_API_KEY not set")
        return []
    
    llm = ChatMistralAI(
        model=model,
        api_key=api_key,
        temperature=0.1,
        max_tokens=3000
    )
    
    prompt = f"""Analyze the following text and identify ALL important information fields that should be extracted.
Return a JSON list of field names (keys) that represent the key information in this document.

Rules:
1. Be comprehensive - capture all important data points
2. Use clear, descriptive field names (e.g., "First Name", "Date of Birth", "Email Address")
3. Group related information (e.g., separate "Undergraduate Degree" and "Undergraduate College")
4. Limit to approximately {max_keys} fields maximum
5. Return ONLY a valid JSON array of strings, no explanation or preamble

Text to analyze:
---
{text[:3000]}
---

Return format: ["Field Name 1", "Field Name 2", "Field Name 3", ...]
"""
    
    import time
    print("  Detecting schema from text...")
    # Slight pause to make logs/readability nicer and avoid immediate throttling
    time.sleep(2)
    
    try:
        message = HumanMessage(content=prompt)
        response = llm.invoke([message])
        response_text = response.content
        
        # Extract JSON from response
        import re
        json_match = re.search(r'\[[\s\S]*\]', response_text)
        if not json_match:
            print("  ERROR: No JSON array in schema detection response")
            return []
        
        schema = json.loads(json_match.group(0))
        
        # Validate and clean schema
        if not isinstance(schema, list):
            print("  ERROR: Schema is not a list")
            return []
        
        schema = [str(s).strip() for s in schema if s and str(s).strip()]
        print(f"  ✓ Detected {len(schema)} fields from text")
        return schema
        
    except json.JSONDecodeError as e:
        print(f"  ERROR parsing schema JSON: {e}")
        return []
    except Exception as e:
        print(f"  ERROR detecting schema: {e}")
        return []


def get_dynamic_schema(text: str) -> List[str]:
    """
    Get dynamic schema by analyzing text with LLM.
    Falls back to empty list if detection fails.
    """
    schema = detect_schema_from_text(text)
    return schema if schema else []


if __name__ == '__main__':
    import sys
    from pathlib import Path
    from pypdf import PdfReader
    
    if len(sys.argv) < 2:
        print('Usage: python schema_detector.py input.pdf')
        raise SystemExit(1)
    
    pdf_path = sys.argv[1]
    reader = PdfReader(pdf_path)
    text = '\n'.join([page.extract_text() or '' for page in reader.pages])
    
    schema = get_dynamic_schema(text)
    
    print(f'\nDetected Schema ({len(schema)} fields):')
    print(json.dumps(schema, indent=2, ensure_ascii=False))
    
    # Save schema
    out_schema = Path(pdf_path).with_stem(Path(pdf_path).stem + '_schema').with_suffix('.json')
    out_schema.write_text(json.dumps(schema, indent=2, ensure_ascii=False))
    print(f'\nSaved to {out_schema}')
