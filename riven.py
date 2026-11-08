"""Numerical riven grading, separate from OCR and market valuation."""
import math
import re
from datetime import datetime, timezone, timedelta
from .cards import Card
from .client import QueryError
from .naming import find_items, query_form

EXPORT = 'https://raw.githubusercontent.com/calamity-inc/warframe-public-export-plus/senpai/'
ROOT = '/Lotus/Upgrades/Mods/Randomized/'
LABELS = {
 'WeaponCritChanceMod':'暴击率','WeaponCritDamageMod':'暴击伤害','WeaponDamageAmountMod':'伤害',
 'WeaponMeleeDamageMod':'伤害','WeaponFireIterationsMod':'多重射击','WeaponFireRateMod':'射速',
 'WeaponMeleeFireRateMod':'攻击速度','WeaponFreezeDamageMod':'冰冻伤害','WeaponFireDamageMod':'火焰伤害',
 'WeaponToxinDamageMod':'毒素伤害','WeaponElectricityDamageMod':'电击伤害',
 'WeaponImpactDamageMod':'冲击伤害','WeaponArmorPiercingDamageMod':'穿刺伤害','WeaponSlashDamageMod':'切割伤害',
 'WeaponProcTimeMod':'触发时间','WeaponStunChanceMod':'触发几率','WeaponAmmoMaxMod':'弹药最大值',
 'WeaponClipMaxMod':'弹匣容量','WeaponProjectileSpeedMod':'弹道速度','WeaponPunctureDepthMod':'穿透',
 'WeaponRecoilReductionMod':'后坐力','WeaponReloadSpeedMod':'装填速度','WeaponZoomFovMod':'变焦',
 'ComboDurationMod':'连击持续时间','WeaponMeleeRangeIncMod':'范围','WeaponMeleeComboEfficiencyMod':'重击效率',
 'WeaponMeleeComboInitialBonusMod':'初始连击','WeaponMeleeComboPointsOnHitMod':'连击获取几率',
 'WeaponMeleeComboBonusOnHitMod':'额外连击几率','SlideAttackCritChanceMod':'滑行暴击率',
 'WeaponMeleeFinisherDamageMod':'处决伤害',
}
for prefix in ['WeaponFactionDamage','WeaponMeleeFactionDamage']:
 for faction in ['Grineer','Corpus','Infested']:
  LABELS[prefix+faction] = '对'+faction
ALIASES = {'暴击几率':'暴击率','暴率':'暴击率','暴伤':'暴击伤害','基础伤害':'伤害','基伤':'伤害',
           '多重':'多重射击','触发率':'触发几率','攻速':'攻击速度','毒':'毒素伤害','冰':'冰冻伤害',
           '火':'火焰伤害','电':'电击伤害','病毒':'病毒伤害','腐蚀':'腐蚀伤害','辐射':'辐射伤害',
           '爆炸':'爆炸伤害','磁力':'磁力伤害','毒气':'毒气伤害'}
SPLICED = {'病毒伤害','腐蚀伤害','辐射伤害','爆炸伤害','磁力伤害','毒气伤害'}
ABSOLUTE = {'ComboDurationMod','WeaponMeleeRangeIncMod','WeaponMeleeComboInitialBonusMod','WeaponPunctureDepthMod'}


def grade(deviation):
    for threshold,label in [(9.5,'S'),(7.5,'A+'),(5.5,'A'),(3.5,'A-'),(1.5,'B+'),(-1.5,'B'),(-3.5,'B-'),(-5.5,'C+'),(-7.5,'C'),(-9.5,'C-')]:
        if deviation >= threshold: return label
    return 'F'


def mean_value(entry, disposition, rank, positives, negatives, curse=False):
    base = float(entry['upgradeValues'][0]['value'])
    common = base * 15 * disposition * (rank+1)
    return common * ({2:.33000001,3:.5}[positives] * -1 if curse else {2:.66000003,3:.5}[positives] * (1.25 ** negatives))


def display(value, tag):
    if 'FactionDamage' in tag: return value+1
    return value if tag in ABSOLUTE else value*100


def unit(tag):
    if 'FactionDamage' in tag: return '×'
    if tag in {'WeaponMeleeRangeIncMod','WeaponPunctureDepthMod'}: return 'm'
    if tag == 'ComboDurationMod': return 's'
    if tag == 'WeaponMeleeComboInitialBonusMod': return ''
    return '%'


