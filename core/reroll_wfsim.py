"""WFSim's measured riven combinations; never attribute a build gain to one stat."""
import asyncio
import hashlib
import json
import math
import re
import time
from datetime import datetime, timezone, timedelta
from functools import lru_cache
from pathlib import Path
from . import paths
from .commands.base import Reply
from .formatters import _riven_stat_cn

ENDPOINT = 'https://mcp.wfsim.app/mcp'
TTL = 3600
_LOCKS = {}
_RATE = asyncio.Lock()
_LAST = 0.0

STAT_IDS = {
    'damage':'melee_damage', 'critical_chance':'crit_chance', 'critical_damage':'crit_damage',
    'weapon_recoil':'recoil', 'ammo_maximum':'ammo_max',
    'additional_combo_count_chance':'extra_combo_count', 'chance_to_gain_combo_count':'combo_gain_chance',
    'critical_chance_for_slide_attack':'slide_crit', 'heavy_attack_wind_up_speed':'melee_heavy_attack_charge',
    'melee_damage_on_heavy_attack':'melee_heavy_attack_damage', 'parry_angle':'melee_parry_angle',
    'reload_while_holstered':'reload_holstered', 'slam_attack_damage':'melee_slam_damage',
    'weak_point_critical_chance':'weakpoint_crit_chance', 'weak_point_damage':'weakpoint_damage',
    'electricity':'electric_damage',
}
STAT_IDS.update({x:x+'_damage' for x in ('cold','heat','toxin','blast','corrosive','gas','magnetic','radiation','viral','impact','puncture','slash')})
STAT_IDS.update({'damage_to_'+x:'damage_vs_'+x for x in ('corpus','grineer','infested','orokin','scaldra','techrot')})

@lru_cache(maxsize=1)
def mod_names():
    try:
        data=json.loads((Path(__file__).parent/'data/mods_stats.json').read_text())
        return {k.casefold():v['zh'] for k,v in data.get('mods',{}).items() if v.get('zh')}
    except (OSError,ValueError):return {}

def record_time(value):
    try:return stamp(datetime.fromisoformat(str(value).replace('Z','+00:00')).timestamp())
    except (ValueError,TypeError):return str(value or '来源未提供')

async def call(client, name, arguments, api_key=''):
    global _LAST
    headers = {'Content-Type':'application/json', 'Accept':'application/json, text/event-stream',
               'User-Agent':'AstrBot-Warframe/WFSim'}
    if api_key: headers['Authorization'] = 'Bearer '+api_key
    async with _RATE:
        await asyncio.sleep(max(0, 2.1-(time.monotonic()-_LAST)))
        _LAST = time.monotonic()
        response = await client.http.post(ENDPOINT, headers=headers, timeout=25,
            json={'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':name,'arguments':arguments}})
    response.raise_for_status()
    if 'text/event-stream' in response.headers.get('content-type',''):
        messages = [json.loads(x[5:].strip()) for x in response.text.splitlines() if x.startswith('data:')]
        envelope = next((x for x in messages if x.get('id') == 1), {})
    else: envelope = response.json()
    result = envelope.get('result', {})
    data = result.get('structuredContent')
    if data is None:
        data = next((json.loads(c['text']) for c in result.get('content',[]) if c.get('type')=='text'), None)
    if envelope.get('error') or result.get('isError') or not isinstance(data,dict) or data.get('ok') is False:
        raise ValueError('WFSim request unavailable')
    return data

def cache_path(query, ruler):
    return paths.run_dir()/'reroll_wfsim'/(hashlib.sha256((query.casefold()+'|'+ruler).encode()).hexdigest()+'.json')

def read_cache(path):
    try:
        data=json.loads(path.read_text())
        stamp=data['sampled_at']
        if data.get('schema')!=1 or not isinstance(data.get('result',{}).get('groups'),list):return None
        if not isinstance(stamp,(int,float)) or not math.isfinite(stamp) or stamp>time.time()+60:return None
        return data
    except (OSError, ValueError, KeyError, TypeError):return None

