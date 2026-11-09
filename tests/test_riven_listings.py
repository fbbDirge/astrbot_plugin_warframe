import unittest
from copy import deepcopy
import test_core
from wf_plugin.core.riven_listings import select
from wf_plugin.core import riven_analysis as RA
from wf_plugin.core.formatters import _riven_price_lines
from test_reroll_market import auction

class ListingTests(unittest.TestCase):
    def test_exact_matching_and_lowest_five(self):
        rows=[auction(i,price=100-i) for i in range(10)]
        bad=auction(30,price=1,slug='rubico')
        rows += [bad,auction(31,price=1,pos=('critical_damage','multishot')),auction(32,price=None),{**auction(33,price=1),'closed':True},rows[-1]]
        result=select(rows,'torid',['critical_chance','multishot'],['zoom'])
        self.assertEqual([r['buyout_price'] for r in result],[91,92,93,94,95])
        malformed=auction(50,price=1);malformed['item']['attributes'][1]=deepcopy(malformed['item']['attributes'][0])
        self.assertFalse(select([malformed],'torid',['critical_chance','multishot'],['zoom']))

    def test_mod_rank_is_used_for_stat_grade(self):
        a=auction(1,rank=0)
        mapping={'critical_chance':'crit_chance','multishot':'multishot','zoom':'zoom'}
        for at in a['item']['attributes']:
            lo,hi=RA.stat_range(mapping[at['url_name']],'rifle',1.2,2,1,negative=not at['positive'])
            at['value']=(hi if at['positive'] else lo)/9
        price={'listings':[a],'stat_ids':mapping,'pos':['crit_chance','multishot'],'neg':['zoom']}
        text='\n'.join(_riven_price_lines(price,'rifle',[]))
        self.assertEqual(text.count('S 100分'),3)
        self.assertIn('0级',text)
        a['item']['mod_rank']=None
        self.assertEqual('\n'.join(_riven_price_lines(price,'rifle',[])).count('待核对'),3)

class ListingIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_query_preserves_values_and_exact_filters(self):
        from unittest.mock import AsyncMock,patch
        from types import SimpleNamespace
        from wf_plugin.core.commands.riven import RivenCommands
        from wf_plugin.core.api_client import WarframeClient
        from wf_plugin.core.parser import RIVEN_URL_COMPAT
        weapon={'url_name':'torid','en':'Torid','riven_type':'rifle'}
        rows=[auction(i,price=100-i) for i in range(8)]+[auction(80,slug='rubico',price=1)]
        client=SimpleNamespace(wm_riven_auctions=AsyncMock(return_value=rows),
                normalize_riven_stats=lambda ids,rt:[RIVEN_URL_COMPAT.get(s,s) for s in ids],
                riven_buyout_summary=WarframeClient.riven_buyout_summary)
        obj=SimpleNamespace(client=client)
        with patch('wf_plugin.core.commands.market.riven_market_weapon',AsyncMock(return_value=weapon)):
            result=await RivenCommands._riven_analysis_price(obj,weapon,[('crit_chance',200),('multishot',120)],[('zoom',40)],'pc')
        self.assertEqual(len(result['listings']),5)
        self.assertEqual(result['listings'][0]['buyout_price'],93)
        self.assertEqual(result['stat_ids']['critical_chance'],'crit_chance')
        self.assertFalse(client.wm_riven_auctions.call_args.kwargs['allow_attribute_fallback'])
