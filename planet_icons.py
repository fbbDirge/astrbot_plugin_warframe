"""Offline star-chart identities. Ambiguous node names never guess a planet."""
import json,re
from functools import lru_cache
from pathlib import Path
from .localization import translate
ROOT=Path(__file__).parent
PLANETS={}
for key,aliases in {
 'mercury':('水星','Mercury'),'venus':('金星','Venus'),'earth':('地球','Earth'),
 'mars':('火星','Mars'),'phobos':('火卫一','Phobos'),'deimos':('火卫二','Deimos','深溯池，火卫二'),
 'ceres':('谷神星','Ceres'),'jupiter':('木星','Jupiter'),'europa':('欧罗巴','Europa'),
 'saturn':('土星','Saturn'),'uranus':('天王星','Uranus'),'neptune':('海王星','Neptune'),
 'pluto':('冥王星','Pluto'),'eris':('阋神星','鬩神星','Eris'),'sedna':('赛德娜','Sedna'),
 'lua':('月球','Lua','月球 Lua'),'kuvafortress':('赤毒要塞','库瓦要塞','Kuva Fortress'),
 'void':('虚空','Void'),'zariman':('扎利曼','扎利曼号','扎里曼','扎里曼号','Zariman','Zariman Ten Zero'),
 'veil':('面纱比邻星域','面纱','Veil','Veil Proxima'),
 'hollvania':('霍瓦尼亚','Höllvania','Hollvania')}.items():
 for alias in aliases:
  PLANETS[alias.casefold()]='planet_'+key
  if key in {'earth','venus','saturn','uranus','neptune','pluto'}:
   PLANETS[(alias+(' Proxima' if alias.isascii() else '比邻星域')).casefold()]='planet_'+key
for alias in ('霍瓦尼亚','Höllvania','Hollvania'):PLANETS[alias.casefold()]='planet_earth'
PLANETS.update({'双衍王境':'cycle_duviri','duviri':'cycle_duviri','解剖圣所':'planet_deimos','羽化之穹（扎里曼）':'planet_zariman','羽化之穹（扎利曼）':'planet_zariman'})
PLANET_ASSETS=set(PLANETS.values())

@lru_cache(maxsize=1)
def nodes():
    candidates={}
    def add(name,icon):
        if name and icon:candidates.setdefault(str(name).strip().casefold(),set()).add(icon)
    zh=json.loads((ROOT/'core/data/de/nodes_zh.json').read_text())
    en=json.loads((ROOT/'core/data/de/solNodes.json').read_text())
    for key,row in zh.items():
        icon=PLANETS.get(row.get('system','').casefold())
        add(key,icon);add(row.get('name'),icon)
        raw=en.get(key,{}).get('value','')
        match=re.fullmatch(r'(.+?)\s*\(([^()]+)\)',raw)
        if match:
            # Use the node's own system record; do not infer faction from it.
            icon=icon or PLANETS.get(match[2].casefold())
            add(key,icon);add(raw,icon);add(match[1],icon);add(translate(match[1]),icon)
    return {name:next(iter(icons)) for name,icons in candidates.items() if len(icons)==1}

def planet_icon(value):
    text=str(value).strip()
    if not text or 'http' in text or text.startswith('/w '):return ''
    key=text.casefold()
    if key in PLANETS:return PLANETS[key]
    relay=re.fullmatch(r'(.+?)(?:中继站|中继)',text)
    if relay and relay[1].casefold() in PLANETS:return PLANETS[relay[1].casefold()]
    # Parenthesized planet in a full node/summary string is explicit source data.
    icons={PLANETS[p.strip().casefold()] for p in re.findall(r'[（(]([^()（）]+)[）)]',text) if p.strip().casefold() in PLANETS}
    if len(icons)==1:return next(iter(icons))
    if len(icons)>1:return ''
    return nodes().get(key,'')
