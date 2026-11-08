import copy
import unittest
from test_core import Command
from wf_plugin.localization import translate, localize_world
from wf_plugin.world import render_world
from wf_plugin.renderer import CardRenderer, FONT
from PIL import ImageFont


def alerts_fixture():
    return {'timestamp': '2026-11-07T07:27:00Z', 'alerts': [
        {'expiry': '2099-11-17T19:00:00Z', 'mission': {'node': node, 'type': kind,
         'reward': {'countedItems': [{'type': resource, 'count': count}], 'credits': credits}}}
        for node, kind, resource, count, credits in [
            ('Stephano (Uranus)', 'Defense', 'Forma', 3, 10000),
            ('Larissa (Neptune)', 'Mobile Defense', 'Kuva', 200000, 10000),
            ('Brugia (Eris)', 'Hive', 'Moonflesh', 50, 17000),
            ('Naeglar (Eris)', 'Exterminate', 'Moonflesh', 50, 17000),
            ('Solium (Eris)', 'Mobile Defense', 'Moonflesh', 50, 17000)]]}


class LocalizationTests(unittest.TestCase):
    def test_screenshot_alerts(self):
        data = alerts_fixture()
        original = copy.deepcopy(data)
        result = render_world(Command('警报'), data)
        self.assertEqual(data, original)
        self.assertEqual(result.rows[0][0][0], 'Stephano（天王星）')
        self.assertEqual(result.rows[2][1][0], '清巢')
        self.assertIn('福马 ×3', result.rows[0][2][0])
        self.assertIn('赤毒 ×200000', result.rows[1][2][0])
        self.assertIn('月华脯 ×50', result.rows[2][2][0])
        for word in ['Uranus','Neptune','Eris','Hive','Forma','Kuva','Moonflesh']:
            self.assertNotIn(word, str(result))

    def test_unknowns_and_identifiers_untouched(self):
        data={'id':'Kuva','link':'https://example.org/Kuva','slug':'Kuva','ingameName':'Kuva', 'name':'Kuva'}
        self.assertEqual(localize_world(data),dict(data,name='赤毒'))
        self.assertEqual(translate('Future New Reward'), 'Future New Reward')
        self.assertEqual(translate('Larissa（海王星）'),'Larissa（海王星）')
        self.assertEqual(translate('hive'),'清巢')

    def test_fissures_and_english_filters(self):
        data={'fissures':[{'tier':'Lith','node':'Stephano (Uranus)','missionType':'Defense','expiry':'2099-01-01T00:00:00Z'}]}
        for query in ['防御','Defense','天王星','Uranus']:
            result=render_world(Command('裂缝',query=query),data)
            self.assertEqual(result.rows[0][0][1],'tier_lith')
            self.assertEqual(result.rows[0][1][0],'Stephano（天王星）')

    def test_word_and_number_wrapping(self):
        font=ImageFont.truetype(str(FONT),28)
        for text, token in [('Stephano Uranus','Uranus'),('奖励 10000 星币','10000')]:
            lines=CardRenderer.wrap(text,font,180)
            self.assertTrue(any(token in line for line in lines))
            self.assertTrue(all(font.getlength(line)<=180 for line in lines))
        lines=CardRenderer.wrap('VeryLongUnbrokenWord',font,60)
        self.assertEqual(''.join(lines),'VeryLongUnbrokenWord')
        self.assertTrue(all(font.getlength(line)<=60 for line in lines))

if __name__=='__main__':unittest.main()
