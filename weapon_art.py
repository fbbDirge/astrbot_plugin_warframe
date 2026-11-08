"""Offline weapon artwork, matched by identity rather than approximate names."""
import json
import re
import unicodedata
from functools import lru_cache
from .bundled_assets import image_path
from pathlib import Path
from .cards import Card, IconText

DIRECTORY=Path(__file__).parent/'assets/weapons'

def normalized(value):
    from .localization import strip_item_tags
    value=strip_item_tags(value)
    return re.sub(r'[\s_·・\-]+','',unicodedata.normalize('NFKC',str(value))).casefold()

@lru_cache(maxsize=1)
def catalog():
    try:data=json.loads((DIRECTORY/'manifest.json').read_text())
    except (OSError,ValueError):return {},{}
    aliases={};files={}
    for row in data.get('weapons',[]):
        filename=row.get('file','')
        if not re.fullmatch(r'[0-9a-f]{24}\.png',filename):continue
        key=filename[:-4];files[key]=DIRECTORY/filename
        for name in row.get('aliases',[]):
            alias=normalized(name)
            if alias in aliases and aliases[alias]!=key:aliases[alias]=None
            else:aliases[alias]=key
    return aliases,files

def weapon_path(key):
    path=catalog()[1].get(key)
    return image_path(path) if path else None

def exact_weapon(text):
    text=re.sub(r'⟦[^⟧]+⟧','',str(text)).strip()
    if re.search(r'蓝图|枪管|枪机|枪托|刀刃|握柄|连接器|弓臂|弓弦|刀柄|护手|\b(?:blueprint|barrel|receiver|stock|blade|handle|grip|string|limb)\b',text,re.I):return None
    aliases,_=catalog()
    # Full names first; then bilingual labels and explicit set suffixes.
    parts=[text,*re.split(r'[\n（()）｜|]',text)]
    for part in parts:
        part=re.sub(r'(?:\s+set|\s*一套|\s*套装)$','',part.strip(),flags=re.I)
        key=aliases.get(normalized(part))
        if key:return key
    return None

def title_weapon(text):
    # Split known title syntax, never substring-match a base weapon inside a Prime/part name.
    text=re.sub(r'\s+(?:紫卡拍卖|紫卡词条范围|玄骸拍卖|价格趋势|在售单|收购单).*$', '', str(text))
    key=exact_weapon(text)
    if key:return key
    for part in re.split(r'[:：·｜|\n]',text):
        key=exact_weapon(part)
        if key:return key
    return None

def decorate(card):
    if not isinstance(card,Card):return
    from .equipment_art import exact_equipment, title_equipment, equipment_path
    def identify(value, title=False):
        key=(title_weapon if title else exact_weapon)(value)
        if key:return 'weapon:'+key
        key=(title_equipment if title else exact_equipment)(value)
        return 'equipment:'+key if key else None
    found=set()
    for block in (card.blocks or [card]):
        block.rows=[list(row) for row in block.rows]
        for row in block.rows:
            for i,(value,role) in enumerate(row):
                header=block.columns[i] if i<len(block.columns) else ''
                semantic=header in {'武器','武器名称','名称','物品','奖励','奖励物品','战甲','空战','机架','增幅器','滑板','部件'}
                if (not semantic and role not in {'text','title','item_name'}) or getattr(value,'icon',''):continue
                if role=='item_name':
                    from .exchange_icons import item_icon,category_icon
                    key=item_icon(value) or category_icon(value)
                    row[i]=(IconText(str(value),key),role)
                    continue
                key=identify(value)
                if (semantic or role=='item_name') and re.search(r'(?:蓝图|Blueprint)$',str(value),re.I):
                    from .component_art import component_icon
                    blueprint=component_icon(value)
                    if blueprint.startswith('blueprint:'):key=blueprint
                if not key and (semantic or role=='item_name'):
                    from .component_art import component_icon
                    key=component_icon(value)
                if key:
                    row[i]=(IconText(str(value),key),role)
                    if key.startswith(('weapon:','equipment:')):found.add(key)
        key=identify(block.title,True)
        if key:found.add(key)
    key=identify(card.title,True)
    if not key and len(found)==1:key=next(iter(found))
    # Component names are rejected above; complete weapon results can use the offline image.
    if key and not card.artwork_path:
        kind,identity=key.split(':',1)
        path=weapon_path(identity) if kind=='weapon' else equipment_path(identity)
        if path and path.is_file():card.artwork_path=path
