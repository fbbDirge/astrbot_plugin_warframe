"""Public, read-only Riven listing search; v1 auctions and v2 manifests."""
import math
import re
from urllib.parse import urlencode

from .cards import Card
from .item_art import market_art
from .client import QueryError
from .naming import find_items, forms, normalized, query_form
from .world import paginate

ALIASES = {
 '暴击':'critical_chance','暴率':'critical_chance','暴击几率':'critical_chance','cc':'critical_chance',
 '暴伤':'critical_damage','cd':'critical_damage','基伤':'base_damage_/_melee_damage',
 '基础伤害':'base_damage_/_melee_damage','伤害':'base_damage_/_melee_damage','dmg':'base_damage_/_melee_damage',
 '多重':'multishot','ms':'multishot','触发率':'status_chance','触发':'status_chance',
 '攻速':'fire_rate_/_attack_speed','攻击速度':'fire_rate_/_attack_speed','射速':'fire_rate_/_attack_speed',
 '范围':'range','后坐力':'recoil','装填':'reload_speed','弹匣':'magazine_capacity',
 '弹速':'projectile_speed','弹道速度':'projectile_speed','初始连击':'channeling_damage',
 '毒':'toxin_damage','冰':'cold_damage','火':'heat_damage','电':'electric_damage',
 '病毒':'viral','腐蚀':'corrosive','辐射':'radiation','爆炸':'blast','磁力':'magnetic','毒气':'gas',
 'g歧视':'damage_vs_grineer','c歧视':'damage_vs_corpus','i歧视':'damage_vs_infested',
 '对grineer':'damage_vs_grineer','对corpus':'damage_vs_corpus','对infested':'damage_vs_infested',
}
HELP = '''WMR 紫卡交易查询
wmr 托里德：不限词条
wmr 托里德 暴击率：至少包含该正面词条
wmr 托里德 暴击率 多重：同时包含两个词条
wmr 托里德 双暴 多重 -变焦：三正词条 + 指定负面
wmr 托里德 +暴击率,多重,-变焦：逗号也可分隔
wmr 托里德 3+1：精确三个正面、一个负面
wmr 托里德 -rank=8 -2：满级，第2页
wmr 托里德 -all：包含离线卖家
wmr 词条：查看接口支持的词条名称
正面词条不加符号或加 +；负面词条加 - 或 负。
多个词条是 AND（全部满足），未指定的词条不限制。
默认只看在线/游戏中的一口价卖单，每页最多5条。
-pc/-ps/-xb/-sw 切换平台；前缀沿用个人设置。
展示公开挂单，不是成交价；不会自动私聊、购买或竞价。'''

WMR_HELP_ROWS = [
    [('wmr 托里德', 'wm_user'), ('不限词条，按一口价从低到高查询在线挂单', 'text')],
    [('wmr 托里德 暴击率 多重', 'riven_stat'), ('同时包含多个正面词条（AND 关系，未指定的不限）', 'text')],
    [('wmr 托里德 双暴 多重 -变焦', 'riven_negative'), ('三正词条 + 指定负面（负面加 - 或 负，逗号或空格分隔）', 'text')],
    [('wmr 托里德 3+1 -rank=8 -2', 'riven_range'), ('精确限制正负词条数量（2+0/2+1/3+0/3+1）、等级与页码', 'text')],
    [('wmr 托里德 -all', 'wm_quantity'), ('包含离线卖家挂单；可加 -pc / -ps / -xb / -sw 切换平台', 'text')],
    [('wmr 词条', 'title'), ('分页查看接口支持的全部紫卡属性名称与英文标识', 'text')],
]


def attr_index(attributes):
    index = {}
    for a in attributes:
        for f in forms(a): index[f] = a['slug']
        for loc in a.get('i18n',{}).values(): index[normalized(loc.get('name',''))] = a['slug']
    valid={a['slug'] for a in attributes}
    for k,v in ALIASES.items():
        if v in valid:index[normalized(k)]=v
    return index


def split_query(query,weapons):
    tokens=query.replace('，',',').replace(',', ' ').split()
    # Longest exact weapon prefix protects names such as "Dual Ichor".
    for count in range(len(tokens),0,-1):
        q=' '.join(tokens[:count]); qf=query_form(q)
        exact=[w for w in weapons if qf in forms(w)]
        if not exact and qf.endswith('prime'):
            exact=[w for w in weapons if qf[:-5] in forms(w)]
        if exact:
            return exact,' '.join(tokens[count:])
    # Fuzzy weapon search only with no trailing attributes; never drop unknown filters.
    return find_items(weapons,query),''


