# Put this in evaluation/ngram_inspector.py
"""
NGram Inspector

Utility to compute n-gram counts, overlap and precision between a reference
text (PDF-extracted original) and a hypothesis text (LLM-produced value).

Usage (quick):
  python -m evaluation.ngram_inspector --ref "reference text" --hyp "hypothesis text"
  python -m evaluation.ngram_inspector --ref-file ref.txt --hyp-file hyp.txt

The script prints per-n precision, top missing n-grams and top extra n-grams.
"""
from collections import Counter
from typing import List, Tuple, Dict
import argparse
import json
import re


def tokenize(text: str) -> List[str]:
    if text is None:
        return []
    # Basic tokenization: split on words and keep punctuation tokens
    tokens = re.findall(r"\w+|[^\w\s]", text.strip())
    return tokens


def ngrams(tokens: List[str], n: int) -> List[Tuple[str, ...]]:
    if n <= 0:
        return []
    return [tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]


def ngram_counts(text: str, n: int) -> Counter:
    toks = tokenize(text)
    return Counter(ngrams(toks, n))


def compare_ngrams(ref: str, hyp: str, n_max: int = 4) -> Dict:
    """Compare n-grams between ref and hyp up to n_max.

    Returns a dict with per-n statistics: matches, total_hyp, precision, missing, extra
    """
    report = {}
    for n in range(1, n_max + 1):
        ref_cnt = ngram_counts(ref, n)
        hyp_cnt = ngram_counts(hyp, n)

        # intersect counts to count matches up to clipped counts
        matches = sum((ref_cnt & hyp_cnt).values())
        total_hyp = sum(hyp_cnt.values())

        precision = (matches / total_hyp) if total_hyp > 0 else 0.0

        # missing: n-grams present in reference but not covered by hypothesis
        missing = list((ref_cnt - hyp_cnt).items())
        extra = list((hyp_cnt - ref_cnt).items())

        # sort by frequency desc
        missing_sorted = sorted(missing, key=lambda x: -x[1])[:10]
        extra_sorted = sorted(extra, key=lambda x: -x[1])[:10]

        report[n] = {
            'matches': matches,
            'total_hyp': total_hyp,
            'precision': precision,
            'distinct_ref_ngrams': len(ref_cnt),
            'distinct_hyp_ngrams': len(hyp_cnt),
            'top_missing': [ (" ".join(k), v) for k,v in missing_sorted ],
            'top_extra': [ (" ".join(k), v) for k,v in extra_sorted ],
        }

    return report


def pretty_print(report: Dict):
    print("N-gram comparison report")
    print("=" * 40)
    for n in sorted(report.keys()):
        r = report[n]
        print(f"\n{n}-gram:")
        print(f"  Precision: {r['precision']:.3f} ({r['matches']} matches / {r['total_hyp']} hyp n-grams)")
        print(f"  Distinct ref n-grams: {r['distinct_ref_ngrams']} | distinct hyp n-grams: {r['distinct_hyp_ngrams']}")
        if r['top_missing']:
            print("  Top missing (in ref but not in hyp):")
            for gram, cnt in r['top_missing']:
                print(f"    - '{gram}': {cnt}")
        if r['top_extra']:
            print("  Top extra (in hyp but not in ref):")
            for gram, cnt in r['top_extra']:
                print(f"    - '{gram}': {cnt}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--ref', help='Reference text string')
    p.add_argument('--hyp', help='Hypothesis text string')
    p.add_argument('--ref-file', help='Path to reference text file')
    p.add_argument('--hyp-file', help='Path to hypothesis text file')
    p.add_argument('--n', type=int, default=4, help='Max n-gram length (default 4)')
    p.add_argument('--json', action='store_true', help='Output JSON instead of pretty text')
    args = p.parse_args()

    ref_text = None
    hyp_text = None
    if args.ref_file:
        with open(args.ref_file, 'r', encoding='utf8') as f:
            ref_text = f.read()
    elif args.ref:
        ref_text = args.ref

    if args.hyp_file:
        with open(args.hyp_file, 'r', encoding='utf8') as f:
            hyp_text = f.read()
    elif args.hyp:
        hyp_text = args.hyp

    if ref_text is None or hyp_text is None:
        p.error('Provide both reference and hypothesis via --ref/--hyp or --ref-file/--hyp-file')

    report = compare_ngrams(ref_text, hyp_text, n_max=args.n)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        pretty_print(report)


if __name__ == '__main__':
    main()