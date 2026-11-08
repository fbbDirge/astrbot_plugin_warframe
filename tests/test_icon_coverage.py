import unittest
from test_core import ROOT
from wf_plugin.presentation import sections, cell
from wf_plugin.core import formatters as fmt
from wf_plugin.core.de_worldstate import _parse_sortie
from wf_plugin.display_icons import line_icon, icon_lines
from wf_plugin.world_icons import FACTIONS
from wf_plugin.renderer import load_icon

class IconCoverageTests(unittest.TestCase):
    def test_all_faction_assets(self):
        for icon,label in FACTIONS.values():
            self.assertIsNotNone(load_icon(icon,32),icon)
        for name in ['credits','ducats','endo','kuva','void','true','tau']:
            self.assertIsNotNone(load_icon(name,32),name)
        self.assertEqual(cell('FC_MITW','派系')[0].icon,'murmur')
        self.assertEqual(cell('Infestation','派系')[0].icon,'infested')
        self.assertEqual(cell('unknown','派系')[0].icon,'')

    def test_market_damage_currency(self):
        for text,role,expected in [('G伤 45','riven_stat','grineer'),('对 Corpus 的伤害 45','riven_stat','corpus'),('毒伤 55','riven_stat','toxin'),('火焰','damage','heat'),
            ('对Corpus伤害 45','riven_stat','corpus'),('虚空 20','damage','void'),
            ('25万现金','item_name','credits'),('赤毒 ×20000','item_name','kuva'),('100 白金','wm_price','platinum')]:
            self.assertEqual(line_icon(text,role),expected,text)
        for text,role in [('火焰风暴','item_name'),('100 白金','wm_user'),('Corpus','wm_user')]:
            self.assertEqual(line_icon(text,role),'')
        self.assertEqual([line_icon(s,'damage') for s in icon_lines('切割 30 / 病毒 50','damage')],['slash','viral'])
        self.assertEqual(cell('45','杜卡德')[0].icon,'ducats')

    def test_task_factions_survive_formatting(self):
        cases=[fmt.fmt_alerts([{'mission':{'node':'A','type':'Defense','faction':'FC_CORPUS'}}]),
            fmt.fmt_sortie({'variants':[{'node':'A','missionType':'Defense'}],'faction':'Infestation'}),
            fmt.fmt_archon({'variants':[{'node':'A','missionType':'Defense','faction':'Narmer'}]}),
            fmt.fmt_kuva([{'node':'A','type':'Capture','enemy':'Grineer'}]),
            fmt.fmt_void_storms([{'nodeCn':'A','tier':'Lith','enemy':'Corpus'}])]
        for (title,lines),expected in zip(cases,['corpus','infested','narmer','grineer','corpus']):
            blocks=sections(lines,title)
            icons=[getattr(value,'icon','') for b in blocks for row in b.rows for value,role in row]
            self.assertIn(expected,icons,title)
        data=_parse_sortie({'Boss':'SORTIE_BOSS_NIRA','Missions':[{}]},archon=True)
        self.assertEqual(data['variants'][0]['faction'],'Narmer')

    def test_invasion_separate_sides(self):
        title,lines=fmt.fmt_invasions([{'node':'A','attacker':{'faction':'Grineer','items':['A reward']},'defender':{'faction':'Corpus','items':['B reward']}}])
        block=next(b for b in sections(lines,title) if '派系' in b.columns)
        self.assertEqual([r[1][0].icon for r in block.rows],['grineer','corpus'])
        self.assertEqual([str(r[3][0]) for r in block.rows],['A reward','B reward'])