def stamp(ts):
    return datetime.fromtimestamp(ts,timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M（北京时间）')

def report(data, stale=False):
    from ..localization import translate
    result=data['result'];weapon=data.get('weapon',{})
    title=(weapon.get('zh') or data['query'])+' · 洗卡推荐'
    lines=['◆ 来源：WFSim 已模拟紫卡组合', '◆ 数据状态：'+('接口失败，历史缓存（非实时）' if stale else '已缓存模拟结果'),
           '◆ 获取时间：'+stamp(data['sampled_at'])]
    groups=result.get('groups',[])
    usable=False
    for g in groups:
        rows=g.get('rivens') or []
        if not rows:continue
        usable=True
        mode={'base':'普通','incarnon':'灵化','cycle':'普通／灵化循环'}.get(g.get('mode'),g.get('mode') or '未标注模式')
        ruler=str(g.get('ruler') or g.get('ruler_id') or '未标注场景')
        for en,zh in [('Standard Single Target','标准单体'),('Standard Multi Target','标准群体'),('100% headshots, aiming','100% 爆头、瞄准'),('Standard conditions','标准条件'),('Lv ','等级 '),(' SP',' 钢铁')]:ruler=ruler.replace(en,zh)
        lines+=['◆ 模拟场景：'+ruler,'◆ 武器模式：'+str(mode)]
        # Rankings only compare within this ruler/mode, never across different fights.
        for i,r in enumerate(rows[:5],1):
            ids=r.get('stat_ids') or {}
            pos=ids.get('bonuses') or r.get('bonuses') or []
            neg=ids.get('malus') or r.get('malus')
            label=lambda x:_riven_stat_cn(STAT_IDS.get(str(x),str(x)),weapon.get('riven_type',''),weapon.get('group',''))
            gain=r.get('gain')
            valid=isinstance(gain,(int,float)) and not isinstance(gain,bool) and math.isfinite(gain) and g.get('riven_free')
            lines+=['◆ 优选组合 '+str(i),'　项目　内容',
                    '· 正面词条　'+' / '.join('▲'+label(x) for x in pos),
                    '· 负面词条　'+('▼'+label(neg) if neg else '无'),
                    '· 配装整体提升　'+(f'{gain*100:+.1f}%' if valid else '无同场景基准，暂不计算'),
                    '· 配套 MOD　'+' / '.join(mod_names().get(str(x).casefold(),translate(x)) for x in r.get('mods',[])),
                    '· 模拟记录时间　'+record_time(r.get('measured_at'))]
        lines+=['※ 提升比较同场景、同模式的无紫卡最优配装；包含配套 MOD 变化，不是单词条收益。']
    if not usable:lines+=['◆ 暂无推荐：WFSim 尚无此武器／场景的已模拟紫卡组合，不使用 WM 价格或其他武器冒充。']
    lines+=['※ 仅覆盖已提交并计算的组合，不代表穷尽所有词条；负面需结合上述模式和配装判断。']
    return Reply(title,lines,footer='WFSim 模拟结果 · 国际服数据参考\n场景说明：https://wfsim.app/method')

async def recommend(client, query, platform='pc', api_key=''):
    query=query.strip()
    refresh=query.endswith(' 刷新');query=re.sub(r'\s+刷新$','',query)
    ruler='standard_single_target'
    if query.endswith(' 群怪'):
        ruler='standard_multi_target';query=query[:-3].strip()
    elif query.endswith(' 单体'):query=query[:-3].strip()
    if not query:return Reply('洗卡推荐',['◆ 用法：托里德 洗卡推荐；支持“群怪”“刷新”参数。'])
    path=cache_path(query,ruler)
    async with _LOCKS.setdefault(str(path),asyncio.Lock()):
        old=read_cache(path)
        if old and not refresh and time.time()-old['sampled_at']<TTL:return report(old)
        try:
            async with asyncio.timeout(60):
                weapon=None
                try:weapon=await asyncio.wait_for(client.resolve_riven_weapon(query),10)
                except Exception:pass
                lookup=(weapon or {}).get('en') or query
                found=await call(client,'builder_weapons_find',{'query':lookup,'limit':40},api_key)
                rows=found.get('rows') or []
                norm=lambda x:re.sub(r'[\s_\-]+','',str(x)).casefold()
                matches=[x for x in rows if norm(lookup) in (norm(x.get('name')),norm(x.get('id')))]
                if not matches and not weapon and len(rows)==1:matches=rows
                if len(matches)!=1:
                    return Reply('洗卡推荐 · 请指定武器',['◆ WFSim 未能唯一匹配，请使用完整名称（区分 Prime 等版本）。']+['· '+str(x.get('name')) for x in rows[:8]])
                result=await call(client,'builder_rivens_read',{'weapon':matches[0]['id'],'ruler':ruler},api_key)
                if result.get('weapon')!=matches[0]['id'] or not isinstance(result.get('groups'),list):raise ValueError('invalid result')
                data={'schema':1,'sampled_at':time.time(),'query':query,'weapon':weapon or {'zh':matches[0]['name']},'result':result}
        except Exception:
            if old:return report(old,stale=True)
            return Reply('洗卡推荐 · 暂不可用',['◆ WFSim 查询失败或暂无已发布结果，且没有此武器的缓存。请稍后重试。'])
        try:
            path.parent.mkdir(parents=True,exist_ok=True)
            tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False));tmp.replace(path)
        except OSError:
            reply=report(data);reply.lines.append('※ 缓存写入失败，本次结果仍可使用。');return reply
        return report(data)
