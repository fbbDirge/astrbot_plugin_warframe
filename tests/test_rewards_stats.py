import tempfile,unittest
from test_core import ROOT
from wf_plugin.core import formatters as fmt
from wf_plugin.core.commands import Reply
from wf_plugin.presentation import present,table
from wf_plugin.display_icons import icon_lines,line_icon
from wf_plugin.stat_icons import STAT_ICONS,STAT_LABELS
from wf_plugin.core.parser import RIVEN_STAT_ZH
from wf_plugin.renderer import CardRenderer,load_icon
from wf_plugin.theme import theme_from

def alerts_card():
    alerts=[]
    for name,amount,node in [('Forma',3,'Stephano (Uranus)'),('Kuva',200000,'Larissa (Neptune)'),('Moonflesh',50,'Nimus (Eris)')]:
        alerts.append({'expiry':'2099-01-01T00:00:00Z','mission':{'node':node,'desc':'奖励示例','type':'Defense','faction':'Grineer','min_level':20,'max_level':30,'reward':{'item_names':[f'{name} ×{amount}'],'credits':10000}}})
    title,lines=fmt.fmt_alerts(alerts)
    return present(Reply(title,lines))[0]

class RewardStatTests(unittest.TestCase):
    def test_mixed_rewards_split_before_currency_match(self):
        parts=list(icon_lines('Forma ×3、10000现金','item_name'))
        self.assertEqual([line_icon(x,'item_name') for x in parts],['forma','credits'])
        card=alerts_card()
        blocks=[b for b in card.blocks if b.columns==('奖励物品','数量')]
        self.assertEqual([b.rows[0][0][0].icon for b in blocks],['forma','kuva','moonflesh'])
        self.assertEqual([b.rows[0][1][0] for b in blocks],['3','200000','50'])
        for b in blocks:self.assertEqual(b.rows[1][0][0].icon,'credits')
        self.assertEqual(blocks[0].rows[0][0][0],'福马')
        for name in ['forma','moonflesh']:self.assertIsNotNone(load_icon(name,32))
        with tempfile.TemporaryDirectory() as tmp:
            for size in (26,42):self.assertTrue(CardRenderer(tmp).render(card,theme_from({'font_size':size})).is_file())

    def test_non_element_stat_coverage_and_guardrails(self):
        for key,icon in STAT_ICONS.items():
            self.assertIsNotNone(load_icon(icon,32))
            self.assertEqual(line_icon(RIVEN_STAT_ZH[key]+' 120','riven_stat'),icon,key)
        for text,icon in [('多重射击 -75.5%','stat_multishot'),('+162.5% 暴击几率','stat_crit_chance'),('暴击伤害 110','stat_crit_damage'),('暴击几率（重击时 x2）','stat_crit_chance')]:
            self.assertEqual(line_icon(text,'riven_negative'),icon)
        for text,role in [('暴击','wm_user'),('暴击','item_name'),('暴击延迟','riven_stat'),('100 白金','wm_user')]:self.assertEqual(line_icon(text,role),'')
        self.assertEqual([line_icon(x,'riven_stat') for x in icon_lines('暴击 100 / 多重 90 / 病毒 50','riven_stat')],['stat_crit_chance','stat_multishot','viral'])
