import tempfile
import unittest
from pathlib import Path
from PIL import Image
from test_core import Command
from wf_plugin.world import render_world
from wf_plugin.world_icons import mission_cell, relic_cell
from wf_plugin.renderer import CardRenderer, load_icon, ICON_NAMES
from wf_plugin.theme import theme_from


class WorldIconTests(unittest.TestCase):
    def test_factions_missing_and_unknown(self):
        for faction in ['Grineer','Corpus','Infested','Sentient']:
            cell=mission_cell('防御',{'enemy':faction})
            self.assertEqual(cell.icon,faction.lower())
        self.assertEqual(mission_cell('防御',{'node':'Earth'}).icon,'')
        self.assertEqual(mission_cell('防御',{'faction':'FutureFaction'}),'防御\nFutureFaction')
        self.assertEqual(mission_cell('防御',{'faction':'FutureFaction'}).icon,'')
        self.assertEqual(mission_cell('防御',{},'Grineer').icon,'grineer')

    def test_tasks_use_enemy_and_relic_tier(self):
        data={'fissures':[{'tier':'Lith','node':'Test','enemy':'Corpus','missionType':'Defense','expiry':'2099-01-01T00:00:00Z'}]}
        card=render_world(Command('裂缝'),data)
        self.assertEqual(card.rows[0][0][0].icon,'lith')
        self.assertEqual(card.rows[0][2][0].icon,'corpus')
        self.assertIn('C佬',card.rows[0][2][0])
        data={'alerts':[{'expiry':'2099-01-01T00:00:00Z','mission':{'node':'Test','type':'Hive','faction':'Infested'}}]}
        card=render_world(Command('警报'),data)
        self.assertEqual(card.rows[0][1][0].icon,'infested')
        self.assertEqual(relic_cell('全能','Omnia').icon,'')

    def test_bundled_assets_and_path_restriction(self):
        for key in ICON_NAMES:
            icon=load_icon(key,40)
            self.assertIsNotNone(icon,key)
            self.assertLessEqual(max(icon.size),40)
        self.assertIsNone(load_icon('../../etc/passwd',40))
        self.assertIsNone(load_icon('unknown',40))

    def test_render_at_large_font(self):
        data={'fissures':[{'tier':t,'node':'Stephano (Uranus)','enemy':e,'missionType':'Mobile Defense','expiry':'2099-01-01T00:00:00Z'} for t,e in [('Lith','Grineer'),('Meso','Corpus'),('Neo','Infested'),('Axi','Sentient')]]}
        card=render_world(Command('裂缝'),data)
        with tempfile.TemporaryDirectory() as directory:
            renderer=CardRenderer(directory)
            for size in [28,40]:
                path=renderer.render(card,theme_from({}, {'font_size':size,'fissure_type':'#008866'}))
                with Image.open(path) as im:
                    self.assertEqual(im.width,1900)
                    self.assertGreater(im.height,400)
