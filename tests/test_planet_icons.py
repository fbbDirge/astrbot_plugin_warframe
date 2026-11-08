import unittest,tempfile
from test_core import ROOT
from wf_plugin.planet_icons import PLANET_ASSETS,planet_icon,nodes
from wf_plugin.presentation import cell,present,table
from wf_plugin.renderer import CardRenderer,load_icon
from wf_plugin.display_icons import line_icon
from wf_plugin.theme import theme_from
from wf_plugin.core.commands import Reply
from wf_plugin.core import formatters as f

class PlanetIconTests(unittest.TestCase):
 def test_planets_nodes_and_assets(self):
  for icon in PLANET_ASSETS:self.assertIsNotNone(load_icon(icon,40),icon)
  for text,expected in [('Stephano (Uranus)','uranus'),('Stephano（天王星）','uranus'),('Stephano','uranus'),('SolNode1','neptune'),('地球比邻星域','earth'),('Veil Proxima','veil'),('Taveuni（赤毒要塞）','kuvafortress'),('扎里曼号','zariman'),('霍瓦尼亚','earth'),('深溯池，火卫二','deimos')]:self.assertEqual(planet_icon(text),'planet_'+expected,text)
  self.assertGreater(len(nodes()),300)
  self.assertFalse(planet_icon('未知节点'))
  self.assertFalse(planet_icon('地图（地球）和地图（金星）'))
 def test_context_isolation(self):
  for header in ('卖家','玩家','用户','奖励','伤害','派系'):
   self.assertFalse(getattr(cell('Mars',header)[0],'icon',''),header)
  self.assertEqual(cell('Grineer','派系')[0].icon,'grineer')
  self.assertEqual(line_icon('虚空伤害','damage'),'void')
  self.assertFalse(line_icon('Mars','wm_user'))
  for header in ('节点','星球','地图','地区','地区信息'):
   self.assertEqual(cell('Mars',header)[0].icon,'planet_mars')
 def test_task_reports(self):
  for title,lines in [f.fmt_sortie({'variants':[{'node':'Stephano (Uranus)','missionType':'Defense','faction':'Grineer'}]}),f.fmt_events([{'name':'测试活动','node':'Earth','rewards':['福马蓝图']}])]:
   cards=present(Reply(title,lines))
   icons=[getattr(v,'icon','') for c in cards for b in c.blocks for row in b.rows for v,role in row]
   self.assertTrue(any(i.startswith('planet_') or i=='cycle_earth' for i in icons),title)
   with tempfile.TemporaryDirectory() as tmp:
    for c in cards:self.assertTrue(CardRenderer(tmp).render(c,theme_from({})).is_file())
