import json
import unittest
import test_core
from wf_plugin.commands import normalize_prefix
from wf_plugin.routing import route
from wf_plugin.presentation import present
from wf_plugin.core.commands import Reply
from wf_plugin.core.parser import COMMAND_ALIASES,parse_wr
from wf_plugin.core import formatters as fmt
from wf_plugin.core.commands.market import MarketCommands


def blocks(cards):
    return [b for c in cards for b in (c.blocks or [c])]

class NativeTests(unittest.TestCase):
    def test_all_routes_are_direct(self):
        for key,aliases in COMMAND_ALIASES.items():
            for alias in aliases:
                for prefix in ('','/','.'):
                    normalized=normalize_prefix(prefix+alias)
                    self.assertIsNotNone(normalized,(key,alias))
                    self.assertEqual(route(normalized).key,key,(alias,key))
        self.assertIsNone(normalize_prefix('sdjk 帮助'))
        self.assertIsNone(normalize_prefix('遗物 古纪A1',prefixes=['/']))
        self.assertEqual(route(normalize_prefix('/wm水晶p头')).key,'wm')
        self.assertEqual(route('奸商 预测').parsed.content,['预测'])

    def test_market_compatibility_and_strict_filters(self):
        from wf_plugin.core.parser import parse_wm
        parsed=route('wm 膛线 -rank=10 -buy').parsed
        q=parse_wm(parsed.content)
        self.assertEqual(q.rank,10);self.assertTrue(q.buy)
        q=parse_wr(route('wmr 托里德 暴击率 多重 -变焦 -rank=8 -all').parsed.content)
        self.assertEqual(q.mod_rank,8)
        self.assertEqual(q.status,'offline')
        self.assertFalse(q.allow_relaxed)
        self.assertEqual(len(q.stats),2)
        self.assertEqual(len(q.negatives),1)
        self.assertTrue(parse_wr(['托里德','近似']).allow_relaxed)
        a={'item':{'mod_rank':7,'attributes':[]}}
        self.assertFalse(MarketCommands._auction_match(a,q,set()))

    def test_market_has_separate_fields_from_records(self):
        orders=[{'order_type':'sell','visible':True,'platinum':15,'quantity':3,'mod_rank':8,'user':{'ingame_name':'Player_A','status':'ingame','reputation':20}}]
        title,lines,_,_=fmt.fmt_wm_orders('测试 MOD',orders)
        views=blocks(present(Reply(title,fmt.limit_notes(lines))))
        view=next(b for b in views if b.columns[0]=='卖家')
        self.assertEqual([c[1] for c in view.rows[0]][:3],['wm_user','wm_quantity','wm_price'])
        self.assertEqual(view.rows[0][0][0],'Player_A')
        self.assertIn('15 白金',view.rows[0][2][0])

    def test_fissures_have_icons_colors_and_all_columns(self):
        title,lines=fmt.fmt_fissures([{'expiry':'2099-01-01T00:00:00Z','tier':'Lith','missionType':'Defense','node':'Stephano (Uranus)','enemy':'Grineer','isHard':True}],all_rows=True)
        views=blocks(present(Reply(title,lines)))
        view=next(b for b in views if b.columns[0]=='遗物等级')
        self.assertEqual(len(view.columns),6)
        self.assertEqual(view.rows[0][0][0].icon,'lith')
        self.assertEqual(view.rows[0][3][0].icon,'grineer')
        self.assertIn('天王星',view.rows[0][2][0])
        self.assertEqual(view.rows[0][1][1],'fissure_type')

    def test_relic_chance_does_not_shift_to_currency(self):
        title,lines=fmt.fmt_relic_rewards('古纪A1',[{'rarity':'金','name':'蓝图','chance':2}])
        view=next(b for b in blocks(present(Reply(title,lines))) if b.columns[0]=='稀有度')
        self.assertEqual([str(c[0]) for c in view.rows[0]],['金','蓝图','—','—','—','2%'])

    def test_ranges_charts_actions_and_no_information_loss(self):
        from wf_plugin.core.commands.base import Action
        ranges={'cols':['2+0','2+1','3+0','3+1'],'rows':[['火焰伤害','1','2','3','4']],'primary':0}
        chart={'title':'价格','unit':'白金','labels':['a','b','c'],'values':[10,None,20]}
        reply=Reply(title='测试',pages=[('第一页',['§RANGES'+json.dumps(ranges)]),('第二页',['§CHART'+json.dumps(chart),'⟦v⟧说明⟦/v⟧'])],whisper=['/w Player_1 hello'],actions=[Action('下一页','遗物 A1 -2')])
        views=blocks(present(reply));cells=[str(t) for b in views for row in b.rows for t,_ in row]
        self.assertTrue(all(x in cells for x in ['火焰伤害','1','2','3','4','说明','/w Player_1 hello','无数据']))
        self.assertTrue(any('遗物 A1 -2' in x for x in cells))
        self.assertTrue(any(len(b.columns)==5 for b in views))
        self.assertTrue(any(b.chart and b.chart['values']==[10,None,20] for b in views))
        self.assertFalse(any('§RANGES' in x or '⟦' in x for x in cells))

    def test_error_not_generic_two_column_table(self):
        views=blocks(present(Reply(raw_text='错误\n请重试')))
        self.assertEqual(len(views[0].columns),1)
        self.assertEqual([r[0][0] for r in views[0].rows],['错误','请重试'])

    def test_native_configuration_and_panel_schema(self):
        from wf_plugin.settings import GameConfig
        from wf_plugin.core.webpanel import load_schema
        parent={'sdjk':{'vision_provider_id_scan':'chosen/model','push_interval':60}}
        config=GameConfig(parent)
        self.assertEqual(config['vision_provider_id_scan'],'chosen/model')
        self.assertTrue(config['vision_routes_isolated'])
        config['page_size']=7;config['default_platform']='ps';config.save_config()
        self.assertNotIn('sdjk',parent)
        self.assertEqual(parent['default_platform'],'ps4')
        self.assertEqual(GameConfig(parent)['page_size'],7)
        schema=load_schema()
        for field in ('vision_provider_id_scan','push_interval','worldsource'):
            self.assertIn(field,schema)
        self.assertNotIn('render_mode',schema)
        self.assertNotIn('game',schema)

    def test_auction_positive_and_negative_cells_separate(self):
        auction={'id':'sample','buyout_price':25,'owner':{'ingame_name':'TestSeller','status':'ingame'},'item':{'mod_rank':8,'attributes':[{'url_name':'critical_chance','value':150,'positive':True},{'url_name':'zoom','value':35,'positive':False}]}}
        title,lines,_=fmt.fmt_wr_auctions('托里德',[auction])
        views=blocks(present(Reply(title,lines)))
        block=next(b for b in views if b.columns==('卖家','价格','正面词条','负面词条'))
        self.assertEqual(block.rows[0][2][1],'riven_stat')
        self.assertEqual(block.rows[0][3][1],'riven_negative')
        self.assertIn('TestSeller',block.rows[0][0][0])
        self.assertIn('25 白金',block.rows[0][1][0])
