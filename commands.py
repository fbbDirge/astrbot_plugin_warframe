from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from .client import QueryError
from .routing import ROUTE_WORDS

WORLD = {
    "平原": "cetusCycle", "地球": "earthCycle", "金星": "vallisCycle",
    "火卫二": "cambionCycle", "扎里曼": "zarimanCycle", "双衍王境": "duviriCycle",
    "突击": "sortie", "执刑官": "archonHunt", "奸商": "voidTrader",
    "钢铁之路": "steelPath", "裂缝": "fissures", "钢铁裂缝": "fissures",
    "虚空风暴": "fissures", "入侵": "invasions", "夜灵电波": "nightwave",
    "仲裁": "arbitration", "每日特惠": "dailyDeals", "新闻": "news",
    "活动": "events", "警报": "alerts", "地幔": "sentientOutposts",
}
ALIASES = {"玄骇": "玄骸", "赤毒玄骸": "玄骸", "wml": "玄骸", "帕尔沃斯姐妹": "姐妹","平原时间": "平原", "地球时间": "地球", "金星平原": "金星", "福尔图娜": "金星",
           "魔胎之境": "火卫二", "夜灵": "平原", "夜波": "夜灵电波", "电波": "夜灵电波",
           "夜灵电台": "夜灵电波", "奸商时间": "奸商", "虚空商人": "奸商", "最新新闻": "新闻",
           "每日特惠": "每日特惠", "帮助": "帮助", "help": "帮助", "物品wiki": "wiki", "倾向": "紫卡倾向", "子卡倾向": "紫卡倾向", "紫卡": "紫卡倾向", "分析紫卡": "紫卡分析"}
COMMANDS = set(WORLD) | set(ALIASES) | {"玄骸", "姐妹", "时间", "物品", "wm", "wmr", "wiki", "帮助", "紫卡倾向", "紫卡分析"}
PLATFORMS = {"-pc": "pc", "-ps": "ps4", "-ps4": "ps4", "-xb": "xb1", "-xb1": "xb1", "-sw": "swi", "-swi": "swi"}


@dataclass
class Command:
    name: str
    query: str = ""
    platform: str = "pc"
    page: int = 1
    rank: int | None = None
    buy: bool = False
    reply: bool = False
    layout: str = "3+1"
    mod_rank: int = 8
    disposition: float | None = None
    include_offline: bool = False
    riven_layout: str | None = None


def effective_prefixes(config, personal):
    """Global bare_commands enables bare input; personal prefixes are explicit overrides."""
    if 'command_prefixes' in personal:
        return list(personal['command_prefixes']), True
    prefixes=list(config.get('command_prefixes',['','/','.']))
    bare=config.get('bare_commands',True)
    if bare and '' not in prefixes:
        prefixes.append('')
    return prefixes, bare


def normalize_prefix(text, prefixes=None, bare=True):
    text = text.strip()
    # Fixed recovery/control entry is always available.
    if re.match(r'(?i)^/?wf(?:\s|$)', text):
        return text.removeprefix('/')
    prefixes = ['', '/', '.'] if prefixes is None else prefixes
    for prefix in sorted(prefixes, key=len, reverse=True):
        if prefix == '' and not bare:
            continue
        if text.startswith(prefix):
            candidate = text[len(prefix):]
            first = candidate.split(maxsplit=1)[0].lower() if candidate else ''
            if re.fullmatch(r'.+?\s+(?:洗卡推荐|紫卡推荐)(?:\s+(?:夜灵|三傻|日常|通用|刷新|-(?:pc|ps|xb|sw|ps4|xb1|swi)))*',candidate) or first in COMMANDS or first in ROUTE_WORDS or first == 'wf' or re.match(r'^(?:wmr|wm|wr|rm|xh)[\u4e00-\u9fff]',candidate,re.I):
                return candidate
    return None


