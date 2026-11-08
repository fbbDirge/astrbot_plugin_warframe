import tempfile,unittest
from test_core import ROOT
from wf_plugin.component_art import component_icon,files
from wf_plugin.renderer import load_icon,CardRenderer,FONT
from wf_plugin.presentation import present,table
from wf_plugin.core import formatters as fmt
from wf_plugin.core.commands import Reply
from wf_plugin.theme import theme_from
from wf_plugin.weapon_art import decorate
from PIL import ImageFont

def relic_card():
    from wf_plugin.core.viewmodel import DataLines
    names=['Forma 蓝图','野马 Prime 枪机','阿利乌双枪 Prime 枪管','Grendel Prime 系统蓝图','迅发电浆炮 Prime 枪机','咀嚼金杖 Prime 刀刃']
    records=[{'name':n,'rarity':r} for n,r in zip(names,['常见']*3+['罕见']*2+['稀有'])]
    prices={n:{'plat':p,'ducats':d,'dpp':round(d/p,2)} for n,p,d in zip(names[1:],[3.,10.,35.,7.,18.],[15,15,65,45,100])}
    return present(Reply('遗物：中纪 M6',DataLines([],domain='relic',records=records,meta={'prices':prices})))[0]

class ComponentArtTests(unittest.TestCase):
    def test_assets_shared_parts_and_blueprints(self):
        for key in files():self.assertIsNotNone(load_icon('component:'+key,40),key)
        self.assertEqual(component_icon('野马 Prime 枪机'),component_icon('迅发电浆炮 Prime 枪机'))
        self.assertNotEqual(component_icon('野马 Prime 枪机'),component_icon('野马 枪机'))
        for name in ['Grendel Prime 系统蓝图','Ash Prime 机体','Ash Prime 头部神经光元','咀嚼金杖 Prime 刀刃','Orthos Prime Handle','Paris Prime Upper Limb','Burston Prime Stock']:
            self.assertIsNotNone(load_icon(component_icon(name),40),name)
        for name in ['Forma 蓝图','Braton Prime Blueprint','Wukong Prime 蓝图']:
            self.assertTrue(component_icon(name).startswith('blueprint:'),name)
            self.assertIsNotNone(load_icon(component_icon(name),40),name)
        self.assertEqual(component_icon('未知武器蓝图'),'')
        c=table('市场',['卖家','价格'],[['野马 Prime 枪机','10 白金']]);decorate(c)
        self.assertFalse(getattr(c.rows[0][0][0],'icon',''))
    def test_relic_icons_and_compact_currency(self):
        c=relic_card();decorate(c);b=c.blocks[0]
        self.assertTrue(all(getattr(r[1][0],'icon','') for r in b.rows))
        font=ImageFont.truetype(str(FONT),26)
        for v in ['3.0 白金','10.0 白金','35.0 白金','18.0 白金']:
            lines,icons=CardRenderer.wrap_cell(v,'wm_price',font,110,27)
            self.assertEqual(len(lines),1);self.assertEqual(icons,['platinum']);self.assertNotIn('白',lines[0])
        with tempfile.TemporaryDirectory() as tmp:
            for size in [26,42]:self.assertTrue(CardRenderer(tmp).render(c,theme_from({'font_size':size})).is_file())

    def test_archwing_export_tag_and_system_blueprint(self):
        from wf_plugin.equipment_art import exact_equipment
        from wf_plugin.presentation import cell
        tagged='<ARCHWING> 陨蜓 Prime 蓝图'
        self.assertEqual(exact_equipment(tagged),exact_equipment('Odonata Prime Blueprint'))
        self.assertEqual(cell(tagged,'奖励')[0],'陨蜓 Prime 蓝图')
        c=table('遗物奖励',['奖励'],[[tagged],['陨蜓 Prime 系统蓝图']]);decorate(c)
        for row in c.rows:self.assertIsNotNone(load_icon(row[0][0].icon,40))
        self.assertTrue(c.rows[0][0][0].icon.startswith('blueprint:equipment:'))
        self.assertEqual(c.rows[1][0][0].icon,'equipment:'+exact_equipment('Odonata Prime Systems'))
        self.assertNotEqual(exact_equipment('Odonata Prime Systems'),exact_equipment('Volt Prime Systems'))
        self.assertEqual(cell('<UNKNOWN> 名称','奖励')[0],'<UNKNOWN> 名称')
