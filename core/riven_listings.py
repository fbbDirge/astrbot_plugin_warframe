"""Select five exact-match buyouts, preserving values and mod rank for display."""
import math


def select(auctions, slug, positive, negative):
    valid={}
    for a in auctions:
        if not isinstance(a,dict) or a.get('visible') is not True or a.get('closed') is not False:continue
        item=a.get('item')
        if not isinstance(item,dict) or item.get('weapon_url_name')!=slug:continue
        attrs=item.get('attributes')
        if not isinstance(attrs,list) or len(attrs)!=len(positive)+len(negative):continue
        if any(not isinstance(at,dict) or not isinstance(at.get('url_name'),str) or type(at.get('positive'))!=bool for at in attrs):continue
        p={at['url_name'] for at in attrs if at['positive']}
        n={at['url_name'] for at in attrs if not at['positive']}
        if p!=set(positive) or n!=set(negative):continue
        price=a.get('buyout_price');aid=a.get('id')
        if not isinstance(aid,str) or not aid:continue
        if type(price) not in (int,float) or not math.isfinite(price) or price<=0:continue
        valid.setdefault(aid,a)
    return sorted(valid.values(),key=lambda a:(a['buyout_price'],a['id']))[:5]