def parse(text, default_platform="pc", bare=True, prefixes=None):
    text = normalize_prefix(text, prefixes, bare)
    if text is None:
        return None
    prefixed = bool(re.match(r"(?i)^wf(?:\s|$)", text))
    if prefixed:
        text = text[2:].strip() or "帮助"
    elif not bare:
        return None
    first = text.split(maxsplit=1)[0] if text else ""
    if first.lower() not in COMMANDS:
        if prefixed:
            raise QueryError("未知指令，发送 wf 帮助 查看已实现功能。")
        return None
    try:
        parts = shlex.split(text)
    except ValueError as exc:
        raise QueryError("引号未闭合，请检查指令。") from exc
    name = parts.pop(0).lower()
    c = Command(ALIASES.get(name, name), platform=default_platform)
    words = []
    for part in parts:
        if c.name in {'wmr','玄骸','姐妹'} and part == '-all':
            c.include_offline = True
        elif c.name == 'wmr' and part in {'2+0','2+1','3+0','3+1'}:
            c.riven_layout = part
        elif c.name in {'紫卡倾向','紫卡分析'} and part in {'2+0','2+1','3+0','3+1'}:
            c.layout = part
        elif c.name in {'紫卡倾向','紫卡分析'} and re.fullmatch(r'-rank=[0-8]',part):
            c.mod_rank = int(part[-1])
        elif c.name in {'紫卡倾向','紫卡分析'} and re.fullmatch(r'-dispo=\d+(?:\.\d+)?',part):
            c.disposition = float(part.split('=')[1])
            if not .5 <= c.disposition <= 1.55:
                raise QueryError('手动倾向范围为 0.5—1.55。')
        elif c.name == '紫卡分析' and re.match(r'-\d+(?:\.\d+)?[%％]?[\u4e00-\u9fff]',part):
            words.append(part)
        elif part in PLATFORMS:
            c.platform = PLATFORMS[part]
        elif part == "-cn":
            raise QueryError("第一版仅支持国际服，暂不支持国服 -cn。")
        elif part == "-r":
            c.reply = True
        elif part == "-buy":
            c.buy = True
        elif re.fullmatch(r"-rank=\d+", part):
            c.rank = int(part[6:])
        elif re.fullmatch(r"-\d+", part):
            c.page = int(part[1:])
            if not 1 <= c.page <= 100:
                raise QueryError("页码范围为 1—100。")
        elif c.name == 'wmr' and re.fullmatch(r'-[A-Za-z_\u4e00-\u9fff][A-Za-z_\u4e00-\u9fff/]*',part):
            words.append(part)
        elif part.startswith("-"):
            raise QueryError(f"不支持的参数：{part}。发送 wf 帮助 查看用法。")
        else:
            words.append(part)
    c.query = " ".join(words)
    if c.name == "wm" and c.query.startswith("收购"):
        c.buy, c.query = True, c.query[2:].strip()
    if c.name in {"wm", "wmr", "物品", "wiki"} and not c.query:
        if c.name == "wmr":
            raise QueryError("用法：wmr 武器名 [词条...]，例如 wmr 托里德 暴击率 多重 -变焦。")
        raise QueryError(f"用法：{c.name} 物品名，例如 {c.name} 膛线")
    if c.name not in {"玄骸", "姐妹", "wm", "wmr", "物品", "wiki", "紫卡倾向", "紫卡分析", "裂缝", "钢铁裂缝", "虚空风暴"} and c.query:
        raise QueryError("此指令不接受查询词；平台用 -pc/-ps/-xb/-sw，翻页用 -2。")
    if c.name == 'wmr':
        if c.buy or c.reply:
            raise QueryError('wmr 查询紫卡一口价卖单，不支持 -buy 和 -r。')
        if c.rank is not None and not 0 <= c.rank <= 8:
            raise QueryError('紫卡等级范围为 0—8。')
    if c.name not in {'wm','wmr'} and (c.buy or c.rank is not None or c.reply):
        raise QueryError("-buy、-rank=N 和 -r 仅适用于 wm。")
    return c


HELP = """Warframe 助手 · 国际服
【资料与计算】
遗物 / 部件 / 伤害 / 识卡 / 识卡伤害 / 蹲
奸商 预测 / 词条范围 / 紫卡融合 / 趋势 / 排行
【世界状态】
时间 / 平原 / 地球 / 金星 / 火卫二 / 扎里曼 / 双衍王境
突击 / 执刑官 / 奸商 / 钢铁之路 / 仲裁
裂缝 / 钢铁裂缝 / 虚空风暴 / 入侵
夜灵电波 / 每日特惠 / 新闻 / 活动 / 警报 / 地幔
【玄骸与姐妹】
玄骸 帮助：交易条件与筛选说明（也支持玄骇、wml）
玄骸 布拉玛 毒 55 有幻纹
姐妹 弧电离子枪 磁力 50-60
【物品与市场】
物品 膛线：可交易物品资料，其他物品可用英文名查询
wiki Excalibur：Wiki 搜索链接
wm 膛线：在线卖家，价格从低到高
wm 猴子 / 女枪：战甲俗称，默认 Prime 一套
wm 猴子系统 / 女枪头：指定配件
wm 收购 膛线：在线买家，价格从高到低
wm 膛线 -rank=10 -r：指定等级，图片内显示私聊交易文本
【紫卡交易】
wmr 托里德：查询紫卡一口价
wmr 托里德 暴击率：单词条
wmr 托里德 暴击率 多重 -变焦：同时满足全部词条
wmr 托里德 双暴 3+1 -all：含离线卖家
wmr 帮助：搜索语法；wmr 词条：可用词条
【紫卡】
紫卡倾向 执法者 3+1：倾向与理论数值区间
紫卡分析 托里德 暴击率=162.5 病毒伤害=110.3 伤害=172 多重=-75.5
紫卡分析 + 截图：需配置视觉模型，先识别并确认
【图片主题】
wf 主题：查看个人配色、字号、背景设置
wf 前缀 无 / .：允许 wm、/wm、.wm（个人设置）
【参数】
-pc / -ps / -xb / -sw：平台；默认 PC
-2：第 2 页；裂缝 可追加关键词
所有指令都可加 wf 前缀，如 wf 突击
不支持国服；交易查询不会自动购买或出价。"""
