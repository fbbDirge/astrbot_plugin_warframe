import unittest,tempfile
from test_core import ROOT
from wf_plugin.core.formatters import sortie_rewards,_sortie_reward_lines,fmt_sortie
from wf_plugin.presentation import present,table
from wf_plugin.core.commands import Reply
from wf_plugin.display_icons import line_icon
from wf_plugin.renderer import load_icon,CardRenderer
from wf_plugin.theme import theme_from

class SortieRewardsTests(unittest.TestCase):
    def test_entire_reward_pool_has_icons(self):
        rows=sortie_rewards()['tiers']['0']
        for row in rows:
            label=row['name']+(f" ×{row['count']}" if row['count']>1 else '')
            icon=line_icon(label,'item_name')
            self.assertTrue(icon,label);self.assertIsNotNone(load_icon(icon,40),label)
        self.assertEqual(line_icon('奥罗金反应堆蓝图','item_name'),'blueprint:reward_reactor')
        self.assertEqual(line_icon('3 天经验值加成','item_name'),'reward_affinity')
        self.assertEqual(line_icon('近战裂罅 Mod','wm_user'),'')
        self.assertEqual(line_icon('未知奖励','item_name'),'')
    def test_real_sortie_reward_table(self):
        title,lines=fmt_sortie({'boss':'测试首领','expiry':'2099-01-01T00:00:00Z','variants':[{'node':'Stephano (Uranus)','missionType':'Defense','faction':'Grineer'}]})
        cards=present(Reply(title,lines),'sortie')
        rewards=[b for c in cards for b in c.blocks if b.columns==('奖励','稀有度','几率')]
        self.assertTrue(rewards)
        for b in rewards:
            for row in b.rows:self.assertTrue(line_icon(row[0][0],row[0][1]))
        with tempfile.TemporaryDirectory() as tmp:
            for c in cards:self.assertTrue(CardRenderer(tmp).render(c,theme_from({})).is_file())
