import tempfile,unittest
from datetime import datetime,timedelta,timezone
from test_core import ROOT
from wf_plugin.core.formatters import fmt_cetus,fmt_timers
from wf_plugin.core.commands import Reply
from wf_plugin.presentation import present,cell
from wf_plugin.renderer import CardRenderer,load_icon
from wf_plugin.theme import theme_from
from wf_plugin.cycle_icons import CYCLE_ICONS

def cycle_reply():
    end=(datetime.now(timezone.utc)+timedelta(hours=2)).isoformat()
    title,lines=fmt_cetus(*[{'_name':key,'state':state,'stateCn':cn,'isDay':False,'expiry':end} for key,state,cn in [('cetus','night','夜晚'),('vallis','cold','寒冷'),('cambion','fass','Fass'),('earth','night','夜晚'),('duviri','joy','喜悦'),('zariman','Corpus','Corpus')]])
    return Reply(title,lines,footer='测试数据 · 地区图标预览')

class CycleIconTests(unittest.TestCase):
    def test_names_and_summary(self):
        cards=present(cycle_reply(),'cetus')
        icons=[getattr(v,'icon','') for c in cards for b in c.blocks for row in b.rows for v,r in row]
        self.assertTrue(set(CYCLE_ICONS.values()).issubset(icons))
        self.assertEqual(getattr(cell('夜灵平野（夜晚）')[0],'icon',''),'cycle_cetus')
        for icon in set(CYCLE_ICONS.values()):self.assertIsNotNone(load_icon(icon,40))
        with tempfile.TemporaryDirectory() as tmp:
            for size in (26,42):
                for c in cards:self.assertTrue(CardRenderer(tmp).render(c,theme_from({'font_size':size})).is_file())
    def test_no_username_or_faction_confusion(self):
        self.assertFalse(getattr(cell('地球','卖家')[0],'icon',''))
        self.assertFalse(getattr(cell('双衍王境','用户')[0],'icon',''))
        self.assertEqual(cell('Duviri','派系')[0].icon,'duviri')
        self.assertEqual(cell('地球','名称')[0].icon,'cycle_earth')
        self.assertFalse(getattr(cell('未知地区','名称')[0],'icon',''))
