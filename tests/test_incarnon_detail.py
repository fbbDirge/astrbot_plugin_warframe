import json,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from PIL import Image
from test_core import ROOT
from wf_plugin.core.circuit import detail,position
from wf_plugin.core.commands.base import Reply
from wf_plugin.presentation import present
from wf_plugin.renderer import CardRenderer
from wf_plugin.theme import theme_from
from wf_plugin.weapon_art import exact_weapon
from wf_plugin.equipment_art import exact_equipment

class IncarnonDetailTests(unittest.TestCase):
    def setUp(self):self.data=json.loads((ROOT/'core/data/rotations.json').read_text())['incarnon']
    def test_snapshot_and_independent_rotations(self):
        lines=detail(self.data,datetime(2026,11,7,tzinfo=timezone.utc));d=lines.meta
        self.assertEqual(d['frames'],['Ivara','Inaros','Titania'])
        self.assertEqual(d['next_frames'],['Nidus','Octavia','Harrow'])
        self.assertEqual(d['current_week'],0);self.assertEqual(len(d['weeks']),9)
        self.assertEqual(len(d['weapons']),5)
        for name in d['frames']+d['next_frames']:self.assertIsNotNone(exact_equipment(name))
        for week in d['weeks']:
            for w in week:self.assertIsNotNone(exact_weapon(w['identity']),w)
        self.assertNotIn('variant',str(d));self.assertNotIn('评价','\n'.join(lines))

    def test_monday_boundary_and_cycle_wrap(self):
        boundary=datetime(2026,6,29,tzinfo=timezone.utc)
        before=detail(self.data,boundary-timedelta(seconds=1)).meta
        after=detail(self.data,boundary).meta
        self.assertEqual((before['current_week'],after['current_week']),(8,0))
        self.assertEqual(before['remaining_seconds'],1)
        self.assertEqual(after['remaining_seconds'],7*86400)
        self.assertEqual(before['next_weapons'],after['weapons'])
        frames=json.loads((ROOT/'core/data/circuit_frames.json').read_text())
        epoch=datetime.fromisoformat(frames['epoch'])
        self.assertEqual(position(frames,epoch+timedelta(weeks=11))[0],0)

    def test_single_image_large_font_custom_background(self):
        lines=detail(self.data,datetime(2026,11,7,tzinfo=timezone.utc))
        cards=present(Reply('本周回廊战甲与灵化武器',lines),'incarnon',page_rows=1)
        self.assertEqual(len(cards),1)
        with tempfile.TemporaryDirectory() as temp:
            renderer=CardRenderer(temp)
            bg=Path(temp)/'bg.png';Image.new('RGB',(20,20),(40,60,80)).save(bg)
            for size in (26,42):
                path=renderer.render(cards[0],theme_from({'background_image':str(bg)}, {'font_size':size,'item_name':'#008866'}))
                with Image.open(path) as im:
                    self.assertEqual(im.width,1900);self.assertGreater(im.height,800)
                    self.assertEqual(im.getpixel((0,0))[:3],(40,60,80))
