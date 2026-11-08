"""Display hints for currency amounts and damage-stat labels only."""
import re

ELEMENT_ICONS = {'火焰':'heat','冰冻':'cold','电击':'electricity','毒素':'toxin',
                 '爆炸':'blast','腐蚀':'corrosive','毒气':'gas','磁力':'magnetic',
                 '辐射':'radiation','病毒':'viral','冲击':'impact','穿刺':'puncture','切割':'slash'}


ELEMENT_ALIASES = dict(ELEMENT_ICONS)
for label, icon in list(ELEMENT_ICONS.items()):
    ELEMENT_ALIASES[icon] = icon
    ELEMENT_ALIASES[label+'伤害'] = icon
ELEMENT_ALIASES.update({'火伤':'heat','冰伤':'cold','电伤':'electricity','毒伤':'toxin',
                        '火':'heat','冰':'cold','电':'electricity','毒':'toxin',
                        'Tau':'tau','tau':'tau','真实':'true','真实伤害':'true','true':'true','虚空':'void','虚空伤害':'void','void':'void'})
CURRENCY_ICONS={'白金':'platinum','platinum':'platinum','星币':'credits','现金':'credits',
                '现金币':'credits','credits':'credits','杜卡德':'ducats','杜卡币':'ducats',
                'ducats':'ducats','内融核心':'endo','endo':'endo','赤毒':'kuva','kuva':'kuva'}
RESOURCE_ICONS={'Forma':'forma','福马':'forma','Forma Blueprint':'forma','福马蓝图':'forma','Moonflesh':'moonflesh','月华脯':'moonflesh','月肉（暂译）':'moonflesh'}

NUMBER = r'[+−-]?\d[\d,]*(?:\.\d+)?%?'

def line_icon(text, role='text'):
    if role in {'fissure_map','text','title'}:
        from .planet_icons import planet_icon
        planet=planet_icon(text)
        if planet:return planet
    if role in {'wm_user','fissure_map','muted'} or 'http' in text or text.lstrip().startswith('/w '):
        return ''
    from .world_icons import FACTIONS
    text=text.strip().lstrip('▲▼').strip()
    # Formatter labels use both Chinese/ASCII colons and middle-dot polarity prefixes.
    text=re.sub(r'^(?:正面|负面|正|负)\s*[·:：]\s*','',text)
    if role not in {'item_name','wm_price','wm_quantity'}:
        faction=FACTIONS.get(text.casefold())
        if faction:return faction[0]
        if role in {'riven_stat','riven_negative','damage'}:
            for short, icon in {'G伤':'grineer','C伤':'corpus','I伤':'infested','S伤':'sentient'}.items():
                if re.fullmatch(re.escape(short)+r'(?:\s*'+NUMBER+r')?',text,re.I):return icon
            for label,(icon,_) in FACTIONS.items():
                if re.fullmatch(r'(?:对\s*|vs\.?\s*)'+re.escape(label)+r'(?:\s*的?伤害)?(?:\s*'+NUMBER+r')?',text,re.I):
                    return icon
    if role in {'wm_price','wm_quantity'}:
        from .exchange_icons import currency_icon
        currency=currency_icon(text)
        if currency:return currency
    if role=='item_name':
        from .exchange_icons import item_icon
        item=item_icon(text)
        if item:return item
        from .bounty_art import bounty_icon
        bounty=bounty_icon(text)
        if bounty:return bounty
        from .reward_icons import reward_icon
        reward=reward_icon(text)
        if reward:return reward
        for label,icon in RESOURCE_ICONS.items():
            if re.fullmatch(re.escape(label)+r'(?:\s*[×x]\s*'+NUMBER+r')?',text,re.I):return icon
    for label,icon in CURRENCY_ICONS.items():
        if re.search(NUMBER+r'\s*[万千]?\s*'+re.escape(label)+r'(?![a-z])',text,re.I) or re.fullmatch(re.escape(label)+r'\s*[×x:]?\s*'+NUMBER,text,re.I):
            return icon
    if role not in {'riven_stat','riven_negative','title','text','damage','fissure_type','faction'}:
        return ''
    from .stat_icons import stat_icon
    stat=stat_icon(text)
    if stat:return stat
    for label, icon in ELEMENT_ALIASES.items():
        if re.fullmatch(r'(?:[正负]面?\s*[·:]?\s*)?(?:'+NUMBER+r'\s*)?'+re.escape(label)+r'(?:伤害)?(?:\s*[:：]?\s*'+NUMBER+r')?',text,re.I):
            return icon
    return ''


def icon_lines(text, role='text'):
    """Separate parallel semantic stats so each receives its own icon and wrap width."""
    for line in str(text).split('\n'):
        if re.match(r'^\s*(?:正|负|正面|负面)\s*[·:：]', line):
            yield line
            continue
        parts=re.split(r'\s*[·/｜|、；;]\s*',line)
        if role=='item_name' and len(parts)>1:
            yield from parts
            continue
        if line_icon(line,role):
            yield line
            continue
        if len(parts)>1 and role not in {'wm_user','fissure_map','muted','item_name'} and any(line_icon(p,role) for p in parts):
            yield from parts
        else:
            yield line
