"""Descriptive asking-price associations, stratified by rank and polarity count."""
from collections import defaultdict
from statistics import median

MIN_QUOTES = 5
MIN_SELLERS = 3


def classify(rows):
    groups = defaultdict(list)
    attributes = set()
    for row in rows:
        groups[(len(row['pos']), len(row['neg']), row['rank'])].append(row)
        attributes.update((polarity, stat) for polarity in ('pos', 'neg') for stat in row[polarity])
    output = []
    for polarity, stat in sorted(attributes):
        comparisons = []
        for key, group in (groups.items() if len(rows) >= 20 and len({r['seller'] for r in rows}) >= 5 else []):
            sides = [defaultdict(list), defaultdict(list)]
            quote_counts = [0, 0]
            for row in group:
                if row['price'] is None:
                    continue
                side = int(stat in row[polarity])
                sides[side][row['seller']].append(row['price'])
                quote_counts[side] += 1
            # One seller must not appear in both arms or dominate either price median.
            overlap = set(sides[0]) & set(sides[1])
            for side in sides:
                for seller in overlap:
                    side.pop(seller, None)
            quote_counts = [sum(map(len, side.values())) for side in sides]
            if min(quote_counts) < MIN_QUOTES or min(map(len, sides)) < MIN_SELLERS:
                continue
            prices = [median(median(v) for v in side.values()) for side in sides]
            base, present = prices
            weight = min(map(len, sides))
            comparisons.append({'delta': present-base, 'pct': (present/base-1)*100,
                                'weight': weight, 'rank': key[2],
                                'cohort': f'{key[0]}正{key[1]}负',
                                'with_sellers': len(sides[1]), 'without_sellers': len(sides[0])})
        matched = [r for r in rows if stat in r[polarity]]
        result = dict(stat=stat, polarity=polarity, count=len(matched),
                      sellers=len({r['seller'] for r in matched}), comparisons=comparisons)
        if not comparisons:
            result.update(category='unknown', delta=None, pct=None)
        else:
            weight = sum(c['weight'] for c in comparisons)
            delta = sum(c['delta']*c['weight'] for c in comparisons)/weight
            pct = sum(c['pct']*c['weight'] for c in comparisons)/weight
            # Opposite effects across strata cannot be called a common recommendation.
            conflicting = any(c['pct'] >= 10 for c in comparisons) and any(c['pct'] <= -10 for c in comparisons)
            if conflicting:
                category = 'conflicting'
            elif pct <= -10:
                category = 'unfavorable'
            elif polarity == 'pos':
                category = 'positive' if pct >= 10 else 'ordinary_positive'
            else:
                category = 'negative_candidate' if pct >= 10 else 'ordinary_negative'
            result.update(category=category, delta=delta, pct=pct)
            if category == 'positive':
                result['tier'] = 'T0' if pct >= 40 else 'T1' if pct >= 20 else 'T2'
        output.append(result)
    return sorted(output, key=lambda r: (r['category'], -(r['pct'] or 0), r['stat']))
