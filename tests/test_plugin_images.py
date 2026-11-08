"""Exercise the plugin event path with a minimal host double, not a live AstrBot."""
import importlib
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
import test_core


class PluginImageTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_handled_paths_return_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            api = types.ModuleType('astrbot.api')
            api.AstrBotConfig = dict
            import logging
            api.logger = logging.getLogger('test')
            event_module = types.ModuleType('astrbot.api.event')
            event_module.AstrMessageEvent = object
            event_module.filter = types.SimpleNamespace(regex=lambda _: lambda f: f)
            star_module = types.ModuleType('astrbot.api.star')
            class Star:
                def __init__(self,context): pass
            star_module.Star = Star; star_module.Context = object
            star_module.StarTools = types.SimpleNamespace(get_data_dir=lambda _:Path(tmp))
            star_module.register = lambda *args:lambda cls:cls
            mods={'astrbot':types.ModuleType('astrbot'),'astrbot.api':api,'astrbot.api.event':event_module,'astrbot.api.star':star_module}
            with patch.dict(sys.modules,mods):
                sys.modules.pop('wf_plugin.main',None)
                module = importlib.import_module('wf_plugin.main')
                from unittest.mock import AsyncMock
                from wf_plugin.core.commands import Reply
                plugin = module.WarframePlugin(None,{'cooldown':0})
                captured=[]
                async def capture(parsed,event,platform):
                    captured.append(parsed)
                    return Reply('测试结果',['◆ 结果：测试数据'])
                runtime=types.SimpleNamespace(
                    _routes={k:capture for k in ['help','wm','sortie','analysis']},
                    groups=types.SimpleNamespace(platform=lambda _: 'pc'),
                    renderer=types.SimpleNamespace(style_config=lambda:plugin.config),
                    _reply_actions=lambda reply,parsed:reply.actions,
                    terminate=AsyncMock())
                plugin.runtime=runtime
                class Event:
                    unified_msg_origin='test:GroupMessage:123'
                    def __init__(self,text): self.message_str=text
                    def get_platform_id(self): return 'test'
                    def get_sender_id(self): return '123'
                    def stop_event(self): pass
                    def image_result(self,path):
                        assert Path(path).is_file()
                        return ('image',path)
                    def plain_result(self,text): raise AssertionError('Unexpected plain text output')
                for text in ['wf 帮助','wf 配色 价格 #FF8800','wf 主题','wf 字号 100','wm']:
                    result=[x async for x in plugin.on_message(Event(text))]
                    self.assertGreaterEqual(len(result),1)
                    self.assertTrue(all(r[0]=='image' for r in result))
                self.assertEqual([x async for x in plugin.on_message(Event('普通聊天'))],[])
                async def broken(*args): raise RuntimeError('test service failure')
                runtime._routes['sortie'] = broken
                with self.assertLogs('test',level='ERROR'):
                    result=[x async for x in plugin.on_message(Event('wf 突击'))]
                self.assertEqual(result[0][0],'image')
                replies=[x async for x in plugin.on_message(Event('wf 前缀 .'))]
                self.assertEqual(replies[0][0],'image')
                self.assertEqual([x async for x in plugin.on_message(Event('wm 野猪'))],[])
                replies=[x async for x in plugin.on_message(Event('.wm 野猪'))]
                self.assertEqual(captured[-1].content,['野猪'])
                # Direct riven OCR route now uses the same native handler as typed analysis.
                replies=[x async for x in plugin.on_message(Event('wf 紫卡分析'))]
                self.assertEqual(captured[-1].command,'analysis')
                await plugin.terminate()
                sys.modules.pop('wf_plugin.main',None)
