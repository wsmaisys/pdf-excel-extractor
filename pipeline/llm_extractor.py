import json
from typing import List, Dict
import os
from dotenv import load_dotenv
from pathlib import Path
import time

load_dotenv()


def extract_with_llm_mistral_batch(text: str, keys: List[str]) -> List[Dict[str, str]]:
    """
    Use Mistral LLM via LangChain to batch extract all keys from narrative text in a single API call.
    Sends all keys + full text in one prompt, requests JSON array response, parses result.
    """
    try:
        from langchain_mistralai import ChatMistralAI
        from langchain.schema import HumanMessage
    except ImportError as e:
        print(f"  ERROR: langchain_mistralai not installed. Install with: pip install langchain_mistralai")
        print("  Falling back to heuristic extractor.\n")
        return extract_with_llm_mistral_mock(text, keys)
    
    api_key = os.getenv('MISTRAL_API_KEY')
    model = os.getenv('MODEL', 'mistral-small-latest')
    
    if not api_key:
        print("  ERROR: MISTRAL_API_KEY not set in .env")
        print("  Falling back to heuristic extractor.\n")
        return extract_with_llm_mistral_mock(text, keys)
    
    # Initialize LLM
    llm = ChatMistralAI(
        model=model,
        api_key=api_key,
        temperature=0.1,  # Low temperature for deterministic extraction
        max_tokens=8000
    )
    
    # Build batch extraction prompt
    keys_formatted = '\n'.join([f"- {key}" for key in keys])
    
    prompt = f"""Extract information from the following text and provide structured output.

For EACH key in the list below, find the corresponding value in the text.
- If a key is found, extract the exact value from the text (do NOT paraphrase or hallucinate).
- If a key is NOT found or not mentioned, set the value to an empty string "".
- Add a brief comment explaining where the value came from or why it's empty.

Keys to extract:
{keys_formatted}

Text to extract from:
---
{text}
---

Return ONLY a valid JSON array with NO preamble or explanation. Each element should have "key", "value", and "comment" fields.
Example format (return EXACTLY like this, as pure JSON):
[
  {{"key": "First Name", "value": "John", "comment": "Found in first line"}},
  {{"key": "Age", "value": "", "comment": "Not mentioned in text"}},
  ...
]
"""
    
    print("  Sending batch extraction request to Mistral LLM...")
    print(f"  Total keys: {len(keys)}")
    
    try:
        # Single API call with all keys at once
        message = HumanMessage(content=prompt)
        
        # Wait 2 seconds before sending to avoid throttling
        print("  Waiting 2 seconds before API call...")
        time.sleep(2)
        
        # Retry logic with exponential backoff
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                response = llm.invoke([message])
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"  Attempt {attempt + 1} failed, retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # exponential backoff
                else:
                    raise
        
        # Extract JSON from response
        response_text = response.content
        print(f"  LLM Response length: {len(response_text)} chars")
        
        # Parse JSON from response
        # Try to extract JSON array from the response
        import re
        json_match = re.search(r'\[[\s\S]*\]', response_text)
        if not json_match:
            print("  ERROR: No JSON array found in LLM response")
            print("  Falling back to heuristic extractor.\n")
            return extract_with_llm_mistral_mock(text, keys)
        
        json_str = json_match.group(0)
        rows = json.loads(json_str)
        
        # Validate structure
        if not isinstance(rows, list):
            print("  ERROR: LLM response is not a JSON array")
            return extract_with_llm_mistral_mock(text, keys)
        
        # Ensure all rows have required fields
        for row in rows:
            if 'key' not in row:
                row['key'] = ''
            if 'value' not in row:
                row['value'] = ''
            if 'comment' not in row:
                row['comment'] = ''
        
        print(f"  Successfully extracted {len(rows)} rows via LLM batch call.\n")
        return rows
        
    except json.JSONDecodeError as e:
        print(f"  ERROR parsing JSON from LLM response: {e}")
        print("  Falling back to heuristic extractor.\n")
        return extract_with_llm_mistral_mock(text, keys)
    except Exception as e:
        print(f"  ERROR during LLM extraction: {e}")
        print("  Falling back to heuristic extractor.\n")
        return extract_with_llm_mistral_mock(text, keys)


