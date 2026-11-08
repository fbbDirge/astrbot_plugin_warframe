import asyncio
import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('wf_plugin', ROOT / '__init__.py', submodule_search_locations=[str(ROOT)])
package = importlib.util.module_from_spec(spec)
sys.modules['wf_plugin'] = package
spec.loader.exec_module(package)
from wf_plugin.commands import Command, parse
from wf_plugin.client import ApiClient, QueryError
from wf_plugin.service import WarframeService, find_items, select_orders
from wf_plugin.world import render_world, paginate

ITEM = {'slug': 'serration', 'maxRank': 10, 'i18n': {'zh-hans': {'name': '膛线'}, 'en': {'name': 'Serration'}}}


class CoreTests(unittest.TestCase):
    def test_prefix_and_unrelated_chat(self):
        self.assertIsNone(parse('今晚一起玩游戏'))
        self.assertIsNone(parse('突击', bare=False))
        self.assertEqual(parse('/wf 突击', bare=False).name, '突击')
        self.assertEqual(parse('wf').name, '帮助')

    def test_market_options(self):
        c = parse('wm 收购 膛线 -ps -rank=10 -r -2')
        self.assertEqual((c.query,c.platform,c.rank,c.page,c.buy,c.reply), ('膛线','ps4',10,2,True,True))
        self.assertEqual(parse('WM Saryn Prime Set').query, 'Saryn Prime Set')

    def test_invalid_options(self):
        for text in ['wm', 'wm 膛线 -cn', '裂缝 -0', 'wm 膛线 -rank=a', '突击 -buy', 'wf 没有此指令', 'wm "膛线']:
            with self.subTest(text=text), self.assertRaises(QueryError):
                parse(text)

    def test_matching_exact_precedes_partial(self):
        other = {'slug':'serration_prime','i18n':{'zh-hans':{'name':'膛线 Prime'}}}
        self.assertEqual(find_items([other, ITEM], '膛线'), [ITEM])
        self.assertEqual(find_items([ITEM], 'Serra tion'), [ITEM])

    def test_order_filter_and_sort(self):
        def order(price, status='ingame', rank=10, kind='sell', visible=True):
            return {'platinum':price,'quantity':1,'type':kind,'visible':visible,'rank':rank,'user':{'status':status}}
        orders = [order(50), order(1,'offline'), order(10,rank=0), order(20), order(5,visible=False), order(40,kind='buy'), order(60,kind='buy')]
        c = Command('wm', rank=10)
        self.assertEqual([x['platinum'] for x in select_orders(orders,c)], [20,50])
        c.buy = True
        self.assertEqual([x['platinum'] for x in select_orders(orders,c)], [60,40])

    def test_fissure_modes_and_expiry(self):
        base = {'node':'Test','missionType':'Capture','tier':'Lith','expiry':'2099-01-01T00:00:00Z'}
        data = {'fissures':[base,dict(base,isHard=True),dict(base,isStorm=True),dict(base,expiry='2000-01-01T00:00:00Z')]}
        for cmd in ['裂缝','钢铁裂缝','虚空风暴']:
            self.assertIn('共 1 条', render_world(Command(cmd),data))
        self.assertIn('暂无可用数据',render_world(Command('裂缝',query='生存'),data))

    def test_pagination(self):
        self.assertIn('c',paginate(['a','b','c'],2,2))
        with self.assertRaises(QueryError):
            paginate(['a'],2,2)


class AsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_market_output_and_rank_validation(self):
        class FakeClient:
            async def get(self,url,**kwargs):
                if url.endswith('/items'):
                    return [ITEM]
                return [{'type':'sell','visible':True,'quantity':2,'rank':10,'platinum':20,'user':{'ingameName':'Tester','status':'ingame'}}]
        service = WarframeService(FakeClient())
        text = await service.run(parse('wm 膛线 -rank=10 -r'))
        self.assertIn('/w Tester', text)
        self.assertIn('(rank 10)', text)
        with self.assertRaises(QueryError):
            await service.run(parse('wm 膛线 -rank=11'))

    async def test_cache_collapses_concurrent_calls(self):
        class Response:
            status = 200
            async def __aenter__(self): return self
            async def __aexit__(self,*args): pass
            async def json(self): return {'data': [ITEM]}
        class Session:
            closed = False
            count = 0
            headers = None
            def get(self,*args,**kwargs):
                self.count += 1
                self.headers = kwargs['headers']
                return Response()
            async def close(self): self.closed = True
        client = ApiClient()
        client.session = Session()
        url = 'https://api.warframe.market/v2/items'
        results = await asyncio.gather(*(client.get(url) for _ in range(8)))
        self.assertEqual(client.session.count,1)
        self.assertEqual(results[0],[ITEM])
        await client.get(url, platform='swi')
        self.assertEqual(client.session.headers['Platform'], 'switch')
        await client.get(url, platform='xb1')
        self.assertEqual(client.session.headers['Platform'], 'xbox')
        await client.close()
        self.assertTrue(client.session.closed)

    async def test_http_error_is_not_cached(self):
        class Response:
            status = 429
            async def __aenter__(self): return self
            async def __aexit__(self,*args): pass
        class Session:
            closed = False
            def get(self,*args,**kwargs): return Response()
        client = ApiClient()
        client.session = Session()
        with self.assertRaisesRegex(QueryError, '频繁'):
            await client.get('https://api.warframe.market/v2/items')
        self.assertFalse(client.cache)


if __name__ == '__main__':
    unittest.main()
