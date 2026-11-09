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

class LocalOnlyRecognition(unittest.IsolatedAsyncioTestCase):
    async def test_no_cloud_call_when_local_disabled(self):
        from wf_plugin.core.commands.vision import VisionCommands
        from unittest.mock import AsyncMock
        obj = VisionCommands.__new__(VisionCommands)
        obj.cfg = {'riven_http_ocr_enabled': True, 'riven_single_ocr': True}
        obj._vision_race_json = AsyncMock()
        result = await obj._extract_riven_from_image('unused')
        self.assertEqual(result['_local_ocr']['state'], 'disabled')
        obj._vision_race_json.assert_not_awaited()
