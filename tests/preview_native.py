"""Offline layout fixtures, explicitly marked as examples."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import test_core
from wf_plugin.core import formatters as fmt
from wf_plugin.core.commands import Reply
from wf_plugin.presentation import present
from wf_plugin.renderer import CardRenderer
from wf_plugin.theme import theme_from
import shutil
from datetime import datetime,timedelta,timezone

ROOT=Path(__file__).resolve().parents[1]
r=CardRenderer(ROOT/'previews/.native-temp')
def save(name,result):
    title,lines=result[:2]
    cards=present(Reply(title,lines,footer='布局示例 · 虚构挂单数据'))
    for i,c in enumerate(cards):
        path=r.render(c,theme_from({}))
        shutil.move(path,ROOT/f'previews/native-{name}{"" if i==0 else "-"+str(i+1)}.png')

orders=[{'order_type':'sell','platinum':p,'quantity':q,'mod_rank':8,'user':{'ingame_name':name,'status':'ingame','reputation':rep}}
        for name,p,q,rep in [('Tenno_One',15,3,120),('Tenno_Two',18,5,68),('Tenno_Three',20,1,32)]]
save('market',fmt.fmt_wm_orders('膛线',orders))
auctions=[{'id':'example','buyout_price':180,'item':{'mod_rank':8,'re_rolls':12,'attributes':[{'url_name':'critical_chance','value':162.5,'positive':True},{'url_name':'multishot','value':110.3,'positive':True},{'url_name':'zoom','value':35,'positive':False}]},'owner':{'ingame_name':'Tenno_Example','status':'ingame','reputation':85}}]
save('riven-market',fmt.fmt_wr_auctions('托里德',auctions))
missions=[{'expiry':(datetime.now(timezone.utc)+timedelta(minutes=34)).isoformat(),'tier':tier,'missionType':mission,'node':node,'enemy':faction,'isHard':hard} for tier,mission,node,faction,hard in [('Lith','Defense','Stephano (Uranus)','Grineer',False),('Meso','Survival','Ani (Void)','Corrupted',True),('Neo','Capture','Hydra (Pluto)','Corpus',False),('Axi','Exterminate','Saxis (Eris)','Infested',True)]]
save('fissures',fmt.fmt_fissures(missions,all_rows=True))
save('relic',fmt.fmt_relic_rewards('古纪 A1',[{'rarity':rarity,'name':name,'chance':chance} for rarity,name,chance in [('铜','示例武器 枪管',25.33),('银','示例战甲 系统蓝图',11),('金','示例武器 蓝图',2)]],{'示例战甲 系统蓝图':{'ducats':45,'plat':15,'dpp':3}}))
save('analysis',fmt.fmt_riven_analysis('托里德',1.25,'rifle',[('crit_chance',162.5),('damage',172),('multishot',110.3)],[('zoom',35)]))
r.output.rmdir()
