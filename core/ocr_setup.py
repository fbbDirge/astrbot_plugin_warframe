"""Explicit administrator setup of the isolated local OCR runtime."""
import asyncio
from .commands.base import Reply


def is_operator(runtime, event):
    try:
        if event.is_admin():
            return True
    except Exception:
        pass
    admins = runtime.cfg.get('super_admins') or []
    sender = runtime._safe_sender(event)
    return bool(sender) and sender in {str(value).strip() for value in admins}


async def handle(runtime, event, command):
    if not is_operator(runtime, event):
        return Reply(raw_text='此操作需要 AstrBot 管理员权限（普通群管理员不能安装服务器依赖）。')
    installer, local = runtime.local_ocr_installer, runtime.local_ocr
    task = getattr(runtime, '_ocr_setup_task', None)
    if command == '本地OCR状态':
        state = installer.status()
        message = getattr(runtime, '_ocr_setup_message', '')
        if task is not None and not task.done():
            message = f"{state['progress']}% · {state['message']}" if state['running'] else message
        status = local.status()
        return Reply(raw_text='本地 OCR：' + ('已启用' if status['enabled'] else '未启用')
                     + '\n' + (message or state['message']))
    if task is not None and not task.done():
        return Reply(raw_text='本地 OCR 正在安装或检查，请发送“本地OCR状态”查看进度。')
    status = local.status()
    if status['ok'] and status['enabled'] and status.get('check_ok') and status['models_found']:
        return Reply(raw_text='本地 OCR 已启用，可直接发送“紫卡分析”并附截图。')
    initial_revision = status['revision']
    result = await installer.start(True, expected_job_id=installer.status()['job_id'])
    if not result.get('accepted'):
        return Reply(raw_text='本地 OCR 无法开始安装：' + result.get('message', result.get('reason', '未知原因')))
    runtime._ocr_setup_message = '安装中，完成后自动检查并启用。'

    async def finish():
        try:
            await installer._task
            state = installer.status()
            if state['state'] != 'succeeded':
                runtime._ocr_setup_message = state['message']
                return
            settings = dict(engine='rapidocr', python=state['recommended_python'], model_dir=state['model_dir'])
            runtime._ocr_setup_message = '依赖已安装，正在检查本地 OCR。'
            await local.save({**settings, 'revision': initial_revision})
            checked = await local.check(**settings)
            if not checked.get('ok') or not checked.get('check_persisted'):
                runtime._ocr_setup_message = checked.get('message', '配置检查未通过，请检查配置是否被修改。')
                return
            await local.enable(True, checked['revision'])
            runtime._ocr_setup_message = '安装成功，已自动启用。发送“紫卡分析”并附截图即可。'
        except asyncio.CancelledError:
            runtime._ocr_setup_message = '安装任务已停止，可重新发送安装命令。'
            raise
        except Exception as exc:
            runtime._ocr_setup_message = f'安装或启用失败：{exc}'
    runtime._ocr_setup_task = asyncio.create_task(finish())
    return Reply(raw_text='已开始安装本地 OCR，完成后自动检查并启用。\n发送“本地OCR状态”查看进度和结果；首次需下载依赖及模型，请勿重启插件。')
