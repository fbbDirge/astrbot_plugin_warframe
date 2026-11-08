import unittest,tempfile
from test_core import ROOT
from wf_plugin.routing import route
from wf_plugin.commands import normalize_prefix
from wf_plugin.presentation import present
from wf_plugin.renderer import CardRenderer
from wf_plugin.theme import theme_from

class RerollTests(unittest.TestCase):
    def test_command_orders_and_prefixes(self):
        for query in ['绝路 洗卡推荐','洗卡推荐 绝路','绝路 Prime 洗卡推荐 夜灵','Rubico Prime 紫卡推荐']:
            for prefix in ['', '/', '.']:
                r=route(normalize_prefix(prefix+query))
                self.assertEqual(r.key,'reroll')
        self.assertIsNone(normalize_prefix('绝路 洗卡推荐',prefixes=['/']))
        self.assertIsNone(normalize_prefix('今晚要不要洗卡推荐一下'))
