import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
import test_core
from PIL import Image
from wf_plugin.core.riven_grade import quality, label
from wf_plugin.core.formatters import RIVEN_DISPLAY_ZH, fmt_riven_analysis
from wf_plugin.stat_icons import STAT_ICONS
from wf_plugin.display_icons import line_icon
from wf_plugin.renderer import load_icon
from wf_plugin.presentation import table

class RivenQualityTests(TestCase):
    def test_direction_boundaries_and_invalid_values(self):
        self.assertEqual(quality(9,0,10),90)
        self.assertEqual(quality(1,0,10,True),90)
        for score, expected in [(90,'S'),(75,'A'),(50,'B'),(25,'C'),(0,'D')]:
            self.assertTrue(label(score).startswith(expected+' '))
        for value in [11,-1,float('nan')]:self.assertIsNone(quality(value,0,10))
        self.assertIsNone(quality(1,None,None))

    def test_all_full_stat_names_units_and_polarities_have_icons(self):
        for sid, expected in STAT_ICONS.items():
            for sign in ['▲','▼']:
                for unit in ['%', 'm', 's', '米', '秒']:
                    text=sign+RIVEN_DISPLAY_ZH[sid]+' +2.3'+unit
                    with self.subTest(text=text):
                        self.assertEqual(line_icon(text,'roll_a'), expected)
                        self.assertIsNotNone(load_icon(expected,24))

    def test_every_display_label_and_inverted_label_matches(self):
        for name in RIVEN_DISPLAY_ZH.values():
            self.assertTrue(line_icon('▲'+name+' +20%', 'roll_s'), name)
        self.assertEqual(line_icon('▲武器后坐力 -20%（卡面-号·正面）','roll_s'), 'stat_recoil')

    def test_failed_load_recovers_without_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'stat_range.png'
            with patch('wf_plugin.renderer.ICON_DIR',Path(tmp)):
                self.assertIsNone(load_icon('stat_range',24))
                path.write_bytes(b'bad image')
                self.assertIsNone(load_icon('stat_range',24))
                Image.new('RGBA',(24,24),'red').save(path)
                self.assertIsNotNone(load_icon('stat_range',24))

    def test_grade_colors_and_unconfirmed_total(self):
        card=table('', ['词条','评分'], [['▲攻击范围 +2.3m','A 77分'],['▼对 Infested 的伤害 -38%','S 95分']])
        self.assertEqual(card.rows[0][0][1],'roll_a')
        self.assertEqual(card.rows[1][0][1],'roll_s')
        _,lines=fmt_riven_analysis('大力士',1.2,'melee',[('attack_speed',63.5),('viral_damage',110.8),('range',2.3)],[('damage_vs_infested',38)],hidden=1)
        self.assertIn('◆ 数值评分：待核对',lines)
