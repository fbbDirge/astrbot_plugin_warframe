import asyncio
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from test_core import Command, QueryError, WarframeService, parse
from wf_plugin.cards import Card
from wf_plugin.renderer import CardRenderer
from wf_plugin.theme import ThemeStore, theme_from
from wf_plugin.world import render_world


class ImageTests(unittest.TestCase):
    def test_personal_preferences_persist_and_isolate(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ThemeStore(tmp)
            store.handle('a','wf 配色 价格 #FF8800')
            store.handle('a','wf 字号 32')
            self.assertEqual(ThemeStore(tmp).get('a')['wm_price'],'#FF8800')
            self.assertEqual(store.get('b'),{})
            for command in ['wf 配色 价格 red','wf 字号 100','wf 背景 ../secret.png']:
                with self.assertRaises(QueryError): store.handle('a',command)
            store.handle('a','wf 主题 重置')
            self.assertEqual(store.get('a'),{})

    def test_background_selection_and_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ThemeStore(tmp)
            Image.new('RGB',(32,32),'navy').save(store.backgrounds/'custom.png')
            store.handle('a','wf 背景 custom.png')
            self.assertTrue(store.get('a')['background_image'].endswith('custom.png'))
            store.handle('a','wf 背景 #FFEEEE')
            self.assertEqual(store.get('a')['background_image'],'')
            store.handle('a','wf 背景 默认')
            self.assertEqual(store.get('a'),{})

    def test_semantic_colors_and_background_reach_pixels(self):
        card = Card('test',title='WM 测试',columns=('玩家','数量','价格','状态'),rows=[[
            ('Player','wm_user'),('12','wm_quantity'),('100 白金','wm_price'),('游戏中','muted')]])
        with tempfile.TemporaryDirectory() as tmp:
            theme = theme_from({}, {'wm_user':'#FF0000','wm_quantity':'#00FF00','wm_price':'#0000FF','background_color':'#FFEEDD'})
            path = CardRenderer(tmp).render(card,theme)
            with Image.open(path) as img:
                colors = set(img.getdata())
                for color in [(255,0,0),(0,255,0),(0,0,255)]: self.assertIn(color,colors)
                self.assertEqual(img.getpixel((0,0)),(255,238,221))

    def test_custom_background_and_large_text_wrap(self):
        with tempfile.TemporaryDirectory() as tmp:
            bg = Path(tmp)/'bg.png'; Image.new('RGB',(100,100),'#112233').save(bg)
            theme = theme_from({}, {'background_image':str(bg),'font_size':42})
            renderer = CardRenderer(tmp)
            text = '非常长的地图名称' * 10
            font = __import__('PIL.ImageFont',fromlist=['truetype']).truetype(str(__import__('wf_plugin.renderer',fromlist=['FONT']).FONT),42)
            self.assertTrue(all(font.getlength(x)<=200 for x in renderer.wrap(text,font,200)))
            path = renderer.render('标题\n'+text,theme)
            with Image.open(path) as img: self.assertEqual(img.getpixel((0,0)),(17,34,51))

    def test_fissure_metadata_survives_pagination(self):
        data = {'fissures':[{'tier':'Lith','node':'Very Long Map','missionType':'Capture','expiry':'2099-01-01T00:00:00Z'}]*6}
        card = render_world(Command('裂缝',page=2),data,5)
        self.assertIsInstance(card,Card)
        self.assertEqual(len(card.rows),1)
        self.assertEqual([role for _,role in card.rows[0]],['tier_lith','fissure_map','fissure_type','muted'])

    def test_all_world_and_theme_outputs_are_structured_cards(self):
        data = {
            'timestamp': '2026-11-07T06:00:00Z',
            'cetusCycle': {'state': 'day', 'expiry': '2099-01-01T00:00:00Z'},
            'sortie': {'boss': 'Vor', 'expiry': '2099-01-01T00:00:00Z', 'variants': [{'node': 'Earth', 'missionType': 'Defense', 'modifier': 'Eximus'}]},
            'voidTrader': {'character': 'Baro', 'location': 'Kronia', 'activation': '2099-01-01T00:00:00Z', 'expiry': '2099-01-02T00:00:00Z', 'inventory': [{'item': 'Primed Continuity', 'ducats': 350, 'credits': 100000}]},
            'steelPath': {'currentReward': {'name': 'Umbra Forma Blueprint', 'cost': 150}, 'expiry': '2099-01-01T00:00:00Z'},
            'invasions': [{'node': 'Mars', 'completion': 45.5, 'attacker': {'reward': {'items': ['Fieldron']}}, 'defender': {'reward': {'items': ['Detonite']}}}],
            'nightwave': {'activeChallenges': [{'title': 'Daily', 'desc': 'Kill 100', 'reputation': 1000, 'expiry': '2099-01-01T00:00:00Z'}]},
            'dailyDeals': [{'item': 'Forma', 'salePrice': 15, 'originalPrice': 20, 'total': 100, 'sold': 40, 'expiry': '2099-01-01T00:00:00Z'}],
            'news': [{'date': '2099-01-01T00:00:00Z', 'message': 'Update', 'link': 'https://www.warframe.com'}],
            'arbitration': {'node': 'Hydron', 'type': 'Defense', 'expiry': '2099-01-01T00:00:00Z'},
            'sentientOutposts': {'mission': {'node': 'Veil', 'faction': 'Sentient'}, 'expiry': '2099-01-01T00:00:00Z'},
            'alerts': [{'mission': {'node': 'Lua', 'type': 'Rescue', 'reward': {'credits': 10000}}, 'expiry': '2099-01-01T00:00:00Z'}],
            'events': [{'description': 'Plague Star', 'expiry': '2099-01-01T00:00:00Z'}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            renderer = CardRenderer(tmp)
            theme = theme_from({})
            for cmd in ['时间', '平原', '突击', '奸商', '钢铁之路', '入侵', '夜灵电波', '每日特惠', '新闻', '仲裁', '地幔', '警报', '活动', '地球']:
                card = render_world(Command(cmd), data)
                self.assertIsInstance(card, Card, cmd)
                self.assertTrue(card.columns and card.rows and card.footer, cmd)
                self.assertTrue(renderer.render(card, theme).is_file())
            store = ThemeStore(tmp)
            for tcmd in ['wf 主题', 'wf 前缀', 'wf 背景', 'wf 配色 价格 #FF8800', 'wf 主题 重置']:
                card = store.handle('u', tcmd)
                self.assertIsInstance(card, Card, tcmd)
                self.assertTrue(card.columns and card.rows and card.footer, tcmd)
                self.assertTrue(renderer.render(card, theme).is_file())


if __name__ == '__main__': unittest.main()
