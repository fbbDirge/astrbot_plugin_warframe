import asyncio
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock
import test_core
from wf_plugin.core.ocr_setup import handle
from wf_plugin.commands import normalize_prefix
from wf_plugin.routing import route
from wf_plugin.core.formatters import fmt_riven_analysis


class OCRSetupTests(IsolatedAsyncioTestCase):
    def setUp(self):
        self.event = SimpleNamespace(is_admin=lambda: True)
        state = dict(job_id='job', state='succeeded', running=False, progress=100,
                     message='安装完成', recommended_python='/ocr/bin/python', model_dir='/ocr/models')
        self.installer = SimpleNamespace(status=lambda: state)
        async def start(*args, **kwargs):
            self.installer._task = asyncio.create_task(asyncio.sleep(0))
            return {'accepted': True}
        self.installer.start = AsyncMock(side_effect=start)
        self.local = SimpleNamespace(
            status=lambda: dict(ok=True, enabled=False, check_ok=False, models_found=False, revision=3),
            save=AsyncMock(), check=AsyncMock(return_value=dict(ok=True, check_persisted=True, revision=4)),
            enable=AsyncMock())
        self.runtime = SimpleNamespace(cfg={}, local_ocr_installer=self.installer,
                                       local_ocr=self.local, _safe_sender=lambda e: '')

    async def test_install_check_enable(self):
        await handle(self.runtime, self.event, '一键安装本地OCR')
        await self.runtime._ocr_setup_task
        self.local.save.assert_awaited_once_with(dict(engine='rapidocr', python='/ocr/bin/python', model_dir='/ocr/models', revision=3))
        self.local.enable.assert_awaited_once_with(True, 4)
        self.assertIn('安装成功', self.runtime._ocr_setup_message)

    async def test_check_failure_does_not_enable(self):
        self.local.check.return_value = dict(ok=False, message='模型不完整')
        await handle(self.runtime, self.event, '安装本地OCR')
        await self.runtime._ocr_setup_task
        self.local.enable.assert_not_awaited()
        self.assertIn('模型不完整', self.runtime._ocr_setup_message)

    async def test_concurrent_config_change_stops_enable(self):
        self.local.save.side_effect = ValueError('配置已更改')
        await handle(self.runtime, self.event, '安装本地OCR')
        await self.runtime._ocr_setup_task
        self.local.check.assert_not_awaited()
        self.local.enable.assert_not_awaited()

    async def test_permission_api_and_platform_guards(self):
        reply = await handle(self.runtime, SimpleNamespace(), '安装本地OCR')
        self.assertIn('管理员', reply.raw_text)
        self.installer.start.assert_not_awaited()
        self.installer.start.side_effect = None
        self.installer.start.return_value = dict(accepted=False, message='平台不支持')
        reply = await handle(self.runtime, self.event, '安装本地OCR')
        self.assertIn('平台不支持', reply.raw_text)
        self.local.save.assert_not_awaited()

    async def test_duplicate_request(self):
        self.runtime._ocr_setup_task = asyncio.create_task(asyncio.sleep(10))
        try:
            reply = await handle(self.runtime, self.event, '安装本地OCR')
            self.assertIn('正在', reply.raw_text)
            self.installer.start.assert_not_awaited()
        finally:
            self.runtime._ocr_setup_task.cancel()
            await asyncio.gather(self.runtime._ocr_setup_task, return_exceptions=True)

    def test_bare_commands_case_and_full_names(self):
        for text in ['一键安装本地OCR', '安装本地ocr', '本地OCR状态']:
            self.assertEqual(normalize_prefix(text), text)
            self.assertEqual(route(text).key, 'admin')
        _, lines = fmt_riven_analysis('毒囊双枪', 1.2, 'pistol',
            [('melee_damage',265.2),('crit_chance',184.2),('weakpoint_damage',272.4)], [('multishot',105.1)])
        output = '\n'.join(lines)
        for full in ['伤害', '暴击几率', '弱点伤害', '多重射击']:
            self.assertIn(full, output)
        self.assertNotIn('基伤', output)
