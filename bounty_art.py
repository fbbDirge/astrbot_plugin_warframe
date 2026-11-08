"""Offline bounty reward identities; quantity never participates in icon lookup."""
import json,re
from functools import lru_cache
from .bundled_assets import image_path
from pathlib import Path
from .weapon_art import normalized
DIRECTORY=Path(__file__).parent/'assets/bounties'

def reward_name(value):
    value=str(value).strip().lstrip('★▣').strip()
    value=re.sub(r'^[\d,]+\s*(?:[×x]\s*)?','',value)
    return re.sub(r'\s*[×x]\s*[\d,]+$','',value).strip()

@lru_cache(maxsize=1)
def catalog():
    try:data=json.loads((DIRECTORY/'manifest.json').read_text())['items']
    except (OSError,ValueError,KeyError):return {},{}
    aliases={normalized(k):v['icon'] for k,v in data.items()}
    files={v['file'][:-4]:DIRECTORY/v['file'] for v in data.values() if re.fullmatch(r'[0-9a-f]{24}\.png',v.get('file',''))}
    return aliases,files

def bounty_icon(text):return catalog()[0].get(normalized(reward_name(text)),'')
def bounty_path(key):
    path=catalog()[1].get(key)
    return image_path(path) if path else None

def bounty_blocks(lines):
    """Keep formatter region/task boundaries and expose reward rows to the icon renderer."""
    from .presentation import table,clean
    from .cards import Card,IconText
    result=[];region='赏金';task='';pending=[]
    def info(text):
        if result:result[-1].footer+='\n'+text
        else:pending.append(text)
    from .core.render import _expand_tents_line
    for original in (part for line in lines for part in _expand_tents_line(line)):
        raw=str(original);plain=clean(raw).strip()
        if not plain:continue
        if plain.startswith('◆'):
            region=plain.lstrip('◆ ').replace('\u3000',' · ');task=''
            result.append(table('地区',['地区信息'],[[region]]))
        elif plain.startswith('▸'):
            task=plain.lstrip('▸ ').replace('｜',' · ')
            result.append(table('赏金档位',['任务信息'],[[task]]))
        elif plain.startswith('※'):
            info(plain.lstrip('※ ').replace('▣ 部件/蓝图　★ MOD','部件 / 蓝图 / MOD'))
        else:
            rotation=re.match(r'^((?:MOD|部件|债券|本轮)\s*轮换(?:（[^）]*）)?)：(.+)$',plain)
            is_rewards=raw.startswith('\u3000\u3000') and not plain.startswith(('点位：','任务：','目标：'))
            if rotation or is_rewards:
                heading=rotation[1] if rotation else ('奖励 · '+task if task else '奖励')
                values=(rotation[2] if rotation else plain).split('、')
                rows=[]
                for value in values:
                    value=value.strip().lstrip('★▣').strip()
                    if not value:continue
                    name,qty=value,'—'
                    m=re.fullmatch(r'([\d,]+)\s*[×x]\s*(.+)',value)
                    tail=re.fullmatch(r'(.+?)\s*[×x]\s*([\d,]+)',value)
                    endo=re.fullmatch(r'([\d,]+)\s+(内融核心)',value)
                    if m:qty,name=m.groups()
                    elif tail:name,qty=tail.groups()
                    elif endo:qty,name=endo.groups()
                    from .localization import translate
                    rows.append([(IconText(translate(name),bounty_icon(name)),'item_name'),(qty,'wm_quantity')])
                result.append(Card('',title=heading,columns=('奖励物品','数量'),rows=rows))
            else:info(plain)
    if pending:
        result.insert(0,table('提示',['说明'],[[v] for v in pending]))
    return result
