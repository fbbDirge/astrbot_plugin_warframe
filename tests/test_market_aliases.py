import unittest
from test_core import WarframeService, parse
from wf_plugin.naming import find_items
from wf_plugin.market_aliases import FRAME_NAMES, market_alias_slug


def item(slug):
    return {'slug': slug, 'i18n': {'en': {'name': slug.replace('_', ' ')}}}


class MarketAliasTests(unittest.TestCase):
    def test_all_aliases_and_parts(self):
        for frame, aliases in FRAME_NAMES.items():
            for alias in (frame, *aliases):
                for suffix, part in [('', 'set'), ('P一套', 'set'), (' Prime 系统', 'systems'), ('p头', 'neuroptics'), ('机体', 'chassis'), ('蓝图', 'blueprint'), ('系统蓝图', 'systems'), (' Prime chassis blueprint', 'chassis')]:
                    slug = f'{frame}_prime_{part}' + ('_blueprint' if part in {'systems', 'chassis', 'neuroptics'} else '')
                    self.assertEqual(find_items([item(slug)], alias + suffix, True), [item(slug)], alias + suffix)

    def test_user_examples(self):
        for query, frame in [('wukongprime','wukong'), ('猴子','wukong'), ('measprime','mesa'), ('女枪','mesa'), ('ahsprim','ash'), ('ash','ash')]:
            slug = f'{frame}_prime_set'
            self.assertEqual(find_items([item(slug)],query,True),[item(slug)])
        self.assertEqual(market_alias_slug('MEAS PRIME 机体'), 'mesa_prime_chassis_blueprint')
        self.assertEqual(market_alias_slug('ahsprim系统'), 'ash_prime_systems_blueprint')

    def test_no_fuzzy_guess_or_wrong_fallback(self):
        for query in ['猴子皮肤','女枪不存在的配件','黑咖喱','奶','mesaprmee']:
            self.assertIsNone(market_alias_slug(query))
        self.assertEqual(find_items([item('wukong_prime_blueprint')], '猴子', True), [])
        self.assertEqual(find_items([item('wukong_prime_set')], '猴子系统', True), [])
        self.assertEqual(find_items([item('mesa_prime_set')], '女枪'), [])

    def test_exact_items_mods_and_resources_preserved(self):
        for slug in ['serration', 'ayatan_amber_star', '女枪']:
            entry = item(slug)
            self.assertEqual(find_items([entry, item('mesa_prime_set')],slug,True),[entry])


class AliasRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_prefixes_and_component_order_endpoint(self):
        class Client:
            async def get(self,url,**kwargs):
                if url.endswith('/items'):
                    return [item('wukong_prime_set'), item('mesa_prime_neuroptics_blueprint'), item('ash_prime_set')]
                self.order_url = url
                return []
        client = Client()
        service = WarframeService(client)
        for command, slug in [('wm 猴子','wukong_prime_set'),('/wm 女枪头','mesa_prime_neuroptics_blueprint'),('.wm ahsprim','ash_prime_set')]:
            result = await service.run(parse(command))
            self.assertTrue(client.order_url.endswith('/orders/item/'+slug))
            self.assertIn('暂无',result)
