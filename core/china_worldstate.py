"""WeGame public worldstate page adapter, isolated from international data.

Request contract follows the public page's JavaScript:
https://www.wegame.com.cn/act/xjzj/xjzj20220330/index.html
"""
import hashlib
import time
import uuid
from datetime import datetime, timezone

PAGE = 'https://www.wegame.com.cn/act/xjzj/xjzj20220330/index.html'
PATH = 'xjzj/xjzj20220330/index/ajax_get_worldState'
URL = 'https://www.wegame.com.cn/api/act/index.php/' + PATH
SUPPORTED = frozenset({'help','status','cetus','bounty','fissures','sortie','archon',
    'voidtrader','dailydeals','alerts','invasions','nightwave','construction',
    'voidstorms','events','conclave','flashsales'})
BOOLS = {'active','expired','isDay','isWarm','isCetus','isStorm','isHard','completed',
         'isDaily','isElite','daily','nightmare','isPersonal','vsInfestation','archwingRequired','isSharkwing','isOpen'}
NUMBERS = {'tierNum','credits','count','quantity','minEnemyLevel','maxEnemyLevel',
           'reputation','amount','season','phase','completion','requiredRuns','cost','ducats','platinum','salePrice','originalPrice','discount',
           'remaining','total','progress','standing','masteryReq','enemyLevel'}


def request_url():
    query = f'uuid={uuid.uuid4()}&version=2&appid=10003&t={round(time.time())}'
    # Public request checksum used by the official web client, not an account key.
    digest = hashlib.md5(('/'+PATH+'?'+query+'&appkey=2020#$wegame!act$#v2').encode()).hexdigest()
    return URL+'?'+query+'&sign='+digest


def validate(payload):
    from .api_client import WarframeAPIError
    if not isinstance(payload, dict) or str(payload.get('status')) != '1' or not isinstance(payload.get('data'), dict):
        raise WarframeAPIError('国服 WeGame 世界状态暂不可用，请稍后重试（不会使用国际服数据替代）')
    try:
        stamp = datetime.fromisoformat(payload['data']['timestamp'].replace('Z','+00:00'))
        age = (datetime.now(timezone.utc)-stamp).total_seconds()
        if not -300 <= age <= 1800:
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        raise WarframeAPIError('国服世界状态时间缺失或已过期，请稍后重试') from None


def normalize(value, key=''):
    if isinstance(value,list): return [normalize(v) for v in value]
    if isinstance(value,dict):
        result={k:normalize(v,k) for k,v in value.items()}
        if result.get('enemyKey'):result['enemy']=result['enemyKey']
        if str(result.get('tierNum','')).startswith('VoidT'):
            from .de_worldstate import fissure_tier
            result['tier'],result['tierNum']=fissure_tier(result['tierNum'])
        if result.get('factionKey'):result['faction']=result['factionKey']
        for side,field in [('attacker','attackingFaction'),('defender','defendingFaction')]:
            if isinstance(result.get(side),dict) and result[side].get('factionKey'):
                result[field]=result[side]['factionKey']
        if str(result.get('node','')).startswith('SolNode'):
            from . import de_worldstate as ws
            code=result['node']
            result['node']=ws._node_name(code)
            node_info=(ws._load('solNodes.json') or {}).get(code,{})
            if str(result.get('enemy','')).startswith('SolNode'):
                result['enemy']='未知（国服源未提供）'
            if result.get('missionType')=='Corruption' and node_info.get('type')=='Void Flood':
                result['missionType']='虚空洪流'
        if result.get('tierNum') in (1,2,3,4,5,6):
            result['tier']={1:'Lith',2:'Meso',3:'Neo',4:'Axi',5:'Requiem',6:'Omnia'}[result['tierNum']]
        if result.get('syndicateKey'):result['syndicate']=result['syndicateKey']
        return result
    if isinstance(value,str):
        if key in BOOLS and value in ('','0','1','true','false'):
            return value in ('1','true')
        if key in NUMBERS:
            try:return float(value) if '.' in value else int(value)
            except ValueError:pass
    return value


def adapt_bundle(data):
    from . import de_worldstate as ws
    bundle=normalize(data)
    hunt=bundle.get('archonHunt')
    if isinstance(hunt,dict):
        hunt['variants']=[dict(m,missionType=m.get('type','')) for m in hunt.get('missions',[])]
        if str(hunt.get('faction','')).startswith('SORTIE_BOSS_'):
            hunt['faction']='未知（国服源未提供）'
        hunt['bossCode']=ws.archon_code(hunt.get('boss',''))
        hunt['boss']=ws.archon_name(hunt.get('boss',''))
    storms=bundle.get('voidStorms')
    if isinstance(storms,list) and any('Node' in s for s in storms):
        bundle['voidStorms']=ws._parse_void_storms({'VoidStorms':storms},int(time.time()*1000))
    for c in bundle.get('conclaveChallenges',[]):
        c.update(cat='每日' if c.get('daily') else '每周',text=c.get('description') or c.get('title','未命名挑战'),value=c.get('amount'))
    for sale in bundle.get('flashSales',[]):
        sale.update(name=sale.get('item','未命名礼包'),end=sale.get('expiry',''))
    for event in bundle.get('events',[]):
        rewards=[]
        for reward in event.get('rewards',[]):
            if isinstance(reward,dict):
                rewards.extend(reward.get('items',[]))
                rewards.extend(f"{r.get('type','未知物品')} ×{r.get('count',1)}" for r in reward.get('countedItems',[]))
                if reward.get('credits'):rewards.append(f"{reward['credits']} 星币")
            else:rewards.append(str(reward))
        event.update(name=event.get('description') or event.get('tooltip') or '未命名活动',rewards=rewards)
    construction=bundle.get('constructionProgress')
    if isinstance(construction,dict):
        progress=[construction.get(k,0) for k in ('fomorianProgress','razorbackProgress','unknownProgress')]
        bundle['constructionProgress']=ws._parse_construction({'ProjectPct':progress})
        bundle['constructionProgress']['assaults_unknown']=True
    return bundle


async def endpoint(client, name):
    from .api_client import WarframeAPIError, WorldstateRows
    payload=await client._fetch_json(request_url(),ttl=45,cache_key='wegame:cn:worldstate:v1',
        headers={'Referer':PAGE,'X-Requested-With':'XMLHttpRequest'},retries=0,
        validator=validate, json_encoding="gb18030")
    bundle=adapt_bundle(payload['data'])
    name={'goals':'events'}.get(name,name)
    if name not in bundle:
        raise WarframeAPIError(f'国服世界状态未提供「{name}」，暂不支持此查询')
    value=bundle[name]
    source='WeGame 国服世界状态 · 数据时间 '+bundle['timestamp']
    if isinstance(value,dict):value=dict(value,_source=source)
    elif isinstance(value,list):
        value=WorldstateRows(value);value.source=source
    return value


def command_error(command, content=()):
    if command not in SUPPORTED:
        if command in {'wm','wr','rm','xh','reroll','rank','trend','ducats'}:
            return 'WM 为国际服市场，未接入国服交易数据。查询国际服报价请显式加 -pc。'
        return '此功能尚未验证国服数据，暂不提供国服结果。可加 -pc 明确查询国际服。'
    if command=='voidtrader' and any(str(t).lower() in {'预测','predict'} for t in content):
        return '国服暂不支持奸商预测；发送「奸商 -cn」查询国服实际排期与库存。'
    return ''
