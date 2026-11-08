"""Catalogue-driven aliases; never turn a component query into a set order."""
import re
from .market_aliases import market_alias_slug


def normalized(text):
    return re.sub(r'[\s_·・\-]+','',text).casefold()


def query_form(text):
    text = normalized(text)
    text = re.sub(r'(一套|整套|套装|全套|套)$','set',text)
    # P shorthand only at a weapon-name boundary, not the P in Plasma/Prime.
    text = re.sub(r'p(?=$|set$|蓝图|枪管|枪机|枪托|刀刃|握柄|连接器|机体|系统|头部神经光元|弓臂|弓弦|饰物|散热器|刀柄|护手)', 'prime', text)
    return text


def forms(item):
    return [query_form(item.get('slug',''))] + [query_form(v.get('name','')) for v in item.get('i18n',{}).values()]


def find_items(items, query, prefer_set=False):
    q = query_form(query)
    exact = [i for i in items if q in forms(i)]
    if exact:
        return exact
    if prefer_set:
        target = market_alias_slug(query)
        if target is not None:
            # A known nickname must never fall back to a different item.
            return [i for i in items if i.get('slug') == target]
    if prefer_set and 'prime' not in q:
        implicit = [i for i in items if any(q == f.replace('prime','') for f in forms(i))]
        if implicit:
            return implicit
    if prefer_set:
        # Match a set's full base name. If omitted, allow Prime only when unique.
        sets = [i for i in items if i.get('setRoot') or i.get('slug','').endswith('_set')]
        matches = [i for i in sets if any(q == re.sub(r'set$','',f) for f in forms(i))]
        if not matches and 'prime' not in q:
            matches = [i for i in sets if any(q == re.sub(r'primeset$','',f) for f in forms(i) if f.endswith('primeset'))]
        if matches:
            return matches
    tokens=[query_form(x) for x in query.split()]
    partial = [i for i in items if any(q in f or (len(tokens)>1 and all(t in f for t in tokens)) for f in forms(i))]
    if prefer_set and not any(s in q for s in ('蓝图','枪管','枪机','枪托','刀刃','握柄','连接器','机体','系统','神经','弓臂','弓弦','饰物','散热器','刀柄','护手','blueprint','barrel','receiver','stock','blade','handle','link','chassis','neuroptics','systems','string','grip','limb')):
        sets = [i for i in partial if i.get('setRoot') or i.get('slug','').endswith('_set')]
        if sets:
            return sets
    return partial