def parse_filters(text,attributes,weapon_type,layout=None):
    index=attr_index(attributes); by_slug={a['slug']:a for a in attributes}
    selected={}
    tokens=text.split()
    for token in tokens:
        positive=True
        if token.startswith(('-', '负')):
            positive=False;token=token[1:]
        elif token.startswith('+'): token=token[1:]
        slugs=['critical_chance','critical_damage'] if token=='双暴' and positive else [index.get(normalized(token))]
        if any(s not in by_slug for s in slugs):
            raise QueryError(f'无法识别词条：{token}。发送 wmr 词条 查看名称；多个词条用空格或逗号分隔。')
        for slug in slugs:
            a=by_slug[slug]
            if slug in selected:
                raise QueryError('词条重复或正负冲突：'+token)
            if positive and a.get('negativeOnly') or not positive and a.get('positiveOnly'):
                raise QueryError('该词条不支持指定的正负类型：'+token)
            if a.get('exclusiveTo') and weapon_type and weapon_type not in a['exclusiveTo']:
                raise QueryError('该武器类型不支持词条：'+token)
            selected[slug]=positive
    positives=sorted(k for k,v in selected.items() if v)
    negatives=sorted(k for k,v in selected.items() if not v)
    if len(positives)>3 or len(negatives)>1: raise QueryError('最多指定3个正面和1个负面词条。')
    if layout:
        p,n=map(int,layout.split('+'))
        if len(positives)>p or len(negatives)>n: raise QueryError('词条筛选与正负数量条件冲突。')
    return positives,negatives


def search_url(weapon,positives,negatives):
    params={'type':'riven','weapon_url_name':weapon,'sort_by':'price_asc','buyout_policy':'direct'}
    if positives:params['positive_stats']=','.join(positives)
    if negatives:params['negative_stats']=','.join(negatives)
    return 'https://api.warframe.market/v1/auctions/search?'+urlencode(params)


def filter_listings(rows,weapon,positives,negatives,c):
    platform={'xb1':'xbox','swi':'switch'}.get(c.platform,c.platform)
    output=[];seen=set()
    for a in rows:
        if not isinstance(a,dict):continue
        item=a.get('item') or {};owner=a.get('owner') or {};price=a.get('buyout_price')
        if (a.get('closed') or a.get('private') or not a.get('visible',False) or a.get('winner')
            or item.get('type')!='riven' or item.get('weapon_url_name')!=weapon):continue
        if a.get('platform',owner.get('platform')) != platform:continue
        if not c.include_offline and owner.get('status') not in {'online','ingame'}:continue
        if isinstance(price,bool) or not isinstance(price,(int,float)) or not math.isfinite(price) or price<=0:continue
        attrs=item.get('attributes') or []
        pos={x.get('url_name') for x in attrs if x.get('positive') is True}
        neg={x.get('url_name') for x in attrs if x.get('positive') is False}
        if not set(positives)<=pos or not set(negatives)<=neg:continue
        if c.rank is not None and item.get('mod_rank')!=c.rank:continue
        if c.riven_layout and (len(pos),len(neg))!=tuple(map(int,c.riven_layout.split('+'))):continue
        ident=a.get('id')
        if not isinstance(ident,str) or not re.fullmatch(r'[a-fA-F0-9]{24}',ident) or ident in seen:continue
        seen.add(ident);output.append(a)
    return sorted(output,key=lambda x:(x['buyout_price'],x['id']))


def label(a):
    loc=a.get('i18n',{})
    return loc.get('zh-hans',loc.get('en',{})).get('name',a.get('slug','?'))


def format_stat(stat,attributes):
    a=attributes.get(stat.get('url_name'),{})
    value=stat.get('value')
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        value_text='数值未知'
    else:
        # Preserve API sign; positive/negative is an independent property (e.g. recoil).
        suffix={'percent':'%','multiply':'×','seconds':'s'}.get(a.get('unit'),'')
        value_text=f'{value:g}{suffix}'
    polarity='正' if stat.get('positive') else '负'
    return f'{polarity} · {label(a) if a else stat.get("url_name","?")} {value_text}'


