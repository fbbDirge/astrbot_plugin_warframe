import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('http_ocr_response', Path(__file__).resolve().parents[1] / 'core/http_ocr_response.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ResponseTests(unittest.TestCase):
    def test_preserves_numbers_and_wrapped_lines(self):
        text = '恶脓双斧 Crita-\nplagado\n0+110.8%异常状态伤害\n+221.9%暴击几率（重击\n时x2)\nx0.6 对 Corpus的伤害'
        self.assertEqual(module.response_text({'plain_text':text, 'text':text, 'words_result':[{'words':x} for x in text.splitlines()]}), text)

    def test_fallback(self):
        self.assertEqual(module.response_text({'plain_text':' ', 'text':'识别文字'}), '识别文字')
        self.assertEqual(module.response_text({'words_result':[{'words':'第一行'},{'words':'第二行'}]}), '第一行\n第二行')

    def test_invalid_or_empty(self):
        for payload in (None, [], {}, {'words_result':[]}, {'words_result':[{'words':12}]}):
            with self.assertRaises(ValueError): module.response_text(payload)
