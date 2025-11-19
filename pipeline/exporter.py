"""Utilities to export extraction results to Excel.

The project stores extracted rows as a list of dictionaries with keys
`key`, `value`, and `comment`. This module converts that structure to a
pandas DataFrame and writes an Excel file using `openpyxl`.
"""

import pandas as pd
from typing import List, Dict


def json_to_excel(rows: List[Dict[str, str]], out_path: str):
    """Write a list of extraction rows to an Excel file.

    Args:
        rows: List of dicts where each dict contains at least 'key' and 'value'.
        out_path: Path where the Excel file will be written.

    Returns:
        The output path (string) for convenience in callers.
    """
    # Build a DataFrame and ensure expected columns exist in a stable order
    df = pd.DataFrame(rows)
    cols = ['key', 'value', 'comment']
    for c in cols:
        if c not in df.columns:
            df[c] = ''
    df = df[cols]

    # Use openpyxl engine for .xlsx output
    df.to_excel(out_path, index=False, engine='openpyxl')
    return out_path


if __name__ == '__main__':
    sample = [
        {'key': 'Invoice No', 'value': '12345', 'comment': 'page 1'},
        {'key': 'Date', 'value': '2025-11-19', 'comment': ''},
    ]
    print(json_to_excel(sample, 'output_test.xlsx'))
