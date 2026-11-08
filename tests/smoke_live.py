"""Optional read-only live integration check; not part of offline unit tests."""
import asyncio
from test_core import ApiClient, WarframeService, parse

async def main():
    client = ApiClient(25)
    service = WarframeService(client)
    failed = []
    try:
        for text in ['时间', '突击', '裂缝', '物品 膛线', 'wm 膛线 -rank=10 -r', '物品 Excalibur', '时间 -ps', 'wm 膛线 -sw', 'wmr 托里德 暴击率', 'wmr 托里德 暴击率 多重 -变焦']:
            try:
                result = await service.run(parse(text))
                print(f'PASS {text}: {result[:260]}\n')
            except Exception as exc:
                failed.append(text)
                print(f'FAIL {text}: {exc}')
    finally:
        await client.close()
    if failed:
        raise SystemExit(1)

asyncio.run(main())
