"""Locally drawn semantic glyphs for non-element Riven attributes (not DE artwork)."""
import re
from functools import lru_cache
from .core.parser import RIVEN_STAT_ALIASES, RIVEN_STAT_ZH

STAT_LABELS = dict(zip(
    ('melee_damage crit_chance crit_damage multishot attack_speed fire_rate status_chance status_duration range initial_combo combo_duration heavy_attack_efficiency finisher_damage slide_crit magazine_capacity ammo_max projectile_speed punch_through reload_speed recoil zoom extra_combo_count combo_gain_chance weakpoint_damage weakpoint_crit_chance status_damage ammo_efficiency reload_holstered melee_heavy_attack_damage melee_heavy_attack_charge melee_parry_angle melee_slam_damage').split(),
    ('基伤 暴率 暴伤 多重 攻速 射速 触发 触时 范围 初连 连时 重效 处决 滑暴 弹匣 弹药 弹速 穿透 装填 后坐 变焦 加连 获连 弱伤 弱暴 异伤 弹效 收装 重伤 蓄力 招架 震地').split()))
STAT_ICONS={key:'stat_'+key for key in STAT_LABELS}

@lru_cache(maxsize=1)
def aliases():
    result={}
    for key,icon in STAT_ICONS.items():
        for name in {*RIVEN_STAT_ALIASES.get(key,()), RIVEN_STAT_ZH.get(key,''),key}:
            if name:result[name.casefold()]=icon
    result.update({
        '暴击倍率':STAT_ICONS['crit_damage'],
        '弹药上限':STAT_ICONS['ammo_max'],
        '射速 / 攻击速度':STAT_ICONS['fire_rate'],
        '射速/攻击速度':STAT_ICONS['fire_rate'],
        '射速/攻速':STAT_ICONS['fire_rate'],
        '基础伤害 / 近战伤害':STAT_ICONS['melee_damage'],
        '基础伤害/近战伤害':STAT_ICONS['melee_damage'],
    })
    return result

def stat_icon(text):
    text=re.sub(r'^(?:[正负]面?\s*[·:]?\s*|[+−-]\s*(?=[^\d]))','',text).strip()
    # Full labels only; descriptive parentheses do not change the stat identity.
    text=re.sub(r'[（(](?:重击时.*|弓类.*)[）)]','',text).strip()
    number=r'[+−-]?\d[\d,]*(?:\.\d+)?[%×x]?'
    text=re.sub(r'^'+number+r'\s*','',text)
    text=re.sub(r'\s*[:：]?\s*'+number+r'$','',text).strip()
    hit=aliases().get(text.casefold(),'')
    if not hit and '/' in text:
        hit=aliases().get(text.split('/')[0].strip().casefold(),'')
    return hit
