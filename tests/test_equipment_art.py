import unittest
from test_core import ROOT
from wf_plugin.equipment_art import catalog,exact_equipment,title_equipment,equipment_path
from wf_plugin.weapon_art import decorate
from wf_plugin.presentation import table
from wf_plugin.renderer import load_icon

class EquipmentArtworkTests(unittest.TestCase):
    def test_catalog_and_categories(self):
        import json
        data=json.loads((ROOT/'assets/equipment/manifest.json').read_text())
        self.assertFalse(data['failed']);self.assertFalse(data['unavailable'])
        self.assertEqual(set(data['counts']),{'warframe','archwing','necramech','amp','kdrive','kitgun','zaw'})
        for path in catalog()[1].values():self.assertTrue(path.is_file(),path)
        for name in ['Wukong Prime','Odonata','Voidrig','Bonewidow','Balla','Haymaker','Raplak Prism','Mote Amp','Bad Baby']:
            key=exact_equipment(name);self.assertIsNotNone(key,name)
            self.assertIsNotNone(load_icon('equipment:'+key,48),name)
        self.assertIsNone(load_icon('equipment:../../main.py',32))

    def test_parts_and_versions(self):
        self.assertNotEqual(exact_equipment('Wukong'),exact_equipment('Wukong Prime'))
        self.assertNotEqual(exact_equipment('Wukong Prime'),exact_equipment('Wukong Prime Chassis'))
        for name in ['Wukong Prime Chassis','Wukong Prime Chassis Blueprint','Odonata Wings']:
            self.assertIsNotNone(exact_equipment(name),name)
        self.assertIsNone(exact_equipment('Unknown Prime Chassis'))
        self.assertIsNone(exact_equipment('Wukong Prime (Unknown Blueprint)'))
        self.assertEqual(title_equipment('Wukong Prime Set 在售单（第1/1页）'),exact_equipment('Wukong Prime'))

    def test_cards_and_usernames(self):
        card=table('装备列表',['物品','数量'],[['Wukong Prime',1],['Raplak Prism',1],['Bad Baby',1]])
        decorate(card)
        self.assertTrue(all(getattr(row[0][0],'icon','').startswith('equipment:') for row in card.rows))
        card=table('市场订单',['卖家','价格'],[['Wukong Prime','100 白金']]);decorate(card)
        self.assertFalse(getattr(card.rows[0][0][0],'icon',''));self.assertIsNone(card.artwork_path)
        card=table('Wukong Prime Chassis 在售单（第1/1页）',['卖家','价格'],[['A','10 白金']]);decorate(card)
        self.assertEqual(card.artwork_path,equipment_path(exact_equipment('Wukong Prime Chassis')))
