"""Read-only converted Lich/Sister listings, not completed weapon sales."""
import math
import re
from urllib.parse import urlencode
from .cards import Card
from .item_art import market_art
from .client import QueryError
from .naming import forms, normalized
from .riven_market import label
from .world import paginate

ELEMENTS = {'impact':'冲击','heat':'火焰','cold':'冰冻','electricity':'电击','toxin':'毒素','magnetic':'磁力','radiation':'辐射'}
ELEMENT_ALIASES = {v:k for k,v in ELEMENTS.items()}
ELEMENT_ALIASES.update({k:k for k in ELEMENTS})
ELEMENT_ALIASES.update({'火':'heat','冰':'cold','电':'electricity','毒':'toxin','磁':'magnetic'})
WEAPON_ALIASES = {'毒瘤':'kuva_nukor','赤毒毒瘤':'kuva_nukor','信条c喷':'tenet_arca_plasmor','c喷':'tenet_arca_plasmor'}
RULES = ('交易的是已感化的玄骸／姐妹，不是成品武器。\n'
         '双方到氏族道场绯红之厅交易；买家不能有正在追猎的玄骸／姐妹。\n'
         '买家接手后需继续追猎；想拿武器最终选择击杀。\n'
         '带幻纹者击杀或感化均可获得幻纹；每个玄骸／姐妹只能交易一次。')


def filters(query):
    weapon=[]; element=None; ephemera=None; low=25.; high=60.; damage_set=False
    for token in query.replace('，',' ').split():
        key=token.casefold()
        if key in ELEMENT_ALIASES:
            if element is not None:raise QueryError('元素只能指定一个。')
            element=ELEMENT_ALIASES[key]
        elif key in {'有幻纹','带幻纹','无幻纹','不带幻纹'}:
            if ephemera is not None:raise QueryError('有无幻纹只能指定一次。')
            ephemera=key in {'有幻纹','带幻纹'}
        elif re.fullmatch(r'\d+(?:\.\d+)?[%％]?(?:[-~～]\d+(?:\.\d+)?[%％]?)?',key):
            if damage_set:raise QueryError('伤害加成只能指定一个数值或范围。')
            values=re.split('[-~～]',key.replace('%','').replace('％',''))
            low=float(values[0]);high=float(values[1]) if len(values)>1 else 60.
            if not 25<=low<=high<=60:raise QueryError('伤害加成范围为25—60%；单个数值表示最低加成。')
            damage_set=True
        else:weapon.append(token)
    return ' '.join(weapon), element, ephemera, low, high


def match_weapons(weapons, query):
    q=normalized(query)
    if q in WEAPON_ALIASES:
        return [w for w in weapons if w['slug']==WEAPON_ALIASES[q]]
    for exact in [True,False]:
        result=[]
        for w in weapons:
            names=forms(w)
            names += [re.sub(r'^(kuva|tenet|赤毒|信条)','',n) for n in names]
            if any(q==n if exact else q in n for n in names):result.append(w)
        if result:return result
    return []


def select(rows, kind, slug, c, element, ephemera, low, high):
    selected=[];seen=set();platform={'xb1':'xbox','swi':'switch'}.get(c.platform,c.platform)
    for a in rows:
        if not isinstance(a,dict):continue
        i=a.get('item') or {};o=a.get('owner') or {};price=a.get('buyout_price');damage=i.get('damage')
        if not isinstance(i,dict) or not isinstance(o,dict):continue
        if a.get('closed') or a.get('private') or not a.get('visible',False) or a.get('winner'):continue
        if i.get('type')!=kind or i.get('weapon_url_name')!=slug:continue
        if a.get('platform',o.get('platform'))!=platform:continue
        if not c.include_offline and o.get('status') not in {'online','ingame'}:continue
        if not a.get('is_direct_sell'):continue
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in [price,damage]):continue
        if price<=0 or not low<=damage<=high:continue
        if element and i.get('element')!=element:continue
        if ephemera is not None and i.get('having_ephemera') is not ephemera:continue
        ident=a.get('id')
        if not isinstance(ident,str) or not re.fullmatch('[a-fA-F0-9]{24}',ident) or ident in seen:continue
        seen.add(ident);selected.append(a)
    return sorted(selected,key=lambda a:(a['buyout_price'],-a['item']['damage'],a['id']))


