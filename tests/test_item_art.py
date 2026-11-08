import asyncio
import io
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from test_core import parse,WarframeService
from wf_plugin.item_art import ArtworkCache,asset_url,market_art

class ArtTests(unittest.TestCase):
    def test_asset_origin_and_metadata(self):
        for bad in ['https://example.org/x.png','http://assets.warframe.market/x','//example.org/x','https://assets.warframe.market@evil.test/x','../x']:
            self.assertEqual(asset_url(bad),'')
        self.assertEqual(market_art({'i18n':{'zh-hans':{'thumb':'items/part.png','subIcon':'sub_icons/blueprint.png'}}}),('https://warframe.market/static/assets/items/part.png','https://warframe.market/static/assets/sub_icons/blueprint.png'))
        self.assertEqual(market_art({}),('',''))

class CacheTests(unittest.IsolatedAsyncioTestCase):
    async def test_cache_reuse_failure_and_bounds(self):
        buffer=io.BytesIO();Image.new('RGBA',(300,200),(10,20,30,255)).save(buffer,format='PNG')
        with tempfile.TemporaryDirectory() as directory:
            cache=ArtworkCache(directory);calls=[];cache.MAX_FILES=2
            async def download(url):calls.append(url);return buffer.getvalue()
            cache.download=download
            url='https://warframe.market/static/assets/items/test.png'
            first,second=await asyncio.gather(cache.get(url),cache.get(url))
            self.assertEqual(first,second);self.assertEqual(len(calls),1)
            with Image.open(first) as im:self.assertEqual(max(im.size),256)
            await cache.get(url+'?v=2');await cache.get(url+'?v=3')
            self.assertEqual(len(list(Path(directory).glob('*.png'))),2)
            async def invalid(url):calls.append(url);return b'not an image'
            cache.download=invalid;bad='https://warframe.market/static/assets/items/bad.png'
            self.assertIsNone(await cache.get(bad));count=len(calls)
            self.assertIsNone(await cache.get(bad));self.assertEqual(len(calls),count)
            self.assertIsNone(await cache.get('https://example.org/x'))
            self.assertEqual(len(list(Path(directory).glob('*.tmp'))),0)

    async def test_component_and_set_keep_distinct_art(self):
        items=[{'slug':'wukong_prime_set','i18n':{'en':{'name':'Wukong Prime Set','thumb':'items/set.png'}}},
               {'slug':'wukong_prime_blueprint','i18n':{'en':{'name':'Wukong Prime Blueprint','thumb':'items/bp.png','subIcon':'sub_icons/blueprint.png'}}}]
        class Client:
            async def get(self,url,**kwargs):return items if url.endswith('/items') else []
        service=WarframeService(Client())
        whole=await service.run(parse('wm 猴子'));part=await service.run(parse('wm 猴子蓝图'))
        self.assertTrue(whole.artwork[0].endswith('/set.png'))
        self.assertTrue(part.artwork[0].endswith('/bp.png'))
        self.assertTrue(part.artwork[1].endswith('/blueprint.png'))

    async def test_network_failure_falls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            cache=ArtworkCache(directory)
            async def fail(url):raise asyncio.TimeoutError()
            cache.download=fail
            self.assertIsNone(await cache.get('https://warframe.market/static/assets/items/test.png'))

    async def test_renderer_with_cached_art(self):
        from wf_plugin.cards import Card
        from wf_plugin.renderer import CardRenderer
        from wf_plugin.theme import theme_from
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'item.png'
            Image.new('RGBA',(128,128),(0,160,80,255)).save(path)
            c=Card('示例',title='战甲蓝图 · PC',artwork=('','sub_icons/blueprint.png'))
            c.artwork_path=path
            rendered=CardRenderer(Path(directory)/'out').render(c,theme_from({}))
            with Image.open(rendered) as image:
                self.assertEqual(image.getpixel((1795,155)),(0,160,80))
