import re
from typing import List, Dict


def extract_kv_from_text_block(text: str, page: int = None) -> List[Dict[str, str]]:
    """Deterministic extraction of key:value pairs from a text block.

    Returns list of dicts with keys: key, value, comment.
    - Looks for explicit 'Key: Value' lines
    - Looks for 'Key\nValue' patterns (label line then value lines)
    - Preserves exact wording
    """
    lines = text.splitlines()
    results = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # pattern 1: Key: Value
        m = re.match(r"^([^:\n]{1,200}?)\s*:\s*(.+)$", line)
        if m:
            key = m.group(1).strip()
            value = m.group(2).strip()
            comment = ''
            # include nearby context (previous and next non-empty lines)
            prev_line = next((l for l in reversed(lines[:i]) if l.strip()), '')
            next_line = next((l for l in lines[i+1:] if l.strip()), '')
            ctx = []
            if prev_line:
                ctx.append(prev_line.strip())
            if next_line:
                ctx.append(next_line.strip())
            if ctx:
                comment = ' | '.join(ctx)
            row = {'key': key, 'value': value, 'comment': comment}
            if page is not None:
                row['page'] = page
            results.append(row)
            i += 1
            continue

        # pattern 2: Label on one line, value on following lines until blank or next label
        # Heuristic: label line ends with no punctuation and is short
        if len(line) < 120 and not line.endswith(('.', '?', '!')) and ':' not in line:
            # lookahead for value lines
            j = i + 1
            value_lines = []
            while j < len(lines):
                l = lines[j]
                if not l.strip():
                    break
                # stop if next line looks like another label (contains ':') or is all-caps short
                if re.match(r"^[^:]{1,200}\s*:\s*.+$", l.strip()):
                    break
                if len(l.strip()) < 60 and l.strip().isupper():
                    break
                value_lines.append(l.rstrip('\n'))
                j += 1
            if value_lines:
                key = line
                value = '\n'.join([v.rstrip() for v in value_lines]).strip()
                comment = ''
                if i-1 >= 0 and lines[i-1].strip():
                    comment = lines[i-1].strip()
                row = {'key': key, 'value': value, 'comment': comment}
                if page is not None:
                    row['page'] = page
                results.append(row)
                i = j
                continue

        # otherwise skip
        i += 1

    return results


if __name__ == '__main__':
    sample = """
Invoice No: 12345
Date: 2025-11-19
Customer
ACME Corp
Notes: Delivery on Monday.
"""
    import json
    print(json.dumps(extract_kv_from_text_block(sample), indent=2))
