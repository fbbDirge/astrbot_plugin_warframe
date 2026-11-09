import base64
import io
import unittest
from unittest.mock import AsyncMock, patch
import httpx
from PIL import Image
import test_core
from wf_plugin.core import http_ocr

TEXT = '18一\n恶脓双斧 Crita-\nplagado\n+106.3%冰冻伤害\n0+110.8%异常状态伤害\n+221.9%暴击几率（重击\n时x2)\nx0.6 对 Corpus的伤害\n段位15\n55'

class HTTPTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        buf=io.BytesIO(); Image.new('RGB',(32,32)).save(buf,'PNG')
        self.image='data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()
        self.config={'riven_http_ocr_key':'test-key'}

    async def test_request_contract(self):
        def handle(request):
            self.assertEqual(str(request.url), http_ocr.DEFAULT_URL)
            self.assertEqual(request.headers['Authorization'], 'Bearer test-key')
            self.assertIn('multipart/form-data', request.headers['content-type'])
            body=request.content
            self.assertIn(b'name="file"; filename="riven.png"',body)
            self.assertIn(b'name="need_location"\r\n\r\nfalse',body)
            self.assertNotIn(b'name="url"',body)
            self.assertNotIn(b'name="image_base64"',body)
            return httpx.Response(200,json={'plain_text':TEXT})
        self.assertEqual(await http_ocr.recognize(self.image,self.config,transport=httpx.MockTransport(handle)),TEXT)

    async def test_errors_do_not_expose_response_or_key(self):
        for status in (302,401,402,429,500):
            with self.assertRaises(ValueError) as caught:
                await http_ocr.recognize(self.image,self.config,transport=httpx.MockTransport(lambda req: httpx.Response(status,text='test-key')))
            self.assertNotIn('test-key',str(caught.exception))
        with self.assertRaises(ValueError):
            await http_ocr.recognize(self.image,self.config,transport=httpx.MockTransport(lambda req:httpx.Response(200,text='not json')))

    async def test_invalid_inputs_fail_before_network(self):
        for image,config in [(self.image,{}),('bad',self.config),(self.image,{**self.config,'riven_http_ocr_url':'http://example.com'}),('data:image/png;base64,'+'A'*(14*1024*1024),self.config)]:
            with self.assertRaises(ValueError): await http_ocr.recognize(image,config)

    async def test_sample_parse_preserves_uncertainty(self):
        with patch.object(http_ocr,'recognize',AsyncMock(return_value=TEXT)):
            data=await http_ocr.read_riven(self.image,self.config)
        self.assertEqual(data['weapon'],'恶脓双斧 Crita-plagado')
        self.assertEqual(len(data['lines']),4)
        self.assertIn('0+110.8%异常状态伤害',data['lines'])
        self.assertIn('+221.9%暴击几率(重击时x2)',data['lines'])
        self.assertIn('x0.6 对 Corpus的伤害',data['lines'])
        self.assertEqual(data['_recognition']['source'],'http_ocr')