class RivenMarketService:
    def __init__(self,client):self.client=client

    async def run(self,c):
        if c.query in {'帮助','help'}:
            return Card(
                HELP,
                title='WMR · 紫卡交易搜索指南',
                columns=('指令示例', '筛选说明'),
                rows=WMR_HELP_ROWS,
                footer='默认只看在线/游戏中的一口价卖单 · 每页最多 5 条 · 展示公开挂单，不会自动私聊或购买',
            )
        attributes=await self.client.get('https://api.warframe.market/v2/riven/attributes',ttl=21600)
        by_slug={a['slug']:a for a in attributes}
        if c.query=='词条':
            text = 'WMR 可用词条\n'+paginate([label(a)+' ('+a['slug']+')'+(' · 仅正面' if a.get('positiveOnly') else ' · 仅负面' if a.get('negativeOnly') else '') for a in attributes],c.page,12)
            pages = (len(attributes) + 11) // 12
            rows = [
                [
                    (label(a), 'riven_stat'),
                    (a['slug'], 'fissure_map'),
                    ('仅正面' if a.get('positiveOnly') else '仅负面' if a.get('negativeOnly') else '正负均可',
                     'riven_negative' if a.get('negativeOnly') else 'muted'),
                ]
                for a in attributes[(c.page-1)*12:c.page*12]
            ]
            return Card(
                text,
                title='WMR · 可用紫卡词条',
                columns=('中文名称', '接口标识 (Slug)', '正负限制'),
                rows=rows,
                footer=f'第 {c.page}/{pages} 页 · 共 {len(attributes)} 条 · 使用 wmr 词条 -2 翻页',
            )
        weapons=await self.client.get('https://api.warframe.market/v2/riven/weapons',ttl=21600)
        matches,filter_text=split_query(c.query,weapons)
        if not matches:
            raise QueryError('未找到紫卡武器。请使用完整中文/英文武器名，词条用空格分开，例如 wmr 托里德 暴击率 多重。')
        if len(matches)>1:
            text = '多个武器匹配，请使用完整名重新查询：\n'+paginate([label(w)+' ('+w['slug']+')' for w in matches],c.page,10)
            pages = (len(matches) + 9) // 10
            rows = [
                [(label(w), 'title'), (w['slug'], 'wm_user'), ('请使用完整名查询', 'muted')]
                for w in matches[(c.page-1)*10:c.page*10]
            ]
            return Card(
                text,
                title=f'{c.query} · WMR 候选武器',
                columns=('武器名称', '市场标识 (Slug)', '查询提示'),
                rows=rows,
                footer=f'第 {c.page}/{pages} 页 · 共 {len(matches)} 条 · 请使用完整武器名重新查询',
            )
        weapon=matches[0]
        positives,negatives=parse_filters(filter_text,attributes,weapon.get('rivenType'),c.riven_layout)
        url=search_url(weapon['slug'],positives,negatives)
        payload=await self.client.get(url,platform=c.platform,ttl=60)
        if not isinstance(payload,dict) or not isinstance(payload.get('auctions'),list):raise QueryError('紫卡市场返回格式异常，请稍后重试。')
        raw=payload['auctions'];orders=filter_listings(raw,weapon['slug'],positives,negatives,c)
        conditions=['+'+label(by_slug[s]) for s in positives]+['负'+label(by_slug[s]) for s in negatives]
        if c.riven_layout:conditions.append(c.riven_layout)
        if c.rank is not None:conditions.append(f'等级 {c.rank}')
        condition='、'.join(conditions) or '不限词条'
        scope=f'本次接口返回 {len(raw)} 条，筛选后 {len(orders)} 条；不代表全部挂单或全市场最低价。'
        title=f'{label(weapon)} · WMR · {c.platform.upper()}'
        if not orders:
            text = title+'\n筛选：'+condition+'\n本次返回中无符合条件的一口价。\n'+scope+'\n可尝试 -all 包含离线卖家，或减少筛选条件。'
            return Card(
                text,
                title=title,
                columns=('筛选条件', '查询结果'),
                rows=[[(condition, 'riven_stat'), ('本次返回中无符合条件的一口价。\n可尝试 -all 包含离线卖家，或减少筛选条件。', 'text')]],
                footer=scope,
            )
        pages=(len(orders)+4)//5
        if c.page>pages:raise QueryError(f'当前结果只有 {pages} 页，请缩小页码。')
        rows=[]
        for a in orders[(c.page-1)*5:c.page*5]:
            i=a['item'];o=a['owner']
            status={'ingame':'游戏中','online':'在线','offline':'离线','invisible':'离线'}.get(o.get('status'),'未知')
            attr_text='\n'.join(format_stat(x,by_slug) for x in i.get('attributes',[]))
            details=f"循环 {i.get('re_rolls','?')}\n等级 {i.get('mod_rank','?')}/8\nMR {i.get('mastery_level','?')}"
            rows.append([(o.get('ingame_name') or o.get('slug','?'), 'wm_user'),(f"{a['buyout_price']:g} 白金\n{status}",'wm_price'),(attr_text,'riven_stat'),(details,'muted')])
        links='\n'.join(f"{n}. https://warframe.market/auction/{a['id']}" for n,a in enumerate(orders[(c.page-1)*5:c.page*5],(c.page-1)*5+1))
        footer='筛选：'+condition+f" · {'含离线' if c.include_offline else '仅在线'}\n第 {c.page}/{pages} 页 · 一口价升序 · 缓存最多60秒\n"+scope+'\n挂单报价非成交价，购买前核对详情（图片链接需手动打开）：\n'+links
        return Card(title,title=title,columns=('卖家','一口价 / 状态','完整词条','卡片信息'),rows=rows,footer=footer,artwork=market_art(weapon))
