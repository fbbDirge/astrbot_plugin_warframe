"""Exact reward identities, including bundle and duration display suffixes."""
import re
REWARD_ICONS={
 '阿耶檀识 Anasa 塑像':'reward_anasa','Ayatan Anasa Sculpture':'reward_anasa',
 '内融核心捆包':'endo','内融核心':'endo','Endo':'endo','赤毒':'kuva','Kuva':'kuva',
 '经验值加成':'reward_affinity','Affinity Booster':'reward_affinity',
 '资源掉落几率加成':'reward_resource_chance','Resource Drop Chance Booster':'reward_resource_chance',
 'Mod 掉落几率加成':'reward_mod_chance','Mod Drop Chance Booster':'reward_mod_chance',
 '战甲特殊功能槽连接器':'reward_exilus','Exilus Warframe Adapter':'reward_exilus',
 '奥罗金反应堆蓝图':'blueprint:reward_reactor','Orokin Reactor Blueprint':'blueprint:reward_reactor',
 '奥罗金催化剂蓝图':'blueprint:reward_catalyst','Orokin Catalyst Blueprint':'blueprint:reward_catalyst',
 '传说核心':'reward_legendary','Legendary Core':'reward_legendary',
}
for label in ('近战','步枪','手枪','霰弹枪','Zaw','组合枪','空战'):
    REWARD_ICONS[label+'裂罅Mod']='reward_riven'
for label in ('Melee','Rifle','Pistol','Shotgun','Zaw','Kitgun','Archgun'):
    REWARD_ICONS[label+' Riven Mod']='reward_riven'

def normalized(text):return re.sub(r'\s+','',text).casefold()
ALIASES={normalized(k):v for k,v in REWARD_ICONS.items()}
REWARD_ASSETS={v.removeprefix('blueprint:') for v in REWARD_ICONS.values()}

def reward_icon(text):
    text=re.sub(r'\s*[×x]\s*[\d,]+\s*$','',str(text),flags=re.I).strip()
    text=re.sub(r'^\d+\s*(?:天|days?)\s*','',text,flags=re.I)
    return ALIASES.get(normalized(text),'')
