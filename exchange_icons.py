"""Shared reward/currency matching for rotations, vendors and event prizes."""
import re
from .bounty_art import bounty_icon
from .reward_icons import reward_icon

def item_icon(text):
    text=str(text).strip().lstrip('★▣')
    text=re.sub(r'⟦[^⟧]*⟧','',text)
    text=re.sub(r'^\d[\d,]*\s*[×x]\s*','',text)
    base=re.split(r'[（(]|\s+·\s+',text,1)[0].strip()
    base=re.sub(r'\s*[×x]\s*[\d,]+$','',base)
    from .weapon_art import exact_weapon
    from .equipment_art import exact_equipment
    from .component_art import component_icon
    weapon=exact_weapon(base);equipment=exact_equipment(base)
    key=('weapon:'+weapon) if weapon else ('equipment:'+equipment if equipment else '')
    if re.search(r'蓝图|blueprint',base,re.I):
        component=component_icon(base)
        if component.startswith('blueprint:'):return component
        if key:return key
    if key:return key
    if base in {'御品阿耶','御品阿耶精华','Regal Aya'}:return 'regal_aya'
    icon=reward_icon(base) or bounty_icon(base)
    if icon:return icon
    icon=component_icon(base)
    if icon:return icon
    m=re.match(r'^(古纪|前纪|中纪|后纪|安魂|Lith|Meso|Neo|Axi|Requiem)\s*.*(?:遗物|Relic)',base,re.I)
    if m:return {'古纪':'lith','前纪':'meso','中纪':'neo','后纪':'axi','安魂':'requiem'}.get(m[1],m[1].lower())
    if re.fullmatch(r'[\d,]+\s*(现金|星币|Credits)',base,re.I):return 'credits'
    return ''

def category_icon(text):
    for pattern,icon in [('场景|摄影棚|Scene','scene'),('浮印|纹章|Glyph|Sigil','glyph'),('护甲|护肩|胸甲|头盔|护胫|幻纹|披饰|披风|外观|面具|Armor|Ephemera|Syandana|Skin','cosmetic'),('娃娃|茶具|装饰|雕像|雕塑|Noggle|Decoration','decoration'),('组合包|礼包|Pack|Bundle','bundle'),('曲目|音乐|Music','music')]:
        if re.search(pattern,str(text),re.I):return 'reward_category_'+icon
    return 'reward_category_item'

def currency_icon(text):
    # Only explicit amounts/currency names; never match generic narrative text.
    m=re.fullmatch(r'[\d,?.]+\s*(苦栓|精华|钢铁精华|碎块|裂罅碎块|御品阿耶|阿耶精华|腐化全息密钥|残余微粒)',str(text).strip())
    return item_icon(m[1]) if m else ''
