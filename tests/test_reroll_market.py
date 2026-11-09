import asyncio,json,tempfile,time,unittest
from unittest.mock import AsyncMock,patch
from pathlib import Path
from types import SimpleNamespace
from test_core import ROOT
from wf_plugin.core import paths
from wf_plugin.core.reroll_market import summarize,market_recommend,_path,_key
from wf_plugin.core.commands.riven import RivenCommands
from wf_plugin.routing import route
from wf_plugin.commands import normalize_prefix
from wf_plugin.presentation import present
from wf_plugin.renderer import CardRenderer
from wf_plugin.theme import theme_from

def auction(i, seller=None,slug='torid',pos=('critical_chance','multishot'),neg=('zoom',),price=100,rank=8):
    return {'id':str(i),'visible':True,'closed':False,'buyout_price':price,'owner':{'id':seller or str(i)},'item':{'type':'riven','weapon_url_name':slug,'mod_rank':rank,'attributes':[{'url_name':s,'positive':p,'value':100} for p,stats in [(True,pos),(False,neg)] for s in stats]}}

class StatTests(unittest.TestCase):
    def test_weights_filtering_and_price_groups(self):
        rows=[auction(i,'bulk') for i in range(10)]+[auction(20,pos=('critical_damage','damage')),auction(21,pos=('critical_damage','damage'))]
        stats=summarize(rows+[rows[0],auction(25,slug='rubico'),{**auction(26),'closed':True}],'torid')
        self.assertEqual(stats['valid'],12);self.assertEqual(stats['sellers'],3);self.assertEqual(stats['excluded'],2)
        chance=next(r for r in stats['positive'] if r['stat']=='critical_chance')
        self.assertAlmostEqual(chance['share'],1/3)
        self.assertTrue(all(c['median'] is None for c in stats['combos']))
        s=summarize([auction(i,price=i*100) for i in range(1,4)]+[auction(9,rank=0,price=1)],'torid')
        c=next(x for x in s['combos'] if x['rank']==8);self.assertEqual(c['median'],200)
        self.assertEqual(len(s['combos']),2)
        mixed=[auction(i,seller='bulk') for i in range(3)]+[auction(4,price=None),auction(5,price=None)]
        self.assertIsNone(summarize(mixed,'torid')['combos'][0]['median'])
        self.assertEqual(summarize([auction(1,price=float('nan'))],'torid')['combos'][0]['price_n'],0)
        with self.assertRaises(ValueError):summarize([{}],'torid')

class MarketTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.previous=paths._RUN;paths.set_run_dir(self.tmp.name)
        self.weapon={'url_name':'torid','zh':'托里德','en':'Torid','riven_type':'rifle'}
        self.client=SimpleNamespace(resolve_riven_weapon=AsyncMock(return_value=self.weapon),wm_riven_auctions=AsyncMock(return_value=[auction(i) for i in range(25)]))
        self.family=patch('wf_plugin.core.commands.market.riven_market_weapon',AsyncMock(return_value=self.weapon));self.family.start()
    async def asyncTearDown(self):
        self.family.stop();paths.set_run_dir(self.previous);self.tmp.cleanup()
    async def test_live_cache_expired_fallback_and_platform(self):
        reply=await market_recommend(self.client,'托里德','pc')
        self.assertNotIn('25 张',''.join(reply.lines));self.assertIn('本次查询成功',''.join(reply.lines))
        self.client.wm_riven_auctions.assert_awaited_once()
        self.assertTrue(self.client.wm_riven_auctions.call_args.kwargs['require_all_sorts'])
        self.client.resolve_riven_weapon.side_effect=RuntimeError('offline')
        self.client.wm_riven_auctions.side_effect=RuntimeError('offline')
        reply=await market_recommend(self.client,'托里德','pc')
        self.assertIn('缓存命中',''.join(reply.lines))
        p=_path('snapshots',_key('pc|torid'));d=json.loads(p.read_text());d['sampled_at']-=86400;p.write_text(json.dumps(d))
        reply=await market_recommend(self.client,'托里德','pc')
        self.assertIn('非实时',''.join(reply.lines));self.assertIn('北京时间',''.join(reply.lines))
        self.assertEqual(json.loads(p.read_text())['sampled_at'],d['sampled_at'])
        other=await market_recommend(self.client,'托里德','ps');self.assertIn('没有',''.join(other.lines))
        cards=present(reply,'reroll');self.assertEqual(len(cards),1)
        self.assertTrue(CardRenderer(self.tmp.name).render(cards[0],theme_from({})).is_file())
    async def test_empty_success_corrupt_cache_and_concurrency(self):
        await asyncio.gather(*(market_recommend(self.client,'托里德','pc') for _ in range(3)))
        self.assertEqual(self.client.wm_riven_auctions.await_count,1)
        self.client.wm_riven_auctions.return_value=[]
        r=await market_recommend(self.client,'托里德 刷新','pc');self.assertIn('暂无有效词条样本',''.join(r.lines))
        p=_path('snapshots',_key('pc|torid'));p.write_text('broken')
        self.client.wm_riven_auctions.side_effect=RuntimeError('429')
        r=await market_recommend(self.client,'托里德','pc');self.assertIn('数据暂不可用',r.title)
    async def test_handler_and_suffix_platform(self):
        for text in ['托里德 洗卡推荐 -ps','托里德 洗卡推荐 刷新','洗卡推荐 托里德']:
            request=route(normalize_prefix(text));self.assertEqual(request.key,'reroll')
        req=route('洗卡推荐 托里德')
        r=await RivenCommands._h_reroll_recommend(SimpleNamespace(client=self.client),req.parsed,None,'pc')
        self.assertIn('托里德',r.title);self.assertIn('推荐档位',''.join(r.lines));self.assertNotIn('挂牌价差',''.join(r.lines));self.assertNotIn('常见组合与挂牌参考',''.join(r.lines))
        self.client.wm_riven_auctions.assert_awaited_once()

class StrictSamplingTests(unittest.IsolatedAsyncioTestCase):
    async def test_second_direction_failure_is_not_full_sample(self):
        from wf_plugin.core.api_client import WarframeClient,WarframeAPIError
        client=WarframeClient.__new__(WarframeClient);client.wm_base='https://example.invalid/v1'
        client._fetch_json=AsyncMock(side_effect=[{'payload':{'auctions':[auction(1)]}},WarframeAPIError('429')])
        with self.assertRaises(WarframeAPIError):
            await client.wm_riven_auctions('torid',require_all_sorts=True)
        client._fetch_json=AsyncMock(side_effect=[{'payload':{'auctions':[auction(1)]}},WarframeAPIError('429')])
        self.assertEqual(len(await client.wm_riven_auctions('torid')),1)
