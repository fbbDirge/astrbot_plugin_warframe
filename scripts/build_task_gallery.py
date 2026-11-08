"""Generate an offline visual review pack using the real formatters and renderer."""
import asyncio,sys,json,html,shutil,time,math
from pathlib import Path
from datetime import datetime,timedelta,timezone
from zipfile import ZipFile,ZIP_DEFLATED
from unittest.mock import AsyncMock,patch
from types import SimpleNamespace
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests'))
from test_core import ROOT
from wf_plugin.core import formatters as f
from wf_plugin.core.commands import Reply
from wf_plugin.presentation import present,table
from wf_plugin.renderer import CardRenderer,load_icon,FONT
from wf_plugin.theme import theme_from
from wf_plugin.cards import Card,IconText
from wf_plugin.world_icons import FACTIONS,RELICS
from wf_plugin.display_icons import ELEMENT_ICONS,line_icon
from wf_plugin.stat_icons import STAT_ICONS
from wf_plugin.core.parser import RIVEN_STAT_ZH,parse
from wf_plugin.core.circuit import detail
from wf_plugin.core.reroll_market import report,summarize
from test_arbitration_display import sample_reply
from test_component_art import relic_card
from test_rewards_stats import alerts_card
from test_reroll_market import auction

OUT=ROOT/'dist/task-images-2026-11-08';OUT.mkdir(parents=True,exist_ok=True)
shutil.rmtree(OUT/'images',ignore_errors=True)
(OUT/'images').mkdir(exist_ok=True);renderer=CardRenderer(OUT/'.render')
entries=[];failures=[];audit=[]
expiry=(datetime.now(timezone.utc)+timedelta(hours=6)).isoformat()

def save(label,command,result,kind='',note=''):
    if isinstance(result,Reply):cards=present(result,kind)
    elif isinstance(result,Card):cards=[result]
    else:cards=present(Reply(result[0],result[1]),kind)
    for page,c in enumerate(cards,1):
        c.footer+='\n测试数据 · 仅用于检查排版与图标，不代表当前任务或行情'
        stem=f'{len(entries)+1:03d}_{label}'+(f'_{page}' if len(cards)>1 else '')
        path=OUT/'images'/(stem+'.png');shutil.copyfile(renderer.render(c,theme_from({})),path)
        entries.append({'name':label,'command':command,'file':'images/'+path.name,'note':note,'page':page})

def case(label,command,fun,*args,kind='',**kwargs):
    try:save(label,command,fun(*args,**kwargs),kind)
    except Exception as e:failures.append((label,type(e).__name__,str(e)));print('FAIL',failures[-1],flush=True)

