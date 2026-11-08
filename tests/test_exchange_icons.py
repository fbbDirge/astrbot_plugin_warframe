import unittest,tempfile,json
from test_core import ROOT
from wf_plugin.core import formatters as f
from wf_plugin.core.commands import Reply
from wf_plugin.presentation import present
from wf_plugin.renderer import CardRenderer,load_icon
from wf_plugin.weapon_art import decorate
from wf_plugin.exchange_icons import item_icon,currency_icon
from wf_plugin.theme import theme_from

class ExchangeIconsTests(unittest.TestCase):
 def test_vendors_events_calendar(self):
  cases=[f.fmt_steel_essence_shop(),f.fmt_sliver_shop(),f.fmt_acrichis_week({'items':[{'name':'奥罗金催化剂蓝图','price':20}]}),f.fmt_prime_vault({'items':[{'name':'Volt Prime','prime':3},{'name':'测试披饰','prime':2}]}),f.fmt_events([{'name':'测试活动','rewards':['福马蓝图','1000 星币','测试礼包']}]),f.fmt_calendar({'days':[{'date':'2026-11-08','events':[{'type':'REWARD','name':'福马蓝图'}]}]}),f.fmt_void_trader({'active':True,'inventory':[{'item':'膛线 Prime','ducats':400,'credits':100000}]})]
  for title,lines in cases:
   cards=present(Reply(title,lines))
   rewards=[]
   with tempfile.TemporaryDirectory() as tmp:
    for c in cards:
     decorate(c)
     for b in c.blocks:
      for row in b.rows:
       for v,role in row:
        if role=='item_name' and not str(v).startswith('['):
         rewards.append(v);self.assertTrue(getattr(v,'icon',''),(title,str(v)));self.assertIsNotNone(load_icon(v.icon,40))
     self.assertTrue(CardRenderer(tmp).render(c,theme_from({})).is_file())
   self.assertTrue(rewards,title)
 def test_exact_amounts_and_isolation(self):
  self.assertEqual(item_icon('3 × Forma'),item_icon('Forma'))
  self.assertTrue(item_icon('安魂遗物 IV'))
  self.assertTrue(item_icon('Umbra Forma 蓝图').startswith('blueprint:'))
  self.assertFalse(item_icon('未知物品'))
  self.assertFalse(currency_icon('这里需要一些苦栓'))
