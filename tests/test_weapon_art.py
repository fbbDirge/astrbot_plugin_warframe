import unittest
from test_core import ROOT
from wf_plugin.weapon_art import catalog, exact_weapon, title_weapon, weapon_path, decorate
from wf_plugin.cards import Card
from wf_plugin.renderer import load_icon
from wf_plugin.presentation import table, sections
from wf_plugin.core import formatters

class WeaponArtworkTests(unittest.TestCase):
    def test_catalog_files_and_known_versions(self):
        aliases,files=catalog()
        self.assertGreater(len(files),600)
        for path in files.values():self.assertTrue(path.is_file(),path)
        self.assertEqual(exact_weapon('托里德'),exact_weapon('Torid'))
        self.assertNotEqual(exact_weapon('Boar'),exact_weapon('Boar Prime'))
        self.assertEqual(exact_weapon('野猪 Prime 一套'),exact_weapon('Boar Prime'))
        self.assertIsNotNone(load_icon('weapon:'+exact_weapon('Torid'),48))
        self.assertIsNone(load_icon('weapon:../../main.py',48))

    def test_no_parts_usernames_or_fuzzy_weapon(self):
        for text in ['Boar Prime Barrel','野猪 Prime 蓝图','Toridish','Future Weapon Prime','Boar (Blueprint)']:
            self.assertIsNone(exact_weapon(text),text)
        card=table('市场订单',['卖家','数量'],[['Torid',1]])
        decorate(card)
        self.assertFalse(getattr(card.rows[0][0][0],'icon',''))
        self.assertIsNone(card.artwork_path)

    def test_native_markets_and_multi_weapon_rows(self):
        for title in ['托里德 紫卡拍卖（第1/1页，共5条）','赤毒布拉玛 玄骸拍卖（5条）','托里德 紫卡词条范围（3正1负）','野猪 Prime 一套 在售单（第1/1页）']:
            self.assertIsNotNone(title_weapon(title),title)
        card=table('武器版本',['武器','原倾向'],[['野猪',1],['野猪 Prime',1]])
        decorate(card)
        self.assertTrue(all(str(row[0][0].icon).startswith('weapon:') for row in card.rows))
        self.assertIsNone(card.artwork_path)
        card=table('托里德 紫卡拍卖（第1/1页）',['卖家','价格'],[['Corpus','100 白金']])
        card.artwork=('https://warframe.market/static/assets/test.png','')
        decorate(card)
        self.assertEqual(card.artwork_path,weapon_path(exact_weapon('Torid')))

    def test_bilingual_damage_report(self):
        blocks=sections(['◆ 输入回显','· 武器　托里德（Torid）｜MR4','· 面板　基伤 100'],'伤害计算')
        report=Card('',title='伤害计算');report.blocks=blocks
        decorate(report)
        self.assertEqual(report.artwork_path,weapon_path(exact_weapon('Torid')))

    def test_native_analysis_weapon_summary(self):
        title,lines=formatters.fmt_riven_analysis('托里德',1.2,'rifle',[],[])
        report=Card('',title=title);report.blocks=sections(lines,title)
        decorate(report)
        self.assertEqual(report.artwork_path,weapon_path(exact_weapon('Torid')))
