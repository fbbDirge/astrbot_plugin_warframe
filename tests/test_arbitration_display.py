import time,unittest,tempfile
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
from pathlib import Path
from test_core import ROOT
from wf_plugin.core.commands.arbitration import ArbitrationCommands
from wf_plugin.presentation import present
from wf_plugin.renderer import CardRenderer
from wf_plugin.theme import theme_from

async def sample_reply(missing=False):
    start=int(time.time()//3600)*3600
    sched={'startTs':start,'stepSec':3600,'seq':[0] if missing else [0,1,2],'nodes':['a','b','c']}
    nodes={'a':{'nameZh':'Malva','systemNameZh':'金星','missionNameZh':'生存','factionNameZh':'Infestation'},
           'b':{'nameZh':'Tycho','systemNameZh':'月球','missionNameZh':'生存','factionNameZh':'Corpus'},
           'c':{'nameZh':'Amarna','systemNameZh':'赛德娜','missionNameZh':'生存','factionNameZh':'Grineer'}}
    host=SimpleNamespace(_arb_fetch=AsyncMock(return_value=(sched,nodes,{'a':'A','b':'A-','c':'A+'})),_ARB_TYPES_STR='生存 / 防御')
    with patch('wf_plugin.core.arbi.measured_of',return_value={}):
        return await ArbitrationCommands._arb_now(host,'pc')

class ArbitrationDisplayTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_three_slots_have_map_type_faction(self):
        reply=await sample_reply();cards=present(reply,'arbitration',page_rows=1)
        self.assertEqual(len(cards),1);blocks=cards[0].blocks
        self.assertEqual([b.title for b in blocks],['当前仲裁','下一小时','下次高效'])
        for b,icon,node in zip(blocks,['infested','corpus','grineer'],['Malva','Tycho','Amarna']):
            self.assertEqual(b.columns,('地图 / 星球','任务类型','派系','评级'))
            self.assertIn(node,b.rows[0][0][0]);self.assertEqual(b.rows[0][0][1],'fissure_map')
            self.assertEqual(b.rows[0][1][1],'fissure_type');self.assertEqual(b.rows[0][2][0].icon,icon)
        with tempfile.TemporaryDirectory() as tmp:
            for size in (26,42):self.assertTrue(CardRenderer(tmp).render(cards[0],theme_from({}, {'font_size':size})).is_file())

    async def test_end_of_schedule_preserves_notices(self):
        cards=present(await sample_reply(True),'arbitration')
        self.assertEqual(len(cards),1);self.assertEqual(len(cards[0].blocks),1)
        self.assertIn('排期表已到末尾',cards[0].blocks[0].footer)
        self.assertIn('排期内暂无',cards[0].blocks[0].footer)

class ArbitrationColorTests(unittest.TestCase):
    def test_grade_roles_and_custom_colors(self):
        from wf_plugin.presentation import table
        from wf_plugin.theme import ThemeStore, ARBITRATION_COLORS
        labels=['S 630','A+ 754','A 655','A-* 586','A− 504','F 300','未评级','']
        block=table('仲裁时间表',['派系','评级'],[['Corpus',x] for x in labels])
        self.assertEqual([r[1][1] for r in block.rows],['arb_s','arb_a_plus','arb_a','arb_a_minus','arb_a_minus','arb_f','arb_unrated','arb_unrated'])
        self.assertEqual(len(set(ARBITRATION_COLORS.values())),6)
        self.assertEqual(table('紫卡',['词条','评级'],[['伤害','A+']]).rows[0][1][1],'riven_grade')
        with tempfile.TemporaryDirectory() as tmp:
            store=ThemeStore(tmp);store.handle('user','wf 配色 仲裁A+ #123456')
            self.assertEqual(theme_from({},store.get('user'))['arb_a_plus'],'#123456')
            self.assertTrue(CardRenderer(tmp).render(block,theme_from({})).is_file())
