import json,tempfile,unittest
from test_core import ROOT
from wf_plugin.bounty_art import bounty_icon,bounty_blocks
from wf_plugin.renderer import load_icon,CardRenderer
from wf_plugin.presentation import present
from wf_plugin.core.formatters import fmt_bounties,_BOUNTY_POOLS,_fmt_pool_items
from wf_plugin.core.commands import Reply
from wf_plugin.theme import theme_from

class BountyIconsTests(unittest.TestCase):
    def test_complete_reward_pool_offline(self):
        def walk(value):
            if isinstance(value,dict):
                for v in value.values():yield from walk(v)
            elif isinstance(value,list):yield from value
        for raw in walk(_BOUNTY_POOLS):
            icon=bounty_icon(raw)
            self.assertTrue(icon,raw)
            self.assertIsNotNone(load_icon(icon,40),raw)
        self.assertEqual(bounty_icon('2 × 3,000 现金匣'),'credits')
        self.assertFalse(bounty_icon('未知物品'))
    def test_all_regions_and_rotations_are_reward_rows(self):
        for region,pools in _BOUNTY_POOLS.items():
            lines=['◆ '+region]
            for tier,pool in pools.items():
                for rot,items in pool.items():
                    if not isinstance(items,list):continue
                    lines+=['　▸ '+tier+' · '+rot,'　　'+_fmt_pool_items(items)]
            blocks=bounty_blocks(lines)
            rewards=[r for b in blocks if b.columns==('奖励物品','数量') for r in b.rows]
            self.assertTrue(rewards,region)
            for row in rewards:self.assertTrue(getattr(row[0][0],'icon',''),str(row))
        blocks=bounty_blocks(['◆ 地球','　MOD 轮换（A）：★蓄能重划、★抵近射击','　▸ 10-30级'])
        self.assertEqual(sum(len(b.rows) for b in blocks if b.columns==('奖励物品','数量')),2)
        self.assertFalse(any('蓄能重划' in b.footer for b in blocks))
    def test_formatter_integration(self):
        for region in ['地球','金星','火卫二','扎里曼','圣所','1999','抢劫','深矿']:
            title,lines=fmt_bounties([],keyword=region)
            cards=present(Reply(title,lines,footer='测试数据'),'bounty')
            self.assertTrue(cards)
            with tempfile.TemporaryDirectory() as tmp:
                for card in cards:self.assertTrue(CardRenderer(tmp).render(card,theme_from({})).is_file())
