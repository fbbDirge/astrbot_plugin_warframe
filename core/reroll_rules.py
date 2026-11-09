"""Build-oriented rule suggestions; no auction queries or price comparisons."""
import re
from .commands.base import Reply
from . import damage_calc, riven_analysis as RA, riven_pools as pools
from .formatters import RIVEN_DISPLAY_ZH


def build_recommendation(weapon, base=None, mode=''):
    name=weapon.get('zh') or weapon.get('en') or weapon.get('url_name')
    cls=RA.weapon_class(weapon.get('riven_type',''),weapon.get('group',''))
    root,members=pools.family_members(weapon.get('en') or name)
    positive,unc_pos=pools.available(cls,root,members,positive=True)
    negative,unc_neg=pools.available(cls,root,members,positive=False)
    positive=set(positive)-unc_pos;negative=set(negative)-unc_neg
    base=base or {}
    crit=base.get('criticalChance');status=base.get('procChance')
    crit_route=isinstance(crit,(int,float)) and crit>=.20
    status_route=isinstance(status,(int,float)) and status>=.20
    melee=cls=='melee';sniper=str(base.get('type','')).lower()=='sniper'
    pos=[];neg=[];avoid=[]
    def add(target,available,sid,grade,reason):
        if sid in available and not any(r[0]==sid for r in target):target.append((sid,grade,reason))
    def p(sid,g,reason):add(pos,positive,sid,g,reason)
    def n(sid,reason):add(neg,negative,sid,'候选',reason)
    def bad(sid,reason):add(avoid,negative,sid,'避免',reason)
    p('melee_damage','A','伤害加成不足时优先；已有大量同类增益时可让位')
    if crit_route:
        p('crit_damage','S','默认面板暴击几率较高，适合暴击配装')
        p('crit_chance','S','暴击路线优先，仍需结合现有暴击增益')
    else:
        p('crit_damage','B','仅在实际配装能稳定暴击时选择')
        p('crit_chance','B','有暴击增益或形态变化时再考虑')
    if melee:
        p('attack_speed','A','普通近战连击路线；不代表震地或特殊攻击收益')
        p('range','A','近战清群、覆盖范围需求')
        p('initial_combo','B','初始连击或重击路线，不作为通用连击推荐')
        p('melee_slam_damage','B','仅震地路线；属于融合词条，不能直接洗出')
        n('finisher_damage','不使用处决输出时')
        n('slide_crit','不使用滑行攻击暴击路线时')
        bad('attack_speed','普通近战连击路线会受影响')
        bad('range','近战覆盖范围会下降')
        bad('combo_duration','需要维持连击倍率时应避开')
    else:
        p('multishot','S','枪械通用候选，需确认武器特殊机制')
        p('fire_rate','A','持续输出且弹药供给允许时')
        p('reload_speed','B','换弹停顿明显、影响输出节奏时')
        if not sniper:n('zoom','不依赖瞄准放大与特殊瞄准机制时；仍需确认手感')
        n('ammo_max','弹药补给充足、非弹药紧张配装时')
        bad('multishot','会损失多重射击收益')
        bad('melee_damage','会降低基础伤害')
        bad('reload_speed','依赖手动换弹时会延长停顿')
    p('status_chance','A' if status_route else 'B','触发路线且需要增加异常覆盖时')
    p('toxin_damage','B','按元素组合和槽位需求选择，避免破坏已有组合')
    p('heat_damage','B','需要火焰或相关复合元素时')
    p('cold_damage','B','需要冰冻或相关复合元素时')
    if mode in {'夜灵','三傻'}:
        p('electric_damage','A','夜灵用途的辐射组合候选，结合现有火焰词条')
    if crit_route:
        bad('crit_chance','暴击路线应避开')
        bad('crit_damage','暴击路线应避开')
    if status_route:bad('status_chance','依赖异常触发的路线应避开')
    lines=[f'◆ 武器：{name}',f'◆ 推荐依据：武器默认形态与通用配装；用途：{mode or "通用"}',
           '※ S＝优先考虑，A＝常用备选，B＝按配装选择；是规则建议，不是收益计算或市场评级。']
    if crit is not None and status is not None:
        lines.append(f'◆ 默认面板：暴击几率 {crit:.0%}；触发几率 {status:.0%}（未装 MOD、未计特殊形态）')
    else:lines.append('※ 本地缺少完整默认面板，仅给类别建议，不推断暴击或触发强度。')
    for title,rows,sign in [('正面推荐',sorted(pos,key=lambda r:{'S':0,'A':1,'B':2}[r[1]]),'▲'),('负面候选（满足条件再选）',neg,'▼'),('负面避坑（按所述路线）',avoid,'▼')]:
        lines+=['◆ '+title,'　档位　词条　适用条件']
        for sid,grade,reason in rows:
            label='近战伤害' if melee and sid=='melee_damage' else RIVEN_DISPLAY_ZH.get(sid,sid)
            lines+=['· '+'　'.join([grade,sign+label,reason])]
        if not rows:lines+=['· 暂无可确认的通用候选，请按实际配装选择']
    lines+=['※ 没有无条件无害的负词条。灵化、特殊攻击、战甲增益及现有 MOD 会改变优先级；只列当前词条池可确认的项目。']
    return Reply(name+' · 洗卡推荐',lines,footer='规则建议 · 不查询 WM 挂单，不进行价格对比')


async def recommend(client,query,platform):
    query=re.sub(r'\s*刷新$','',query.strip()).strip()
    mode='';match=re.search(r'\s+(夜灵|三傻|日常|通用)$',query)
    if match:mode=match[1];query=query[:match.start()].strip()
    if not query:return Reply('洗卡推荐',['◆ 用法：武器名 洗卡推荐','· 执法者 洗卡推荐','· 绝路 Prime 洗卡推荐 夜灵'])
    try:weapon=await client.resolve_riven_weapon(query)
    except Exception:return Reply('洗卡推荐',['◆ 武器资料暂不可用，请稍后重试。'])
    if not weapon:return Reply('洗卡推荐',['◆ 未找到紫卡武器，请使用完整武器名或现有别名。'])
    base=damage_calc.find_weapon_exact(weapon.get('en') or '') or damage_calc.find_weapon_exact(weapon.get('zh') or '')
    return build_recommendation(weapon,base,mode)
