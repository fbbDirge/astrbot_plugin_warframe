"""Offline artwork for equipment and its explicitly named components."""
import json
import re
from functools import lru_cache
from .bundled_assets import image_path
from pathlib import Path
from .weapon_art import normalized
DIRECTORY=Path(__file__).parent/'assets/equipment'

@lru_cache(maxsize=1)
def catalog():
    try:data=json.loads((DIRECTORY/'manifest.json').read_text())
    except (OSError,ValueError):return {},{}
    aliases={};files={}
    for row in data.get('items',[]):
        filename=row.get('file','')
        if not re.fullmatch(r'[0-9a-f]{24}\.png',filename):continue
        key=filename[:-4];files[key]=DIRECTORY/filename
        for name in row.get('aliases',[]):
            alias=normalized(name)
            if alias in aliases and aliases[alias]!=key:aliases[alias]=None
            else:aliases[alias]=key
    return aliases,files

def equipment_path(key):
    path=catalog()[1].get(key)
    return image_path(path) if path else None

def exact_equipment(text):
    text=re.sub(r'⟦[^⟧]+⟧','',str(text)).strip()
    aliases,_=catalog()
    key=aliases.get(normalized(text))
    if key:return key
    # Chinese exports may append 蓝图 to an explicitly known component name.
    base=re.sub(r'\s*(?:蓝图|Blueprint)$','',text,flags=re.I).strip()
    if base!=text and re.search(r'机体|系统|头部神经光元|机翼|外甲|\b(?:chassis|systems|neuroptics|wings|harness)$',base,re.I):
        key=aliases.get(normalized(base))
        if key:return key
    # Never turn an unknown blueprint or part into a whole frame/vehicle thumbnail.
    if re.search(r'蓝图|机体|系统|头部神经光元|机翼|外甲|\b(?:blueprint|chassis|systems|neuroptics|wings|harness)\b',text,re.I):return None
    for part in re.split(r'[\n（()）｜|]',text):
        part=re.sub(r'(?:\s+set|\s*一套|\s*套装)$','',part.strip(),flags=re.I)
        key=aliases.get(normalized(part))
        if key:return key
    return None

def title_equipment(text):
    text=re.sub(r'\s+(?:在售单|收购单|价格趋势).*$', '', str(text))
    key=exact_equipment(text)
    if key:return key
    for part in re.split(r'[:：·｜|\n]',text):
        key=exact_equipment(part)
        if key:return key
    return None
