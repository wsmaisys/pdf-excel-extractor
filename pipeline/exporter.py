import pandas as pd
from typing import List, Dict


def json_to_excel(rows: List[Dict[str, str]], out_path: str):
    df = pd.DataFrame(rows)
    # ensure columns order
    cols = ['key', 'value', 'comment']
    for c in cols:
        if c not in df.columns:
            df[c] = ''
    df = df[cols]
    df.to_excel(out_path, index=False, engine='openpyxl')
    return out_path


if __name__ == '__main__':
    sample = [
        {'key': 'Invoice No', 'value': '12345', 'comment': 'page 1'},
        {'key': 'Date', 'value': '2025-11-19', 'comment': ''},
    ]
    print(json_to_excel(sample, 'output_test.xlsx'))
