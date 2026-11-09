"""Numerical roll quality, independent of market value and build preference."""
import math


def grade(score):
    return next(label for cutoff, label in [(90,'S'),(75,'A'),(50,'B'),(25,'C'),(0,'D')] if score >= cutoff)


def quality(value, lo, hi, negative=False):
    if lo is None or hi is None or hi <= lo or not all(math.isfinite(x) for x in (value, lo, hi)):
        return None
    # Card values are rounded to one decimal; do not grade incompatible old rolls.
    if value < lo - .051 or value > hi + .051:
        return None
    position = max(0.0, min(100.0, 100 * (value-lo)/(hi-lo)))
    return 100-position if negative else position


def label(score):
    if score is None:
        return '待核对'
    score = round(score, 1)
    return f'{grade(score)} {score:g}分'
