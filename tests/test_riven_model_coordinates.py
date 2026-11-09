import unittest
import test_core
from wf_plugin.core import loadout_ocr as lo, riven_analysis as ra
from wf_plugin.core.parser import RIVEN_STAT_ZH

class ModelCoordinates(unittest.TestCase):
    def test_tuple_and_list_preserve_sign_and_decimal(self):
        for wrapper in [('(', ')'), ('[', ']')]:
            raw = wrapper[0] + '504,619,665,51,0,"+145.8% 多重射击"' + wrapper[1]
            result = lo.coordinate_text_lines(raw)
            self.assertEqual(result, ['504,619,665,51,0,+145.8% 多重射击'])
            self.assertEqual(ra.decode_riven_lines(result)['lines'], ['+145.8% 多重射击'])
        self.assertEqual(lo.coordinate_text_lines('(478,785,673,51,0,"-109.3% 穿刺伤害")'),
                         ['478,785,673,51,0,-109.3% 穿刺伤害'])

    def test_invalid_records_remain_visible(self):
        for raw in ['(1,2,3,4,999,"+10% 伤害")', '(1,2,3,4,0,"+10% 伤害"',
                    '(1,2,3,4,0,__import__("os"))']:
            self.assertEqual(lo.coordinate_text_lines(raw), [raw])

if __name__ == '__main__': unittest.main()

class ModelRecovery(unittest.IsolatedAsyncioTestCase):
    async def test_bounded_reread_requires_matching_complete_stats(self):
        from wf_plugin.core.commands.vision import VisionCommands as GameRuntime
        from unittest.mock import AsyncMock
        from types import SimpleNamespace
        for conflict in [False, True]:
            obj = GameRuntime.__new__(GameRuntime)
            obj.cfg = {'vision_routes_isolated': True}
            obj._cfg_str = lambda key: ''
            provider = SimpleNamespace(meta=lambda: SimpleNamespace(id='test/model'))
            obj._riven_vision_providers = lambda: [provider]
            obj._line_vision_providers = lambda: [provider]
            data = {'weapon':'视使之触','positive':[
                {'name':'多重射击','value':'+145.8%'},
                {'name':'病毒伤害','value':'+110.8%'},
                {'name':'暴击伤害','value':'+102.3%'},
                {'name':'穿刺伤害','value':'-109.3%'}], 'negative':[]}
            bad = obj._parse_riven_lines_text('视使之触 Cari-分裂\n重伤\n+145.8% 多重射击\n+110.8% 病毒伤害\n+102.3% 暴击伤害\n-109.3% 穿刺伤害')
            good = obj._parse_riven_lines_text('视使之触 Cari-cron\n+145.8% 多重射击\n+110.8% 病毒伤害\n+' + ('103.3' if conflict else '102.3') + '% 暴击伤害\n-109.3% 穿刺伤害\n段位16\n426')
            obj._vision_race_json = AsyncMock(side_effect=[data,bad,good])
            result = await obj._extract_riven_from_image('test')
            self.assertEqual(obj._vision_race_json.await_count, 3)
            self.assertEqual(result['_recognition']['line_recheck']['adopted'], not conflict)
            self.assertEqual(result['lines'], (bad if conflict else good)['lines'])
