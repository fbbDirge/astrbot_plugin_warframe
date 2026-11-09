import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock
import test_core
from wf_plugin.core import china_worldstate as cn
from wf_plugin.core.api_client import WarframeAPIError, WarframeClient
from wf_plugin.routing import route
from wf_plugin.core.parser import normalize_platform

class ChinaTests(unittest.IsolatedAsyncioTestCase):
    def test_route_and_policy(self):
        for text in ['裂缝 -cn','突击 -cn','wm 猴子 -cn']:
            self.assertEqual(route(text).parsed.platform,'cn')
        self.assertEqual(normalize_platform('国服'),'cn')
        self.assertEqual(normalize_platform('wegame'),'cn')
        self.assertTrue(cn.command_error('wm'))
        self.assertTrue(cn.command_error('arbitration'))
        self.assertTrue(cn.command_error('voidtrader',['预测']))
        self.assertFalse(cn.command_error('fissures'))

    def test_normalize_types_without_changing_ids(self):
        row=cn.normalize({'id':'001234','active':'1','expired':'','isHard':'0','tierNum':'1','enemyKey':'Grineer','credits':'50000','activation':'2026-11-09T00:00:00Z'})
        self.assertEqual(row['id'],'001234')
        self.assertIs(row['active'],True)
        self.assertIs(row['expired'],False)
        self.assertIs(row['isHard'],False)
        self.assertEqual(row['tier'],'Lith')
        self.assertEqual(row['credits'],50000)

    def test_reject_error_and_stale_response(self):
        for payload in [{'status':'0','data':'-13'}, {'status':'1','data':{}}, {'status':'1','data':{'timestamp':(datetime.now(timezone.utc)-timedelta(hours=2)).isoformat()}}]:
            with self.assertRaises(WarframeAPIError): cn.validate(payload)
        cn.validate({'status':'1','data':{'timestamp':datetime.now(timezone.utc).isoformat()}})

    async def test_cn_never_uses_international_fallback(self):
        client=WarframeClient()
        client._resilient_de_bundle=AsyncMock(side_effect=AssertionError('international data'))
        client._fetch_json=AsyncMock(return_value={'status':'1','data':{'timestamp':datetime.now(timezone.utc).isoformat(),'fissures':[]}})
        try:
            self.assertEqual(await client.worldstate('cn','fissures'),[])
            client._resilient_de_bundle.assert_not_called()
            args=client._fetch_json.call_args
            self.assertEqual(args.kwargs['headers']['X-Requested-With'],'XMLHttpRequest')
            self.assertIn('wegame:cn',args.kwargs['cache_key'])
            with self.assertRaises(WarframeAPIError): await client.worldstate('cn','arbitration')
        finally: await client.close()

    def test_wegame_shapes_match_renderers(self):
        data=cn.adapt_bundle({
            'archonHunt':{'boss':'SORTIE_BOSS_AMAR','missions':[{'node':'测试节点','type':'防御'}]},
            'conclaveChallenges':[{'description':'赢得比赛','amount':'6','daily':''}],
            'flashSales':[{'item':'测试礼包','expiry':'2026-12-01T00:00:00Z'}],
            'events':[{'description':'测试活动','rewards':[{'items':['测试物品'],'credits':'50000'}]}],
            'constructionProgress':{'fomorianProgress':'57.49','razorbackProgress':'71.17'},
            'invasions':[{'completion':'82.5','vsInfestation':'','attacker':{'factionKey':'Corpus'}}]})
        self.assertEqual(data['archonHunt']['variants'][0]['missionType'],'防御')
        self.assertEqual(data['conclaveChallenges'][0]['text'],'赢得比赛')
        self.assertEqual(data['conclaveChallenges'][0]['cat'],'每周')
        self.assertEqual(data['flashSales'][0]['name'],'测试礼包')
        self.assertEqual(data['events'][0]['rewards'],['测试物品','50000 星币'])
        self.assertAlmostEqual(data['constructionProgress']['projects'][0]['pct'],57.49)
        self.assertEqual(data['invasions'][0]['completion'],82.5)
        self.assertEqual(data['invasions'][0]['attackingFaction'],'Corpus')

    async def test_real_client_decodes_gbk(self):
        import json,httpx
        payload={'status':'1','data':{'timestamp':datetime.now(timezone.utc).isoformat(),'fissures':[{'id':'fixture','node':'地球','tierNum':'1','isHard':''}]}}
        raw=json.dumps(payload,ensure_ascii=False).encode('gb18030')
        client=WarframeClient()
        await client._http.aclose()
        client._http=httpx.AsyncClient(transport=httpx.MockTransport(lambda request:httpx.Response(200,content=raw)))
        try:
            rows=await client.fissures('cn')
            self.assertEqual(rows[0]['node'],'地球')
            self.assertIs(rows[0]['isHard'],False)
            self.assertEqual(rows[0]['tier'],'Lith')
        finally:await client.close()