class LichMarketService:
    def __init__(self,client):self.client=client

    async def run(self,c):
        kind='sister' if c.name=='姐妹' else 'lich'
        title='帕尔沃斯姐妹' if kind=='sister' else '赤毒玄骸'
        if not c.query or c.query in {'帮助','help','交易','怎么交易'}:
            return Card(RULES,title=title+' · 交易与查询',columns=('指令示例','说明'),rows=[
                [('玄骸 布拉玛 毒 55 有幻纹','wm_user'),('毒素、至少55%、有幻纹的一口价挂单','text')],
                [('姐妹 弧电离子枪 磁力 50-60','wm_user'),('指定伤害加成范围；元素、加成、幻纹均可省略','text')],
                [('玄骸 武器 / 姐妹 武器','wm_user'),('查看当前支持的武器目录','text')],
                [('-all / -2 / -ps','wm_user'),('包含离线／翻页／平台；沿用个人前缀','text')],
                [('如何交易','title'),(RULES,'text')]],footer='查询公开挂单，不自动购买或私聊。\n资料：Warframe 官方更新26.0.7 / WARFRAME Wiki Adversary System')
        weapons=await self.client.get(f'https://api.warframe.market/v2/{kind}/weapons',ttl=21600)
        if not isinstance(weapons,list):raise QueryError('武器目录格式异常，请稍后重试。')
        if c.query=='武器':
            return title+'可交易武器对应的玄骸／姐妹\n'+paginate([label(w)+' ('+w['slug']+')' for w in weapons],c.page,10)
        query,element,ephemera,low,high=filters(c.query)
        if not query:raise QueryError('请指定武器，例如：玄骸 布拉玛 毒 55 有幻纹。')
        matches=match_weapons(weapons,query)
        if not matches:raise QueryError('未找到武器或存在无法识别的筛选条件。发送 '+c.name+' 武器 查看目录；各条件用空格分开。')
        if len(matches)>1:return '匹配多个武器，请使用完整名称：\n'+paginate([label(w)+' ('+w['slug']+')' for w in matches],c.page,10)
        weapon=matches[0];slug=weapon['slug']
        params={'type':kind,'weapon_url_name':slug,'buyout_policy':'direct','sort_by':'price_asc','damage_min':math.floor(low),'damage_max':math.ceil(high)}
        if element:params['element']=element
        if ephemera is not None:params['having_ephemera']='true' if ephemera else 'false'
        payload=await self.client.get('https://api.warframe.market/v1/auctions/search?'+urlencode(params),platform=c.platform,ttl=60)
        if not isinstance(payload,dict) or not isinstance(payload.get('auctions'),list):raise QueryError('玄骸市场返回格式异常，请稍后重试。')
        raw=payload['auctions'];orders=select(raw,kind,slug,c,element,ephemera,low,high)
        condition=f"{ELEMENTS.get(element,'不限元素')} · {low:g}—{high:g}% · "+('不限幻纹' if ephemera is None else '有幻纹' if ephemera else '无幻纹')
        scope=f'本次返回 {len(raw)} 条，符合 {len(orders)} 条；不代表全部挂单或全市场最低价。'
        title=f'{label(weapon)} · {title} · {c.platform.upper()}'
        if not orders:return title+'\n'+condition+'\n本次无符合条件的在线一口价挂单，可加 -all 包含离线。\n'+scope
        pages=(len(orders)+4)//5
        if c.page>pages:raise QueryError(f'当前只有 {pages} 页。')
        batch=orders[(c.page-1)*5:c.page*5];rows=[]
        for a in batch:
            i=a['item'];o=a['owner'];status={'ingame':'游戏中','online':'在线','offline':'离线','invisible':'离线'}.get(o.get('status'),'未知')
            eph='有幻纹' if i.get('having_ephemera') is True else '无幻纹' if i.get('having_ephemera') is False else '幻纹未知'
            rows.append([(o.get('ingame_name') or o.get('slug','?'),'wm_user'),(f"{a['buyout_price']:g} 白金\n{status}",'wm_price'),(f"{ELEMENTS.get(i.get('element'),i.get('element','未知'))} {i['damage']:g}%",'riven_stat'),(eph,'wm_quantity')])
        links='\n'.join(f"{n}. https://warframe.market/auction/{a['id']}" for n,a in enumerate(batch,1))
        return Card(title,artwork=market_art(weapon),title=title,columns=('卖家','一口价 / 状态','元素 / 加成','幻纹'),rows=rows,
                    footer=condition+f" · {'含离线' if c.include_offline else '仅在线'}\n第 {c.page}/{pages} 页 · 缓存60秒\n"+scope+'\n感化玄骸／姐妹挂单，非成品武器；成交前核对详情：\n'+links)
