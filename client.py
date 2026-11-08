"""Public read-only APIs with bounded cache and request pacing."""
import asyncio
import time
from collections import OrderedDict

import aiohttp


class QueryError(Exception):
    pass


class ApiClient:
    def __init__(self, timeout=20):
        self.timeout = max(3, min(int(timeout), 60))
        self.session = None
        self.cache = OrderedDict()
        self.lock = asyncio.Lock()
        self.next_market = 0.0
        self.next_auction = 0.0

    async def get(self, url, *, platform="pc", ttl=60):
        key = (url, platform)
        cached = self.cache.get(key)
        if cached and cached[0] > time.monotonic():
            return cached[1]
        async with self.lock:
            cached = self.cache.get(key)
            if cached and cached[0] > time.monotonic():
                return cached[1]
            market = url.startswith("https://api.warframe.market/")
            auction = url.startswith('https://api.warframe.market/v1/auctions/search?')
            if auction:
                await asyncio.sleep(max(0, self.next_auction - time.monotonic()))
                self.next_auction = time.monotonic() + 6.0
            if market:
                await asyncio.sleep(max(0, self.next_market - time.monotonic()))
                self.next_market = time.monotonic() + 0.4
            if self.session is None or self.session.closed:
                self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
            try:
                async with self.session.get(url, headers={
                    "User-Agent": "AstrBot-Warframe/0.7.1", "Language": "zh-hans",
                    "Platform": {"xb1": "xbox", "swi": "switch"}.get(platform, platform), "Crossplay": "false",
                    "Accept-Language": "zh-CN",
                }) as response:
                    if response.status == 429:
                        raise QueryError("数据源请求过于频繁，请稍后再试。")
                    if response.status != 200:
                        raise QueryError(f"数据源暂时不可用（HTTP {response.status}），请稍后重试。")
                    if url.startswith('https://raw.githubusercontent.com/calamity-inc/warframe-public-export-plus/'):
                        data = await response.json(content_type=None)
                    else:
                        data = await response.json()
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
                raise QueryError("数据源连接超时或返回异常，请稍后重试。") from exc
            if market:
                if not isinstance(data, dict) or data.get("error") or data.get("payload" if url.startswith("https://api.warframe.market/v1/") else "data") is None:
                    raise QueryError("WM 数据格式异常，请稍后重试。")
                data = data["payload" if url.startswith("https://api.warframe.market/v1/") else "data"]
            self.cache[key] = (time.monotonic() + ttl, data)
            self.cache.move_to_end(key)
            while len(self.cache) > 128:
                self.cache.popitem(last=False)
            return data

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
