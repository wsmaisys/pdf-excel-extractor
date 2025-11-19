"""
BLEU score evaluation for extraction consistency and quality.
Measures how well extracted values match expected content semantically.
"""

import json
from typing import List, Dict
from collections import Counter
import math
import difflib


def bleu_score(reference: str, hypothesis: str, n_gram_max: int = 4, weights: List[float] = None, smoothing: float = 1e-9, preserve_case: bool = False) -> float:
    """
    Calculate BLEU score between reference and hypothesis text.
    
    Args:
        reference: Gold standard / expected value
        hypothesis: Extracted value
        n_gram_max: Maximum n-gram size (typically 4 for BLEU-4)
    
    Returns:
        BLEU score between 0 and 1 (1 = perfect match)
    """
    if reference is None or hypothesis is None:
        if not reference and not hypothesis:
            return 1.0
        return 0.0
    
    # Normalize text
    # Optionally preserve case for strict comparisons (assignment requires
    # preserving original wording). By default we lowercase to be tolerant.
    if preserve_case:
        comp_ref = reference.strip()
        comp_hyp = hypothesis.strip()
    else:
        comp_ref = reference.lower().strip()
        comp_hyp = hypothesis.lower().strip()

    # Exact-match shortcut (very strict): if texts are identical, return perfect score
    if comp_ref == comp_hyp:
        return 1.0

    ref = comp_ref.split()
    hyp = comp_hyp.split()
    
    if len(ref) == 0 or len(hyp) == 0:
        return 0.0
    
    # Calculate n-gram precision scores
    scores = []
    
    max_n = min(n_gram_max, len(ref), len(hyp))
    for n in range(1, max_n + 1):
        # Get n-grams
        ref_ngrams = Counter([tuple(ref[i:i+n]) for i in range(len(ref) - n + 1)])
        hyp_ngrams = Counter([tuple(hyp[i:i+n]) for i in range(len(hyp) - n + 1)])
        
        # Count matches
        matches = sum((hyp_ngrams & ref_ngrams).values())
        total_hyp = sum(hyp_ngrams.values())
        
        # Precision for this n-gram (smoothed)
        precision = (matches / total_hyp) if total_hyp > 0 else 0.0
        # apply smoothing to avoid zero precisions which zero out geometric mean
        precision = precision if precision > 0.0 else smoothing
        scores.append(precision)
    
    # Geometric mean of precision scores using optional weights
    if not scores:
        geometric_mean = 0.0
    else:
        # default: uniform weights across available n-grams
        if weights is None:
            w = [1.0 / len(scores)] * len(scores)
        else:
            # normalize provided weights to the available n-grams length
            w_raw = weights[:len(scores)]
            s_w = sum(w_raw)
            w = [x / s_w for x in w_raw] if s_w > 0 else [1.0 / len(scores)] * len(scores)

        log_scores = [math.log(s) for s in scores]
        weighted_log_sum = sum(wi * ls for wi, ls in zip(w, log_scores))
        geometric_mean = math.exp(weighted_log_sum)
    
    # Brevity penalty (penalize if hypothesis is too short)
    if len(hyp) == 0:
        brevity_penalty = 0.0
    elif len(hyp) < len(ref):
        brevity_penalty = math.exp(1 - len(ref) / len(hyp))
    else:
        brevity_penalty = 1.0
    
    bleu = brevity_penalty * geometric_mean
    return max(0.0, min(1.0, bleu))  # Clamp to [0, 1]


