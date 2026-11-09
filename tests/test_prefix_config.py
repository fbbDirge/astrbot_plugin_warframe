import unittest
import test_core
from wf_plugin.commands import effective_prefixes,normalize_prefix

class PrefixConfigTests(unittest.TestCase):
    def test_global_bare_flag_with_symbol_only_list(self):
        config={'command_prefixes':['/','.'],'bare_commands':True}
        prefixes,bare=effective_prefixes(config,{})
        for text in ['裂缝','裂缝 -cn','默认平台 国服','/裂缝','.裂缝']:
            self.assertIsNotNone(normalize_prefix(text,prefixes,bare))
        self.assertIsNone(normalize_prefix('普通聊天',prefixes,bare))
        self.assertEqual(config['command_prefixes'],['/','.'])

    def test_personal_prefixes_remain_explicit(self):
        prefixes,bare=effective_prefixes({'bare_commands':True},{'command_prefixes':['.']})
        self.assertIsNone(normalize_prefix('裂缝',prefixes,bare))
        self.assertEqual(normalize_prefix('.裂缝',prefixes,bare),'裂缝')
        self.assertEqual(normalize_prefix('wf 前缀 默认',prefixes,bare),'wf 前缀 默认')

    def test_bare_disabled(self):
        prefixes,bare=effective_prefixes({'bare_commands':False,'command_prefixes':['','/']},{})
        self.assertIsNone(normalize_prefix('裂缝',prefixes,bare))
        self.assertEqual(normalize_prefix('/裂缝',prefixes,bare),'裂缝')

    def test_bare_group_switches(self):
        from wf_plugin.routing import route
        prefixes,bare=effective_prefixes({'bare_commands':True,'command_prefixes':['/','.']},{})
        for text,platform in [('切换国服','cn'),('切换国际服','pc')]:
            normalized=normalize_prefix(text,prefixes,bare)
            self.assertEqual(normalized,text)
            request=route(normalized)
            self.assertEqual(request.key,'admin')
            self.assertEqual(request.admin_text,'.默认平台 '+platform)
