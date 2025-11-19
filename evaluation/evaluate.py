import json
from typing import List, Dict
from difflib import SequenceMatcher


def exact_match(a: str, b: str) -> bool:
    return (a or '').strip() == (b or '').strip()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a or '', b or '').ratio()


def evaluate_exact_match(gold: List[Dict], pred: List[Dict]) -> Dict:
    """Compare gold and pred lists of dicts with keys 'key' and 'value'.

    Returns report with counts and per-row diffs.
    """
    report = {'total_gold': len(gold), 'total_pred': len(pred), 'matches': 0, 'rows': []}

    # build index by key (exact match) for gold
    gold_by_key = { (g['key'] or '').strip(): g for g in gold }

    for p in pred:
        k = (p.get('key') or '').strip()
        v = p.get('value') or ''
        gold_row = gold_by_key.get(k)
        row = {'key': k, 'pred_value': v, 'gold_value': gold_row.get('value') if gold_row else None}
        if gold_row and exact_match(gold_row.get('value'), v):
            row['exact'] = True
            report['matches'] += 1
        else:
            row['exact'] = False
            row['similarity'] = similarity(gold_row.get('value') if gold_row else '', v)
        report['rows'].append(row)

    report['exact_match_rate'] = report['matches'] / max(1, report['total_gold'])
    return report


if __name__ == '__main__':
    gold = [{'key':'Invoice','value':'123'}, {'key':'Date','value':'2025-11-19'}]
    pred = [{'key':'Invoice','value':'123'}, {'key':'Date','value':'2025/11/19'}]
    import pprint
    pprint.pprint(evaluate_exact_match(gold, pred))