def parse_analysis(query):
    # Explicit key=value syntax avoids mistaking digits in weapon names for stats.
    tokens = query.replace('，',' ').replace(',',' ').replace('％','%').split()
    weapon, stats = [], []
    for token in tokens:
        m = re.fullmatch(r'([^=：:]+)[=：:]([+-]?\d+(?:\.\d+)?)([%ms×]?)',token)
        if not m:
            m2 = re.fullmatch(r'([+-]\d+(?:\.\d+)?)%?([\u4e00-\u9fff]+)',token)
            if m2: m = (m2[2],m2[1],'')
        if m:
            label,value,suffix = (m[1],m[2],m[3]) if not isinstance(m,tuple) else m
            label = ALIASES.get(label,label)
            value = float(value)
            if not math.isfinite(value) or abs(value)>100000:
                raise QueryError('属性数值超出合理输入范围。')
            if label in [a for a,_,_ in stats]: raise QueryError('同一属性不能重复输入。')
            stats.append((label,value,suffix))
        elif '=' in token or ':' in token or '：' in token:
            raise QueryError('属性格式：暴击率=162.5 多重=-75.5；数值不要包含其他文字。')
        elif stats:
            raise QueryError('请先填写完整武器名，再填写 属性=数值。')
        else: weapon.append(token)
    if not weapon or not 2 <= len(stats) <= 4:
        raise QueryError('用法：紫卡分析 托里德 暴击率=162.5 病毒伤害=110.3 伤害=172 多重=-75.5\n默认满级，可加 -rank=0 至 -rank=8。')
    return ' '.join(weapon),stats


