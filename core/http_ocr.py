"""Standalone UAPI-compatible OCR; no vision provider or automatic fallback."""
import base64
import io
from urllib.parse import urlsplit

import httpx
from PIL import Image

from .http_ocr_response import response_text

DEFAULT_URL = 'https://uapis.cn/api/v1/image/ocr'
MAX_IMAGE_BYTES = 10 * 1024 * 1024


async def recognize(image_url, config, *, transport=None):
    endpoint = str(config.get('riven_http_ocr_url') or DEFAULT_URL).strip()
    key = str(config.get('riven_http_ocr_key') or '').strip()
    parsed = urlsplit(endpoint)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('OCR 接口地址必须是 HTTPS 地址')
    if not key:
        raise ValueError('请先配置独立 OCR API 密钥')
    if not isinstance(image_url, str) or not image_url.startswith('data:image/') or ';base64,' not in image_url:
        raise ValueError('OCR 图片格式不正确')
    encoded = image_url.split(';base64,', 1)[1]
    if len(encoded) > ((MAX_IMAGE_BYTES + 2) // 3) * 4:
        raise ValueError('OCR 图片不能超过 10MB')
    try:
        raw = base64.b64decode(encoded, validate=True)
        if not raw or len(raw) > MAX_IMAGE_BYTES:
            raise ValueError()
        with Image.open(io.BytesIO(raw)) as image:
            fmt = image.format
            image.verify()
        extension, mime = {'JPEG': ('jpg', 'image/jpeg'), 'PNG': ('png', 'image/png'),
                           'BMP': ('bmp', 'image/bmp'), 'GIF': ('gif', 'image/gif'),
                           'WEBP': ('webp', 'image/webp')}[fmt]
    except Exception:
        raise ValueError('OCR 图片损坏或格式不支持') from None
    try:
        timeout = max(1, min(120, float(config.get('riven_http_ocr_timeout', 60))))
    except (TypeError, ValueError):
        raise ValueError('OCR 超时配置必须为数字') from None
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, transport=transport) as client:
            response = await client.post(endpoint, headers={'Authorization': 'Bearer ' + key},
                files={'file': ('riven.' + extension, raw, mime)},
                data={'need_location': 'false'})
        if response.status_code != 200:
            raise ValueError(f'OCR 接口请求失败（HTTP {response.status_code}），请检查密钥、额度或服务状态')
        payload = response.json()
    except httpx.TimeoutException:
        raise ValueError('OCR 接口请求超时，请稍后重试') from None
    except httpx.RequestError:
        raise ValueError('OCR 接口连接失败，请检查网络') from None
    except ValueError as exc:
        if str(exc).startswith('OCR 接口请求失败'):
            raise
        raise ValueError('OCR 接口未返回有效 JSON') from None
    return response_text(payload)


async def read_riven(image_url, config):
    from .riven_ocr_reader import decode_text
    text = await recognize(image_url, config)
    observation = decode_text(text)
    if observation.multiple:
        raise ValueError('画面中有多个完整紫卡，请仅保留一张卡')
    if not observation.data:
        raise ValueError('OCR 已返回文字，但未能提取完整紫卡，请裁剪清晰卡面重试，或手动输入词条')
    observation.data['_recognition'] = {'source': 'http_ocr'}
    return observation.data
