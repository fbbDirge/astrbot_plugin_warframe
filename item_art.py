"""Bounded, persistent cache for WM's own item artwork."""
import asyncio
import hashlib
import io
import time
from pathlib import Path
from urllib.parse import urlsplit
import aiohttp
from PIL import Image, ImageOps

BASE = 'https://warframe.market/static/assets/'


def asset_url(path):
    if not isinstance(path, str) or not path or path.startswith('//'):
        return ''
    url = path if '://' in path else BASE + path.lstrip('/')
    p = urlsplit(url)
    if p.scheme != 'https' or p.netloc != 'warframe.market' or not p.path.startswith('/static/assets/') or '..' in p.path.split('/'):
        return ''
    return url


def market_art(item):
    loc = item.get('i18n', {})
    for lang in ['zh-hans','en']:
        entry = loc.get(lang) or {}
        image = asset_url(entry.get('thumb') or entry.get('icon'))
        if image:
            return (image, asset_url(entry.get('subIcon')))
    return ('', '')


class ArtworkCache:
    MAX_BYTES = 3 * 1024 * 1024
    MAX_FILES = 256

    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.lock = asyncio.Lock()
        self.failed = {}

    async def download(self, url):
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as session:
            async with session.get(url, allow_redirects=False) as response:
                if response.status != 200:
                    raise ValueError('Artwork unavailable')
                data = bytearray()
                async for chunk in response.content.iter_chunked(65536):
                    data.extend(chunk)
                    if len(data) > self.MAX_BYTES:
                        raise ValueError('Artwork too large')
                return bytes(data)

    def save(self, data, target):
        with Image.open(io.BytesIO(data)) as source:
            if source.width * source.height > 4_000_000:
                raise ValueError('Artwork dimensions too large')
            image = ImageOps.contain(source.convert('RGBA'), (256,256))
            temporary = target.with_suffix('.tmp')
            try:
                image.save(temporary,format='PNG')
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
        files = sorted(self.directory.glob('*.png'), key=lambda p:p.stat().st_mtime, reverse=True)
        for old in files[self.MAX_FILES:]:
            old.unlink(missing_ok=True)

    async def get(self, url):
        url = asset_url(url)
        if not url:
            return None
        async with self.lock:
            now = time.time()
            path = self.directory / (hashlib.sha256(url.encode()).hexdigest()+'.png')
            if path.exists() and now-path.stat().st_mtime < 30*86400:
                return path
            if self.failed.get(url,0) > now:
                return path if path.exists() else None
            try:
                data = await self.download(url)
                await asyncio.to_thread(self.save,data,path)
                self.failed.pop(url,None)
                return path
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError, ValueError, Image.DecompressionBombError):
                self.failed = {k:v for k,v in self.failed.items() if v>now}
                if len(self.failed)>=256:self.failed.pop(next(iter(self.failed)))
                self.failed[url] = now+300
                return path if path.exists() else None
