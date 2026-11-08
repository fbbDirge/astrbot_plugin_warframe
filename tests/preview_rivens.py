"""Deterministic preview using the checked-in source-data fixture."""
import asyncio
from test_riven import RivenTests
from test_core import parse
from wf_plugin.renderer import CardRenderer
from wf_plugin.theme import theme_from

async def main():
    case=RivenTests();case.setUp()
    renderer=CardRenderer('previews')
    for text,filename in [
        ('紫卡倾向 执法','riven-variants.png'),
        ('紫卡倾向 圣洁执法者 3+1','riven-disposition.png'),
        ('紫卡倾向 执法者','riven-base.png'),
        ('紫卡分析 托里德 暴击率=162.5 病毒伤害=110.3 伤害=172 多重=-75.5 -dispo=1.2','riven-analysis.png')]:
        card=await case.service.run(parse(text))
        card.footer+='\n预览示例 · 测试数据'
        path=renderer.render(card,theme_from({}))
        path.replace(renderer.output/filename)

asyncio.run(main())