def evaluate_extraction_quality(extracted: List[Dict[str, str]], gold: List[Dict[str, str]] = None) -> Dict:
    """
    Evaluate extraction quality using BLEU scores and consistency metrics.
    
    Args:
        extracted: Extracted key-value pairs from LLM
        gold: Optional gold standard for comparison
    
    Returns:
        Dictionary with evaluation metrics including BLEU scores
    """
    scores = []
    field_scores = {}
    non_empty_count = 0
    seq_scores = []
    insertion_ratios = []
    
    if gold:
        # Compare with gold standard
        gold_dict = {row['key']: row['value'] for row in gold if row.get('value')}
        
        for row in extracted:
            key = row.get('key', '')
            value = row.get('value', '')
            
            if key in gold_dict:
                ref = gold_dict[key]
                # Use stricter BLEU weighting (favor higher-order n-grams) and
                # preserve case to enforce original wording where required.
                score = bleu_score(ref, value, n_gram_max=4, weights=[0.05,0.15,0.4,0.4], preserve_case=True)
                # sequence similarity ratio (character sequence) - helps detect paraphrase vs reorder
                seq_ratio = difflib.SequenceMatcher(None, ref, value).ratio()
                # compute insertion/extra-token ratio: tokens in hyp not accounted in ref
                ref_tokens = Counter(ref.lower().split())
                hyp_tokens = Counter(value.lower().split())
                extra = 0
                for t, c in (hyp_tokens - ref_tokens).items():
                    extra += c
                insertion_ratio = (extra / sum(hyp_tokens.values())) if sum(hyp_tokens.values())>0 else 0.0

                scores.append(score)
                seq_scores.append(seq_ratio)
                insertion_ratios.append(insertion_ratio)

                field_scores[key] = {
                    'bleu': score,
                    'seq_ratio': seq_ratio,
                    'insertion_ratio': insertion_ratio,
                    'exact_match': (ref == value),
                    'extracted': value,
                    'gold': ref
                }
                if value:
                    non_empty_count += 1
    else:
        # Self-consistency check: non-empty values are good
        for row in extracted:
            key = row.get('key', '')
            value = row.get('value', '')
            
            if value:
                score = 1.0  # Non-empty extraction (no gold available)
                non_empty_count += 1
            else:
                score = 0.0
            
            scores.append(score)
            field_scores[key] = {'bleu': None, 'seq_ratio': None, 'insertion_ratio': None, 'exact_match': (value is not None and value != ''), 'extracted': value}
    
    # Calculate aggregate metrics
    total_fields = len(extracted)

    if gold:
        if scores:
            avg_bleu = sum(scores) / len(scores)
            max_bleu = max(scores)
            min_bleu = min(scores)
        else:
            avg_bleu = max_bleu = min_bleu = 0.0
    else:
        # When no gold is provided we cannot compute a true BLEU score.
        # Previously this branch assigned 1.0 for any non-empty field which
        # made `avg_bleu` equal to `coverage`. Instead, set BLEU values to None
        # to avoid misleadingly high BLEU numbers when no reference is available.
        avg_bleu = None
        max_bleu = None
        min_bleu = None

    # Coverage is percentage of fields that have a non-empty extracted value
    coverage = (non_empty_count / total_fields) if total_fields > 0 else 0.0
    
    return {
        'avg_bleu': avg_bleu,
        'max_bleu': max_bleu,
        'min_bleu': min_bleu,
        'coverage': coverage,  # % of fields extracted with values
        'total_fields': len(extracted),
        'non_empty_fields': non_empty_count,
        'field_scores': field_scores,
        'timestamp': __import__('datetime').datetime.now().isoformat()
    }


def format_confidence_score(eval_result: Dict) -> str:
    """
    Format evaluation results as a readable confidence/quality score string.
    
    Returns:
        String representation of confidence with emoji and percentage
    """
    avg_bleu = eval_result.get('avg_bleu', None)
    coverage = eval_result.get('coverage', 0.0)

    # If BLEU is not available (no gold/reference), use coverage as the confidence proxy.
    if avg_bleu is None:
        confidence = coverage
    else:
        # Confidence is average of BLEU score and coverage
        confidence = (avg_bleu + coverage) / 2
    
    # Emoji based on confidence level
    if confidence >= 0.85:
        emoji = "🟢"
    elif confidence >= 0.70:
        emoji = "🟡"
    else:
        emoji = "🔴"
    
    bleu_text = "N/A" if avg_bleu is None else f"{avg_bleu*100:.1f}%"
    return f"{emoji} Confidence: {confidence*100:.1f}% | BLEU: {bleu_text} | Coverage: {coverage*100:.1f}%"


if __name__ == '__main__':
    # Test BLEU scoring
    test_cases = [
        ("Vijay Kumar", "Vijay Kumar", 1.0),  # Perfect match
        ("March 15, 1989", "15 March 1989", None),  # Similar but different order
        ("IIT Delhi", "Delhi IIT", None),  # Different order
        ("", "", 1.0),  # Both empty
        ("Senior Data Engineer", "Data Engineer", None),  # Partial match
    ]
    
    print("BLEU Score Tests:")
    print("-" * 60)
    
    for ref, hyp, expected in test_cases:
        score = bleu_score(ref, hyp)
        status = "✓" if expected is None or abs(score - expected) < 0.01 else "✗"
        print(f"{status} Ref: '{ref}' | Hyp: '{hyp}' | BLEU: {score:.3f}")