def extract_with_llm_mistral_mock(text: str, keys: List[str]) -> List[Dict[str, str]]:
    """
    Fallback heuristic extractor (uses simple text matching).
    Used when Mistral API is unavailable or for testing.
    """
    rows = []
    
    # Simple heuristic: look for key patterns in text
    lines = text.lower().split('\n')
    
    for i, key in enumerate(keys):
        if not key.strip():
            continue
        
        value = ''
        comment = ''
        
        # Try to find the key in text (case-insensitive search)
        key_lower = key.strip().lower()
        for j, line in enumerate(lines):
            if key_lower in line:
                # Found a line containing the key. Extract value heuristically.
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        value = parts[1].strip()[:200]
                elif j + 1 < len(lines):
                    # Value might be on next line
                    value = lines[j+1].strip()[:200]
                comment = 'heuristic match'
                break
        
        rows.append({'key': key, 'value': value, 'comment': comment})
        
        if (i + 1) % 10 == 0:
            print(f"  [{i+1}/{len(keys)}] Processed {i+1} keys...")
    
    return rows


def extract_with_llm_mistral(text: str, keys: List[str] = None) -> List[Dict[str, str]]:
    """
    Use Mistral LLM via LangChain to extract values for a list of keys from narrative text.
    
    If keys is None, dynamically detects schema from text first.
    Batch approach: sends all keys + full text in ONE API call requesting JSON response.
    Falls back to mock if API unavailable or on error.
    """
    # Dynamic schema detection if keys not provided
    if keys is None or len(keys) == 0:
        from pipeline.schema_detector import get_dynamic_schema
        keys = get_dynamic_schema(text)
        if not keys:
            print("  WARNING: Failed to detect schema, using empty schema")
            return []
    
    return extract_with_llm_mistral_batch(text, keys)


def load_gold_schema(excel_path: str = 'Expected Output.xlsx') -> List[str]:
    """Extract expected keys from gold standard Excel."""
    import pandas as pd
    try:
        df = pd.read_excel(excel_path, header=0)
        
        # Find the 'Key' column (case-insensitive)
        key_col = None
        for col in df.columns:
            if 'key' in str(col).lower():
                key_col = col
                break
        
        if key_col is None:
            # If no 'Key' column found, use the second column (index 1)
            key_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
        
        keys = df[key_col].dropna().tolist()
        return [str(k).strip() for k in keys if k and str(k).strip() and str(k).strip() not in ['#', 'Key']]
    except Exception as e:
        print(f'Error reading gold schema: {e}')
        return []


if __name__ == '__main__':
    import sys
    
    # Load schema
    keys = load_gold_schema()
    print(f'Loaded {len(keys)} keys from Expected Output.')
    
    # Load text
    if len(sys.argv) < 2:
        print('Usage: python llm_extractor.py <text_file or pdf>')
        raise SystemExit(1)
    
    input_file = sys.argv[1]
    if input_file.endswith('.pdf'):
        from pypdf import PdfReader
        reader = PdfReader(input_file)
        text = '\n'.join([page.extract_text() or '' for page in reader.pages])
    else:
        text = Path(input_file).read_text(encoding='utf-8')
    
    print(f'Extracting {len(keys)} fields from text...')
    rows = extract_with_llm_mistral(text, keys)
    
    # Print results
    print(f'\nExtracted {len(rows)} rows.')
    print(json.dumps(rows[:10], indent=2, ensure_ascii=False))
    
    # Save results
    out_json = Path(input_file).with_stem('extracted_llm').with_suffix('.json')
    out_json.write_text(json.dumps(rows, indent=2, ensure_ascii=False))
    print(f'Saved to {out_json}')
