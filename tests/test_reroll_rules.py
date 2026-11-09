import unittest
from unittest.mock import AsyncMock
from types import SimpleNamespace
import test_core
from wf_plugin.core.reroll_rules import recommend,build_recommendation

class RuleTests(unittest.IsolatedAsyncioTestCase):
    async def test_never_queries_auction_prices(self):
        c=SimpleNamespace(resolve_riven_weapon=AsyncMock(return_value={'en':'Torid','zh':'托里德','riven_type':'rifle'}),wm_riven_auctions=AsyncMock(side_effect=AssertionError('No auction comparison')))
        r=await recommend(c,'托里德','pc')
        text='\n'.join(r.lines)
        self.assertIn('正面推荐',text);self.assertNotIn('挂牌价差',text)
        c.wm_riven_auctions.assert_not_awaited()
    def test_melee_and_guns_have_distinct_candidates(self):
        r=build_recommendation({'en':'Magistar','zh':'执法者','riven_type':'melee'}, {'criticalChance':.20,'procChance':.10})
        text='\n'.join(r.lines)
        self.assertNotIn('多重射击',text)
        self.assertIn('攻击范围',text)
        self.assertIn('处决伤害',text)
