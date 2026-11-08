"""Render deterministic example data, not live market quotes."""
from pathlib import Path
from test_core import Command
from wf_plugin.cards import Card
from wf_plugin.renderer import CardRenderer
from wf_plugin.theme import theme_from
from wf_plugin.world import render_world

out = Path(__file__).resolve().parents[1]/'previews'
r = CardRenderer(out)
wm = Card('',title='膛线 · PC · 在线卖家',columns=('玩家','数量','价格','等级 / 状态'),rows=[
 [('Tenno_Aurora','wm_user'),('12','wm_quantity'),('18 白金','wm_price'),('等级 10 · 游戏中','muted')],
 [('Void_Walker','wm_user'),('3','wm_quantity'),('20 白金','wm_price'),('等级 10 · 在线','muted')],
 [('Lotus_Garden','wm_user'),('8','wm_quantity'),('22 白金','wm_price'),('等级 10 · 游戏中','muted')]],footer='示例数据 · 非实时报价\n第 1/1 页 · 报价缓存最多 30 秒')
p=r.render(wm,theme_from({}));p.replace(out/'wm-default.png')

boar_set = Card('',title='野猪 Prime 一套 · PC · 在线卖家',columns=('玩家','数量','价格','等级 / 状态'),rows=[
 [('kskblQWQ','wm_user'),('1','wm_quantity'),('88 白金','wm_price'),('游戏中','muted')],
 [('Xtramix','wm_user'),('2','wm_quantity'),('88 白金','wm_price'),('游戏中','muted')],
 [('-Riddle-','wm_user'),('5','wm_quantity'),('89 白金','wm_price'),('在线','muted')],
 [('-FCG-PANTSU','wm_user'),('5','wm_quantity'),('89 白金','wm_price'),('游戏中','muted')],
 [('El_Grappadura','wm_user'),('1','wm_quantity'),('89 白金','wm_price'),('游戏中','muted')]],footer='第 1/6 页 · 共 28 条 · 报价缓存最多 30 秒')
p=r.render(boar_set,theme_from({}));p.replace(out/'wm-boar-set.png')

boar_barrel = Card('',title='野猪 Prime 枪管 · PC · 在线卖家',columns=('玩家','数量','价格','等级 / 状态'),rows=[
 [('__Quintessence__','wm_user'),('3','wm_quantity'),('17 白金','wm_price'),('游戏中','muted')],
 [('Day_One','wm_user'),('6','wm_quantity'),('17 白金','wm_price'),('游戏中','muted')],
 [('zhuxinrana','wm_user'),('5','wm_quantity'),('17 白金','wm_price'),('游戏中','muted')],
 [('Neetguy','wm_user'),('1','wm_quantity'),('18 白金','wm_price'),('游戏中','muted')],
 [('PeoplesHero','wm_user'),('45','wm_quantity'),('19 白金','wm_price'),('游戏中','muted')]],footer='第 1/4 页 · 共 17 条 · 报价缓存最多 30 秒')
p=r.render(boar_barrel,theme_from({}));p.replace(out/'wm-boar-barrel.png')

wmr_example = Card('',title='托里德 · WMR · PC',columns=('卖家','一口价 / 状态','完整词条','卡片信息'),rows=[
 [('Tenno_Aurora','wm_user'),('500 白金\n游戏中','wm_price'),('正 · 暴击率 150%\n正 · 多重射击 100%\n负 · 变焦 -40%','riven_stat'),('循环 2\n等级 8/8\nMR 10','muted')],
 [('Void_Walker','wm_user'),('650 白金\n游戏中','wm_price'),('正 · 暴击率 150%\n正 · 多重射击 100%\n负 · 变焦 -40%','riven_stat'),('循环 25\n等级 8/8\nMR 10','muted')]],
 footer='预览示例 · 虚构挂单与价格\n筛选：暴击率 + 多重 + 负变焦\n仅在线 · 一口价升序 · 实际查询可显示详情地址')
p=r.render(wmr_example,theme_from({}));p.replace(out/'wmr-example.png')

wmr_live = Card('',title='托里德 · WMR · PC',columns=('卖家','一口价 / 状态','完整词条','卡片信息'),rows=[
 [('BloodyFluff','wm_user'),('600 白金\n游戏中','wm_price'),('正 · 多重射击 143%\n正 · 暴击率 231.5%\n负 · 变焦 -35.8%','riven_stat'),('循环 125\n等级 8/8\nMR 16','muted')],
 [('unevie','wm_user'),('700 白金\n游戏中','wm_price'),('正 · 多重射击 91.6%\n正 · 暴击率 152.2%\n正 · 冰冻伤害 109.4%\n负 · 变焦 -53.4%','riven_stat'),('循环 92\n等级 8/8\nMR 15','muted')],
 [('NineTailedSpiritCat','wm_user'),('900 白金\n游戏中','wm_price'),('正 · 暴击率 169.6%\n正 · 腐蚀伤害 109.4%\n正 · 多重射击 107.7%\n负 · 变焦 -56.5%','riven_stat'),('循环 65\n等级 8/8\nMR 12','muted')],
 [('Fighting32','wm_user'),('1350 白金\n游戏中','wm_price'),('正 · 多重射击 104.1%\n正 · 腐蚀伤害 109.5%\n正 · 暴击率 174.3%\n负 · 变焦 -59%','riven_stat'),('循环 240\n等级 8/8\nMR 10','muted')],
 [('Karina_KR','wm_user'),('1500 白金\n游戏中','wm_price'),('正 · 暴击率 192.9%\n正 · 多重射击 109.2%\n正 · 射速/攻击速度 70.5%\n负 · 变焦 -57.4%','riven_stat'),('循环 313\n等级 8/8\nMR 10','muted')]],
 footer='筛选：+暴击率、+多重射击、负变焦 · 仅在线\n第 1/1 页 · 一口价升序 · 缓存最多60秒\n本次接口返回 100 条，筛选后 5 条；不代表全部挂单或全市场最低价。\n挂单报价非成交价，购买前核对详情（图片链接需手动打开）：\n1. https://warframe.market/auction/6ae36eab06403f008c229207\n2. https://warframe.market/auction/6adf63a7e4283600081d3755\n3. https://warframe.market/auction/6aeb9a3787ad1a002a94752f\n4. https://warframe.market/auction/6ae64140fd03c20023e41d24\n5. https://warframe.market/auction/6ac1dbc164a7ca032576c219')
p=r.render(wmr_live,theme_from({}));p.replace(out/'wmr-live.png')

data={'timestamp':'2026-11-07T06:00:00Z','fissures':[
 {'tier':tier,'tierNum':i,'node':node,'missionType':mission,'expiry':'2099-01-01T12:30:00Z'}
 for i,(tier,node,mission) in enumerate([('Lith','Hepit（虚空）','Capture'),('Meso','Io（木星）','Defense'),('Neo','Ukko（虚空）','Capture'),('Axi','Apollo（月球）','Disruption')])]}
card=render_world(Command('裂缝'),data)
card.footer='示例数据 · 非实时任务\n第 1/1 页 · 共 4 条'
p=r.render(card,theme_from({}));p.replace(out/'fissures-default.png')
p=r.render(wm,theme_from({}, {'background_color':'#F4E7ED','wm_user':'#7C3AED','wm_quantity':'#0E7490','wm_price':'#EA580C','font_size':30}));p.replace(out/'wm-custom.png')
print(out)
