import unittest
from test_core import Command
from wf_plugin.display_icons import line_icon, ELEMENT_ICONS
from wf_plugin.renderer import CardRenderer, FONT
from PIL import ImageFont

class DisplayIconTests(unittest.TestCase):
    def test_currency_context(self):
        for text in ['100 白金','原价 100 白金','55 platinum']:
            self.assertEqual(line_icon(text,'wm_price'),'platinum')
        for text,role in [('白金','text'),('100 白金','wm_user'),('/w User buy for 100 platinum','text'),('https://example.com/100platinum','text')]:
            self.assertEqual(line_icon(text,role),'')

    def test_credits(self):
        self.assertEqual(line_icon('100 星币','wm_price'),'credits')

    def test_elements_and_multiple_stats(self):
        for label,icon in ELEMENT_ICONS.items():
            for text in [label+'伤害','正 · '+label+'伤害 100%',label+' 55%','-30% '+label+'伤害']:
                self.assertEqual(line_icon(text,'riven_stat'),icon,text)
        self.assertEqual(line_icon('火焰风暴','title'),'')
        self.assertEqual(line_icon('病毒','wm_user'),'')
        font=ImageFont.truetype(str(FONT),28)
        lines,icons=CardRenderer.wrap_cell('正 · 火焰伤害 100%\n负 · 冰冻伤害 -30%','riven_stat',font,280,28)
        self.assertEqual([i for i in icons if i],['heat','cold'])
        self.assertEqual(len(lines),len(icons))


class PolarityPrefixTests(unittest.TestCase):
    def test_display_polarity_prefixes_preserve_icons(self):
        from wf_plugin.display_icons import line_icon
        for prefix in ['正面：','负面：','正 · ','负 · ','负面:']:
            for label,expected in [('病毒 55%','viral'),('暴击伤害 50%','stat_crit_damage'),('多重 50%','stat_multishot'),('对Corpus伤害 50','corpus')]:
                self.assertEqual(line_icon(prefix+label,'riven_stat'),expected)
        self.assertEqual(line_icon('负面：多重 50%','wm_user'),'')
