import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from test_core import ROOT
from wf_plugin.core.commands.daily import DailyCommands
from wf_plugin.core.parser import parse,parse_fissure_filter
from wf_plugin.presentation import present

class FissureQueryTests(unittest.IsolatedAsyncioTestCase):
    async def query(self,text,rows=None):
        base={'expiry':'2099-01-01T00:00:00Z','tier':'Lith','missionType':'Survival','enemy':'Grineer'}
        data=rows or [{**base,'node':'普通'},{**base,'node':'钢铁','isHard':True},{**base,'node':'九重天','isStorm':True}]
        host=SimpleNamespace(client=SimpleNamespace(fissures=AsyncMock(return_value=data)),page_size=12,_worldstate_source=lambda _: '')
        return await DailyCommands._h_fissures(host,parse(text),None,'pc')

    async def test_defaults_and_explicit_types(self):
        for command,expected,label in [('裂缝',['普通'],'普通裂缝'),('裂隙',['普通'],'普通裂缝'),('裂缝 生存',['普通'],'普通裂缝'),('钢铁裂缝',['钢铁'],'钢铁裂缝'),('九重天裂缝',['九重天'],'九重天裂缝'),('裂缝 全部',['普通','钢铁','九重天'],'全部裂缝')]:
            reply=await self.query(command)
            self.assertEqual([r['node'] for r in reply.lines.records],expected,command)
            self.assertIn(label,reply.title)

    async def test_one_image_contains_tasks_not_summary(self):
        rows=[{'expiry':'2099-01-01T00:00:00Z','tier':'Lith','missionType':'Survival','node':f'节点{i}','enemy':'Grineer'} for i in range(35)]
        reply=await self.query('裂缝',rows)
        cards=present(reply,'fissures',page_rows=2)
        self.assertEqual(len(cards),1);self.assertEqual(len(cards[0].rows),35)
        self.assertIn('节点',cards[0].columns);self.assertNotIn('指标',cards[0].columns)
        self.assertEqual(cards[0].rows[0][0][0].icon,'lith')
        self.assertEqual(cards[0].rows[0][3][0].icon,'grineer')

    async def test_or_groups_and_subscription_unchanged(self):
        reply=await self.query('裂缝 生存,钢铁生存')
        self.assertEqual([r['node'] for r in reply.lines.records],['普通','钢铁'])
        self.assertTrue(parse_fissure_filter('生存').match({'missionType':'Survival','isHard':True}))

    async def test_empty_normal_does_not_fall_back_to_other_types(self):
        reply=await self.query('裂缝',[{'expiry':'2099-01-01T00:00:00Z','tier':'Lith','node':'钢铁','isHard':True}])
        self.assertIn('普通裂缝',reply.title)
        self.assertIn('没有进行中的裂隙',' '.join(reply.lines))
        self.assertEqual(len(present(reply,'fissures')),1)