class RivenService:
    def __init__(self,client,page_size=10):
        self.client=client; self.page_size=page_size

    async def data(self):
        weapons = await self.client.get(EXPORT+'ExportWeapons.json',ttl=21600)
        upgrades = await self.client.get(EXPORT+'ExportUpgrades.json',ttl=21600)
        dictionary = await self.client.get(EXPORT+'dict.zh.json',ttl=21600)
        mods = {k:v for k,v in upgrades.items() if k.startswith(ROOT) and 'RandomModRare' in k and 'compatibleItems' in v}
        catalogue=[]
        for ref,w in weapons.items():
            if w.get('excludeFromCodex') or not w.get('omegaAttenuation'): continue
            cursor=ref; mod=None; seen=set()
            while cursor and cursor not in seen:
                seen.add(cursor)
                mod = next((k for k,v in mods.items() if cursor in v['compatibleItems']),None)
                if mod: break
                cursor=weapons.get(cursor,{}).get('parentName')
            if not mod: continue
            title=dictionary.get(w.get('name'),w.get('name',''))
            if title.startswith('/'): continue
            catalogue.append({'slug':ref.rsplit('/',1)[-1], 'i18n':{'zh-hans':{'name':title}},'ref':ref,'weapon':w,'mod':mods[mod]})
        # WM supplies reliable English names for base weapons, not every variant.
        market=await self.client.get('https://api.warframe.market/v2/riven/weapons',ttl=21600)
        by_ref={x['gameRef']:x for x in market}
        for item in catalogue:
            if item['ref'] in by_ref:
                src=by_ref[item['ref']]; item['slug']=src['slug']; item['i18n'].update(src.get('i18n',{}))
        return catalogue

    async def run(self,c):
        query,stats=parse_analysis(c.query) if c.name=='紫卡分析' else (c.query,[])
        if not query: raise QueryError('用法：紫卡倾向 武器名，例如 紫卡倾向 执法者 3+1')
        catalogue=await self.data()
        matches=find_items(catalogue,query)
        family=[]
        if c.name=='紫卡倾向':
            # Show exact base weapon and its related named variants together.
            q=query_form(query)
            family=[x for x in catalogue if q in query_form(x['i18n']['zh-hans']['name'])]
            if not (len(matches)==1 and q in [query_form(matches[0]['i18n']['zh-hans']['name']),query_form(matches[0]['slug'])]):
                matches=family or matches
        if not matches: raise QueryError('未找到紫卡武器。请使用完整中文武器名，含 Prime／圣洁等版本名。')
        if len(matches)>1:
            rows=[[(x['i18n']['zh-hans']['name'],'riven_stat'),(f"{x['weapon']['omegaAttenuation']:.3f}",'riven_range'),('●'*dots(x['weapon']['omegaAttenuation'])+'○'*(5-dots(x['weapon']['omegaAttenuation'])),'riven_grade'),('请用完整名查看区间','muted')] for x in matches]
            return self.card_page(c,'紫卡倾向 · 武器版本',rows,('武器','倾向','等级','查询提示'),'数据：Public Export Plus · 请明确版本后分析。')
        item=matches[0]; w=item['weapon']; entries={LABELS.get(x['tag'],x['tag']):x for x in item['mod']['upgradeEntries']}
        if 'Melee' in item['mod'].get('compat','') and '射速' in entries:
            entries['攻击速度'] = entries.pop('射速')
        disposition=c.disposition if c.disposition is not None else float(w['omegaAttenuation'])
        title=item['i18n']['zh-hans']['name']
        detail=f'倾向 {disposition:g}'+('（手动覆盖）' if c.disposition is not None else '（数据源当前值）')+f' · 卡片等级 {c.mod_rank}/8'
        related=[x for x in family if x['ref']!=item['ref']]
        if related:
            detail+='\n同系版本：'+' / '.join(f"{x['i18n']['zh-hans']['name']} {x['weapon']['omegaAttenuation']:g}" for x in related[:6])
        if not stats:
            p,n=map(int,c.layout.split('+')); rows=[]
            for label,entry in entries.items():
                if label.startswith('Weapon'): continue
                tag=entry['tag']; pos=mean_value(entry,disposition,c.mod_rank,p,n)
                neg=mean_value(entry,disposition,c.mod_rank,p,n,True)
                rows.append([(label,'riven_stat'),(interval(pos,tag) if entry.get('canBeBuff',True) else '不可为正','riven_range'),(interval(neg,tag) if n and entry.get('canBeCurse',False) else '—','riven_negative'),(unit(tag),'muted')])
            return self.card_page(c,f'{title} · 紫卡倾向',rows,('属性','正面区间','负面区间','单位'),detail+f' · {p}正{n}负\n理论区间非可洗出词条清单；武器限制需以游戏为准。')
        resolved=[]; estimated=False
        for label,value,suffix in stats:
            entry=entries.get(label)
            if label in SPLICED:
                # Export currently omits spliced entries: explicit estimated model.
                entry=entries.get('毒素伤害'); estimated=True
            if not entry: raise QueryError(f'暂不支持该武器的属性：{label}。请用 紫卡倾向 查看可用属性。')
            tag=entry['tag']; base=float(entry['upgradeValues'][0]['value'])
            if suffix and suffix != unit(tag): raise QueryError(f'{label} 的单位应为 {unit(tag) or "数值"}。')
            raw=value-1 if 'FactionDamage' in tag else value
            if raw==0: raise QueryError('属性数值不能为零。')
            curse=raw*base<0
            if curse and (not entry.get('canBeCurse',False) or label in SPLICED): raise QueryError(f'{label} 不支持此负面属性。')
            if not curse and not entry.get('canBeBuff',True): raise QueryError(f'{label} 不支持此正面属性。')
            resolved.append((label,value,entry,curse))
        n=sum(x[3] for x in resolved); p=len(resolved)-n
        if p not in {2,3} or n not in {0,1}: raise QueryError('支持 2正0负、2正1负、3正0负、3正1负；后坐力的负数属于正面属性。')
        rows=[]; deviations=[]; invalid=False
        for label,value,entry,curse in resolved:
            tag=entry['tag']; mean=mean_value(entry,disposition,c.mod_rank,p,n,curse)
            center=display(mean,tag); offset=1 if 'FactionDamage' in tag else 0
            deviation=((value-offset)/(center-offset)-1)*100
            lo,hi=sorted([display(mean*.9,tag),display(mean*1.1,tag)])
            outside=value<lo-.051 or value>hi+.051
            adjusted=-deviation if curse else deviation
            invalid |= outside
            if not outside: deviations.append(adjusted)
            label_text=label+('（估算）' if label in SPLICED else '')
            rows.append([(f'{label_text}\n{value:+g}{unit(tag)}','riven_negative' if curse else 'riven_stat'),(interval(mean,tag)+unit(tag),'riven_range'),(f'{deviation:+.3f}%','muted'),('超出区间' if outside else grade(adjusted),'riven_grade')])
        summary='不评级（数值超出区间，请核对版本、等级或倾向）' if invalid else f'{grade(sum(deviations)/len(deviations))} · 品质偏差 {sum(deviations)/len(deviations):+.3f}%'
        footer=detail+f' · {p}正{n}负\n综合：'+summary+'\n负面按惩罚越小越好反向评级；综合为等权数值品质，不是价格或配装强度。'
        if estimated: footer+='\n含融合元素：暂按基础元素系数估算，评级仅供参考。'
        footer+='\n数据：Public Export Plus / browse.wf · 理论浮动 ±10%'
        return Card('紫卡分析',title=title+' · 紫卡数值分析',columns=('属性 / 实际值','理论区间','相对均值偏差','评级'),rows=rows,footer=footer)

    def card_page(self,c,title,rows,columns,footer):
        total=(len(rows)+self.page_size-1)//self.page_size
        if c.page>total: raise QueryError(f'只有 {total} 页。')
        footer+=f'\n第 {c.page}/{total} 页 · 使用 -2 翻页'
        return Card(title,title=title,columns=columns,rows=rows[(c.page-1)*self.page_size:c.page*self.page_size],footer=footer)


def interval(mean,tag):
    a,b=sorted([display(mean*.9,tag),display(mean*1.1,tag)])
    return f'{a:.2f} ～ {b:.2f}'


def dots(d):
    return 1+sum(d>=x for x in [.7,.9,1.1,1.3])