async def main():
    variants=[{'node':'Stephano (Uranus)','missionType':'Defense','faction':'Grineer','modifier':'火焰','level':'100-110'},
              {'node':'V Prime (Venus)','missionType':'Survival','faction':'Corpus','modifier':'冰冻','level':'110-120'},
              {'node':'Nimus (Eris)','missionType':'Exterminate','faction':'Infested','modifier':'辐射','level':'120-130'}]
    case('平原周期','平原',f.fmt_cetus,*[{'_name':n,'expiry':expiry,'state':state,'isDay':False} for n,state in [('cetus','night'),('vallis','cold'),('cambion','fass'),('earth','night'),('duviri','joy'),('zariman','corpus')]])
    case('时效汇总','时效',f.fmt_timers,[('突击',{'expiry':expiry}),('执刑官',{'expiry':expiry}),('仲裁',{'expiry':expiry})])
    factions=['Grineer','Corpus','Infested','Corrupted','Sentient','Narmer','The Murmur','Scaldra','Techrot','Duviri']
    missions=['Capture','Defense','Survival','Exterminate','Disruption','Interception','Alchemy','Mobile Defense','Excavation','Spy']
    for name,hard,storm in [('普通裂缝',False,False),('钢铁裂缝',True,False),('九重天裂缝',False,True)]:
        rows=[{'tier':tier,'tierNum':i+1,'missionType':missions[i],'node':variants[i%3]['node'],'enemy':factions[i],'expiry':expiry,'isHard':hard,'isStorm':storm} for i,tier in enumerate(['Lith','Meso','Neo','Axi','Requiem','Omnia'])]
        case(name,name,f.fmt_fissures,rows,all_rows=True,kind='fissures')
    case('突击','突击',f.fmt_sortie,{'boss':'测试首领','expiry':expiry,'variants':variants})
    case('执刑官猎杀','执刑官',f.fmt_archon,{'boss':'Nira','bossCode':'SORTIE_BOSS_NIRA','expiry':expiry,'faction':'Narmer','variants':[{**v,'faction':'Narmer'} for v in variants]})
    alertrows=[{'expiry':expiry,'mission':{'node':v['node'],'type':v['missionType'],'faction':v['faction'],'desc':'测试警报','min_level':20,'max_level':30,'reward':{'item_names':[reward],'credits':10000}}} for v,reward in zip(variants,['Forma ×3','Kuva ×200000','Moonflesh ×50'])]
    case('警报','警报',f.fmt_alerts,alertrows)
    case('入侵','入侵',f.fmt_invasions,[{'node':v['node'],'attacker':{'faction':v['faction'],'items':['福马蓝图'],'completion':50},'defender':{'faction':factions[(i+1)%3],'items':['赤毒 ×10000']},'completion':50} for i,v in enumerate(variants)])
    case('赤毒虹吸','赤毒',f.fmt_kuva,[{'node':v['node'],'type':v['missionType'],'enemy':v['faction']} for v in variants])
    case('虚空风暴','九重天',f.fmt_void_storms,[{'nodeCn':v['node'],'tier':['Lith','Meso','Axi'][i],'missionType':v['missionType'],'enemy':v['faction'],'expiry':expiry} for i,v in enumerate(variants)])
    save('当前仲裁','仲裁',await sample_reply(),'arbitration')
    from wf_plugin.core.commands.arbitration import ArbitrationCommands
    host=ArbitrationCommands();now=int(time.time()//3600)*3600
    nodes={str(i):{'nameZh':v['node'],'systemNameZh':'测试星球','missionNameZh':missions[i%len(missions)],'factionNameZh':fac} for i,(v,fac) in enumerate(zip(variants*4,factions))}
    host._arb_fetch=AsyncMock(return_value=({'startTs':now,'stepSec':3600,'seq':list(range(10)),'nodes':list(nodes)},nodes,{str(i):['S','A+','A','A-','F'][i%5] for i in range(10)}))
    save('仲裁时间表','仲裁表',await host._h_arbtable(parse('仲裁表'),None,'pc'),'arbtable')
    for title,fac in [('深层科研','The Murmur'),('时光科研','Scaldra')]:
        case(title,title,f.fmt_archimedea,{'expiry':expiry,'missions':[{'missionType':m,'faction':fac,'difficulties':[{'tag':'普通','deviation':'测试偏差','risks':['护盾限制']},{'tag':'硬化','deviation':'测试偏差','risks':['护盾限制','能量限制']}]} for m in ['Survival','Mirror Defense','Alchemy']],'variables':[{'name':'测试个人减益','description':'此处为测试说明。'}]},title)
    case('夜灵电波','电波',f.fmt_nightwave,{'season':10,'activeChallenges':[{'title':'测试挑战','desc':'完成指定任务','required':3,'standing':1000,'expiry':expiry,'isDaily':i==0,'isElite':i==2} for i in range(3)]})
    case('结合目标','结合目标',f.fmt_synth_targets,[{'active':True,'name':'Lancer','node':'Mantle (Earth)','type':'Capture','faction':'Grineer'}])
    case('钢铁侵袭','钢铁侵袭',f.fmt_incursions,{'expiry':expiry,'nodes':['SolNode1','SolNode2','SolNode3']})
    case('钢铁之路','钢铁之路',f.fmt_steel_path,{'currentReward':'福马蓝图','remaining':'6小时','incursions':[{'node':v['node'],'missionType':v['missionType']} for v in variants]})
    case('沉沦之地','沉沦之地',f.fmt_descendia,{'expiry':expiry,'challenges':[{'index':i+1,'Type':t,'code':'VeryToxic'} for i,t in enumerate(['DT_EXTERMINATE','DT_ALCHEMY','DT_DEFENSE','DT_RACE'])]})
    case('日历','日历',f.fmt_calendar,{'season':'CST_SPRING','yearIteration':1,'expiry':expiry,'days':[{'date':'2026-11-08','day':8,'events':[{'type':'CHALLENGE','name':'测试挑战','desc':'击败指定敌人'}]},{'date':'2026-11-09','day':9,'events':[{'type':'REWARD','name':'福马蓝图'}]},{'date':'2026-11-10','day':10,'events':[{'type':'UPGRADE','name':'测试增益','desc':'暴击几率提升'}]}]})
    for reg,kw in [('Ostrons','地球'),('Solaris United','金星'),('Entrati','火卫二')]:
        jobs=[{'type':'测试赏金','enemyLevels':[10,30],'standingStages':[100,200,300],'rewardPool':['内融核心 ×100','福马蓝图'],'rewardTable':'CetusTierATableARewards'}]
        case('赏金_'+reg,'赏金',f.fmt_bounties,[{'syndicate':reg,'expiry':expiry,'jobs':jobs}],keyword=kw)
    for reg,tag,node in [('扎里曼','ZarimanSyndicate','SolNode230'),('实验室','EntratiLabSyndicate','SolNode718'),('1999','HexSyndicate','SolNode851')]:
        challenge=next(iter(f.de_zh('challenges_zh.json')))
        case('赏金详情_'+reg,'赏金 '+reg,f.fmt_bounties,[],keyword=reg,cycle={'expiry':expiry,'rot':'A','bounties':{tag:[{'node':node,'challenge':challenge}]}})
    case('限时活动','活动',f.fmt_events,[{'name':'测试社区活动','node':'Earth','goal':1000,'count':450,'expiry':expiry,'desc':'测试活动说明','rewards':['福马蓝图','10000 星币']}])
    case('武形秘仪','武形秘仪',f.fmt_conclave,[{'cat':'每日','mode':'歼灭','text':'完成 3 场对战','value':3}])
    case('舰队建设','舰队进度',f.fmt_construction,{'expiry':expiry,'projects':[{'name':'巨人战舰','en':'Fomorian','faction':'Grineer','pct':40,'event':'巨人战舰袭击'}],'assaults':[]})
    case('氏族奖励','氏族任务',f.fmt_clan_rewards,[{'region':'地球','week':1,'rewards':[{'name':'内融核心','count':1000,'points':500},{'name':'福马蓝图','count':1,'points':1000}]}])
    case('奸商','奸商',f.fmt_void_trader,{'active':True,'character':'Baro Ki’Teer','location':'水星中继站','activation':datetime.now(timezone.utc).isoformat(),'expiry':expiry,'inventory':[{'item':'棱晶 空刃','ducats':500,'credits':175000},{'item':'膛线 Prime','ducats':400,'credits':100000}]})
    case('每日特惠','每日特惠',f.fmt_daily_deals,[{'item':'福马','salePrice':15,'originalPrice':35,'total':100,'sold':20,'expiry':expiry}])
    case('商城折扣','商城折扣',f.fmt_flash_sales,[{'name':'测试礼包','price':75,'discount':50,'end':expiry}])
    case('钢铁兑换','钢铁兑换',f.fmt_steel_essence_shop)
    case('裂罅碎块兑换','碎银',f.fmt_sliver_shop)
    case('御品阿耶','阿耶',f.fmt_prime_vault,{'items':[{'name':'Volt Prime','price':3,'cost':3,'prime':3}],'prime':['Volt Prime'],'prime_currency':True,'expiry':expiry})
    from wf_plugin.core.commands.rotations import RotationCommands
    rotations=json.loads((ROOT/'core/data/rotations.json').read_text())
    save('回廊灵化','灵化',Reply('本周回廊战甲与灵化武器',detail(rotations['incarnon'])),'incarnon')
    # Populate element bonuses with clearly synthetic values for icon coverage.
    for key in ('tenet','coda'):
        data=rotations[key]
        for items in [data.get('items',[]),*data.get('batches',[])]:
            for i,item in enumerate(items):
                if isinstance(item,dict):item.update(element=['heat','cold','electricity','toxin','magnetic','radiation','impact'][i%7],bonus=25+i*5)
    rotation_fixture=OUT/'rotation-fixture.json';rotation_fixture.write_text(json.dumps(rotations,ensure_ascii=False))
    rotation_host=RotationCommands();rotation_host._valence_note=lambda *args: '※ 测试元素加成'
    for key,label in [('tenet','信条轮换'),('coda','科达轮换')]:
        try:
            with patch('wf_plugin.core.commands.rotations.core_paths.read_path',return_value=rotation_fixture):save(label,label,rotation_host._rotation_lines(key,label))
        except Exception as e:failures.append((label,type(e).__name__,str(e)))
    case('言录使','言录使',f.fmt_acrichis_week,{'expiry':expiry,'items':[{'name':'福马蓝图','price':20,'qty':1}]})
    case('新闻','新闻',f.fmt_news,[{'message':'测试新闻：任务图片图标检查','link':'https://www.warframe.com','date':datetime.now(timezone.utc).isoformat()}])
    save('遗物奖励','遗物 中纪M6',relic_card())
    orders=[{'order_type':'sell','visible':True,'platinum':p,'quantity':q,'user':{'ingame_name':'Test_Tenno_'+str(i),'status':'ingame','reputation':50}} for i,(p,q) in enumerate([(15,3),(20,10),(100,1)])]
    case('WM卖单','wm 膛线',f.fmt_wm_orders,'膛线',orders)
    case('WM买单','wm 膛线 收购',f.fmt_wm_orders,'膛线',[{**r,'order_type':'buy'} for r in orders],buy=True)
    auctions=[auction(i,slug='torid',pos=('critical_chance','critical_damage','multishot'),neg=('zoom',),price=100+i*10) for i in range(25)]
    for a in auctions:a['owner'].update(ingame_name='Test_Tenno_'+a['id'],status='ingame');a['item']['re_rolls']=10
    case('WMR紫卡','wmr 托里德',f.fmt_wr_auctions,'托里德',auctions[:3])
    case('紫卡分析','紫卡分析 托里德',f.fmt_riven_analysis,'托里德',1.2,'rifle',[('crit_chance',162.5),('crit_damage',110),('multishot',100)],[('zoom',35)])
    w={'zh':'托里德','en':'Torid','url_name':'torid','riven_type':'rifle'}
    save('洗卡推荐缓存','托里德 洗卡推荐',report(w,w,{'slug':'torid','platform':'pc','sampled_at':time.time()-86400,'stats':summarize(auctions,'torid')},'测试：接口失败，使用历史缓存（非实时）'),'reroll')
    for element in ['heat','cold','electricity','toxin','impact','magnetic','radiation']:
        a={'id':'test','buyout_price':100,'owner':{'ingame_name':'Test_Tenno','status':'ingame'},'item':{'type':'lich','weapon_url_name':'kuva_bramma','element':element,'damage':55,'having_ephemera':True}}
        case('玄骸_'+element,'xh 布拉玛 '+element,lambda a:('玄骸交易',f.fmt_lich_table([a])),a)
    # Cross-product audits retain expected and observed icon identities in the pack.
    for alias,(icon,label) in FACTIONS.items():
        from wf_plugin.presentation import cell
        actual=getattr(cell(alias,'派系')[0],'icon','')
        audit.append({'text':alias,'role':'派系','expected':icon,'actual':actual,'loaded':load_icon(actual,32) is not None})
    for name,icon in {**ELEMENT_ICONS,'虚空':'void','Tau':'tau','真实':'true'}.items():
        for value in [name,name+' 55%',f'+55% {name}',f'负面：{name} 55%']:
            actual=line_icon(value,'damage');audit.append({'text':value,'role':'damage','expected':icon,'actual':actual,'loaded':load_icon(actual,32) is not None})
    for sid,icon in STAT_ICONS.items():
        for text in [RIVEN_STAT_ZH[sid]+' 100%', '负面：'+RIVEN_STAT_ZH[sid]+' 50%']:
            actual=line_icon(text,'riven_stat');audit.append({'text':text,'role':'riven_stat','expected':icon,'actual':actual,'loaded':load_icon(actual,32) is not None})
    save('派系图标全览','图标检查',table('派系图标全览',['派系','说明'],[[next(k for k,v in FACTIONS.items() if v[0]==icon),'测试图标'] for icon in dict.fromkeys(v[0] for v in FACTIONS.values())]))
    save('伤害元素图标全览','图标检查',table('物理与元素伤害',['元素','数值'],[[name,'100%'] for name in [*ELEMENT_ICONS,'虚空','Tau','真实']]))
    save('紫卡词条图标全览','图标检查',table('非元素紫卡词条',['词条','数值'],[[RIVEN_STAT_ZH[sid],'100%'] for sid in STAT_ICONS]))
    for filename,label,command in [('native-help.png','指令一览','帮助'),('native-damage.png','武器伤害计算','伤害 绝路')]:
        source=ROOT/'previews'/filename
        if source.exists():
            target=OUT/'images'/f'{len(entries)+1:03d}_{label}.png';shutil.copyfile(source,target)
            entries.append({'name':label,'command':command,'file':'images/'+target.name,'note':'本地固定参数计算或帮助说明，不含实时数据','page':1})
    failed=[a for a in audit if a['actual']!=a['expected'] or not a['loaded']]
    save('负面格式图标检查','图标检查',table('带负面前缀的图标',['词条','说明'],[[a['text'],'期望：'+a['expected']] for a in audit if a['text'].startswith('负面：')]))
    if Path('/tmp/wf-task-icons-before.json').exists():shutil.copyfile('/tmp/wf-task-icons-before.json',OUT/'icon-audit-before-fix.json')
    (OUT/'icon-audit.json').write_text(json.dumps({'checks':audit,'failed':failed},ensure_ascii=False,indent=2))
    (OUT/'manifest.json').write_text(json.dumps({'generated':datetime.now(timezone(timedelta(hours=8))).isoformat(),'images':entries,'generation_errors':failures},ensure_ascii=False,indent=2))
    print('IMAGES',len(entries),'ERRORS',failures,'ICON_FAILURES',len(failed),flush=True)
    if failures:raise SystemExit(1)
    finish()

def finish():
    links=''.join(f'<article><h2>{html.escape(e["name"])}</h2><p>指令：{html.escape(e["command"])}</p><a href="{html.escape(e["file"])}"><img loading="lazy" src="{html.escape(e["file"])}"></a></article>' for e in entries)
    (OUT/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Warframe 任务图片检查</title><style>body{background:#eaf1f6;font:16px sans-serif;margin:30px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(620px,1fr));gap:20px}article{background:white;padding:16px;border-radius:12px}img{width:100%;max-height:950px;object-fit:contain;object-position:top}h2{font-size:20px}</style><h1>任务图片与图标测试包</h1><p>全部为离线测试数据（统一宽度 1900px）；点击图片查看原图。完整列表见 manifest.json，图标检查见 icon-audit.json。</p><main>'+links+'</main>')
    (OUT/'说明.txt').write_text('本包使用当前插件真实 formatter → presentation → renderer 生成（全部图片宽度统一固定为 1900px）。全部为离线测试数据，不代表实时排期或报价。\n打开 index.html 浏览；images 为原始 PNG；manifest.json 列出对应指令。\n世界任务涵盖裂缝三类、突击、执刑官、警报、入侵、仲裁、科研、赏金等，并额外包含市场、紫卡、玄骸和图标检查矩阵。\n非任务的管理、订阅操作、OCR 输入流程不在任务样图范围内。\n')
    for old_jpg in OUT.glob('总览_*.jpg'):
        old_jpg.unlink(missing_ok=True)
    thumbw,thumbh=475,650;font=ImageFont.truetype(str(FONT),32)
    for start in range(0,len(entries),24):
        batch=entries[start:start+24];im=Image.new('RGB',(thumbw*4,thumbh*math.ceil(len(batch)/4)),'#eaf1f6');d=ImageDraw.Draw(im)
        for i,e in enumerate(batch):
            x=(i%4)*thumbw;y=(i//4)*thumbh
            with Image.open(OUT/e['file']) as src:
                thumb=ImageOps.contain(src.convert('RGB'),(thumbw-20,thumbh-68));im.paste(thumb,(x+(thumbw-thumb.width)//2,y+58))
            d.text((x+12,y+12),f'{start+i+1:03d} {e["name"][:11]}',font=font,fill='#163d57')
        im.save(OUT/f'总览_{start//24+1}.jpg',quality=90)
    shutil.rmtree(OUT/'.render',ignore_errors=True)
    dest=ROOT/'dist/Warframe任务图片测试包-2026-11-08.zip'
    with ZipFile(dest,'w',ZIP_DEFLATED) as z:
        for p in OUT.rglob('*'):
            if p.is_file():z.write(p,p.relative_to(OUT))
    with ZipFile(dest) as z:assert z.testzip() is None
    print(dest,round(dest.stat().st_size/1024**2,1),'MiB')

if __name__=='__main__':asyncio.run(main())
