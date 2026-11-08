import html
import re
from urllib.parse import quote
from .client import QueryError
from .cards import Card, IconText
from .item_art import market_art
from .naming import normalized, find_items
from .riven import RivenService
from .riven_market import RivenMarketService
from .lich_market import LichMarketService
from .commands import HELP, WORLD
from .world import paginate, render_world

MARKET = "https://api.warframe.market/v2"
STATUS = "https://api.warframestat.us"

HELP_ROWS = [
    [('世界周期', 'title'), ('时间 / 平原 / 地球 / 金星 / 火卫二 / 扎里曼 / 双衍王境', 'fissure_map'), ('查看全部或单个开放世界与双衍王境轮换', 'text')],
    [('星图任务', 'title'), ('突击 / 执刑官 / 仲裁 / 裂缝 / 钢铁裂缝 / 虚空风暴 / 入侵 / 警报 / 地幔', 'fissure_type'), ('实时任务、裂缝关键词筛选与节点奖励', 'text')],
    [('商店与资讯', 'title'), ('奸商 / 钢铁之路 / 每日特惠 / 夜灵电波 / 新闻 / 活动', 'wm_quantity'), ('虚空商人、每周钢铁精华、电波挑战与特惠', 'text')],
    [('物品与百科', 'title'), ('物品 膛线 · 物品 Excalibur · wiki Excalibur', 'wm_user'), ('可交易物品详情、非交易资料与 Wiki 链接', 'text')],
    [('WM 交易市场', 'title'), ('wm 膛线 · wm 猴子 · wm 收购 膛线 · wm 膛线 -rank=10 -r', 'wm_price'), ('在线卖家/买家、战甲俗称、等级与私聊词', 'text')],
    [('WMR 紫卡市场', 'title'), ('wmr 托里德 暴击率 多重 -变焦 · wmr 词条 · wmr 帮助', 'riven_stat'), ('紫卡一口价挂单、多词条筛选、含离线(-all)', 'text')],
    [('紫卡倾向分析', 'title'), ('紫卡倾向 执法者 3+1 · 紫卡分析 托里德 暴击率=162.5 ...', 'riven_grade'), ('理论数值区间、词条品质评级与截图识别', 'text')],
    [('主题与前缀', 'title'), ('wf 主题 · wf 配色 · wf 字号 · wf 背景 · wf 前缀', 'muted'), ('自定义个人图片配色、字号、背景与指令前缀', 'text')],
]


def name(item, lang="zh-hans"):
    loc = item.get('i18n', {})
    return loc.get(lang, loc.get('en', {})).get('name', item.get('slug', '?'))


def select_orders(orders, command):
    result = [o for o in orders if o.get('type') == ('buy' if command.buy else 'sell')
              and o.get('visible', True) and o.get('quantity', 0) > 0
              and o.get('user', {}).get('status') in {'online', 'ingame'}
              and (command.rank is None or o.get('rank') == command.rank)]
    return sorted(result, key=lambda o: o.get('platinum', 0), reverse=command.buy)


class WarframeService:
    def __init__(self, client, page_size=10):
        self.client = client
        self.page_size = max(5, min(int(page_size), 20))

    async def run(self, c):
        if c.name in {"玄骸", "姐妹"}:
            return await LichMarketService(self.client).run(c)
        if c.name == "wmr":
            return await RivenMarketService(self.client).run(c)
        if c.name in {'紫卡倾向', '紫卡分析'}:
            return await RivenService(self.client, self.page_size).run(c)
        if c.name == '帮助':
            return Card(
                HELP,
                title='Warframe 助手 · 指令指南',
                columns=('功能分类', '常用指令', '说明与示例'),
                rows=HELP_ROWS,
                footer='参数：-pc / -ps / -xb / -sw 切换平台（默认 PC） · -2 翻页 · 所有指令均可加 wf 前缀 · 仅支持国际服',
            )
        if c.name == 'wiki':
            url = 'https://wiki.warframe.com/w/Special:Search?search=' + quote(c.query)
            text = 'Warframe Wiki 搜索：\n' + url
            return Card(
                text,
                title=f'{c.query} · Wiki 搜索',
                columns=('检索词', '搜索链接'),
                rows=[[(c.query, 'title'), (url, 'wm_user')]],
                footer='图片内链接无法直接点击，请手动输入或复制搜索关键词。',
            )
        if c.name in WORLD or c.name == '时间':
            data = await self.client.get(f'{STATUS}/{c.platform}?language=zh', ttl=45)
            if not isinstance(data, dict):
                raise QueryError('世界状态数据格式异常。')
            return render_world(c, data, self.page_size)
        items = await self.client.get(f'{MARKET}/items', ttl=21600)
        matches = find_items(items, c.query, prefer_set=c.name == "wm")
        if not matches and c.name == '物品':
            return await self.general_item(c)
        if not matches:
            text = '未找到可交易物品，请使用完整中文名、英文名或 WM slug。'
            return Card(
                text,
                title=f'{c.query} · 市场查询',
                columns=('状态', '提示信息'),
                rows=[[('未找到物品', 'riven_negative'), (text, 'text')]],
                footer='支持 WM 中文名、英文名、slug 及 40 种战甲常用俗称',
            )
        if len(matches) > 1:
            text = '匹配到多个物品，请使用完整名称重新查询：\n' + paginate([f'{name(x)} ({x["slug"]})' for x in matches], c.page, self.page_size)
            pages = (len(matches) + self.page_size - 1) // self.page_size
            rows = [
                [(name(x), 'title'), (name(x, 'en'), 'wm_user'), (x['slug'], 'muted')]
                for x in matches[(c.page - 1) * self.page_size:c.page * self.page_size]
            ]
            return Card(
                text,
                title=f'{c.query} · 候选可交易物品',
                columns=('中文名称', '英文名称', 'WM 标识 (Slug)'),
                rows=rows,
                footer=f'第 {c.page}/{pages} 页 · 共 {len(matches)} 条 · 请使用完整名称重新查询',
            )
        item = matches[0]
        slug = quote(item['slug'], safe='')
        link = f'https://warframe.market/items/{slug}'
        if c.name == '物品':
            item = await self.client.get(f'{MARKET}/item/{slug}', ttl=3600)
            loc = item.get('i18n', {}).get('zh-hans') or item.get('i18n', {}).get('en', {})
            lines = [f'【{name(item)}】', name(item, 'en')]
            rows = [
                [('中文名称', 'title'), (name(item), 'wm_user')],
                [('英文名称', 'title'), (name(item, 'en'), 'text')],
            ]
            if loc.get('description'):
                desc = html.unescape(re.sub('<[^>]*>', '', loc['description']))
                lines.append(desc)
                rows.append([('物品描述', 'title'), (desc, 'text')])
            for key, label in [('maxRank', '最高等级'), ('reqMasteryRank', '段位要求'), ('ducats', '杜卡德'), ('tradingTax', '交易税')]:
                if key in item:
                    lines.append(f'{label}：{item[key]}')
                    role = 'wm_price' if key in {'ducats', 'tradingTax'} else 'wm_quantity'
                    value = IconText(str(item[key]), {'ducats':'ducats','tradingTax':'credits'}.get(key,''))
                    rows.append([(label, 'title'), (value, role)])
            if 'vaulted' in item:
                v_text = '已入库' if item['vaulted'] else '未入库'
                lines.append('入库状态：' + v_text)
                rows.append([('入库状态', 'title'), (v_text, 'riven_negative' if item['vaulted'] else 'wm_quantity')])
            text = '\n'.join(lines + [link])[:3500]
            return Card(
                text,
                title=f'{name(item)} · 物品资料',
                columns=('属性项目', '详情内容'),
                rows=rows,
                footer=link, artwork=market_art(item),
            )
        if c.rank is not None and ('maxRank' not in item or c.rank > item['maxRank']):
            raise QueryError(f'此物品不支持该等级；最高等级：{item.get("maxRank", "无等级")}。')
        orders = await self.client.get(f'{MARKET}/orders/item/{slug}', platform=c.platform, ttl=30)
        orders = select_orders(orders, c)
        lines = []
        card_rows = []
        for o in orders:
            user = o['user']
            ign = user.get('ingameName') or user.get('slug', '?')
            rank = f' · 等级 {o["rank"]}' if 'rank' in o else ''
            bundle = f' · 每笔 {o["perTrade"]} 件' if o.get('perTrade', 1) != 1 else ''
            lines.append(f'{ign}：{o["platinum"]} 白金 · 库存 {o["quantity"]}{rank}{bundle} · {"游戏中" if user["status"] == "ingame" else "在线"}')
            card_rows.append([(ign, 'wm_user'), (str(o['quantity']), 'wm_quantity'), (str(o['platinum']) + ' 白金', 'wm_price'),
                              ((f"等级 {o['rank']} · " if 'rank' in o else '') + ('游戏中' if user['status'] == 'ingame' else '在线') + bundle, 'muted')])
            if c.reply:
                action = 'sell' if c.buy else 'buy'
                rank_text = f' (rank {o["rank"]})' if 'rank' in o else ''
                lines[-1] += f'\n/w {ign} Hi! I want to {action}: {name(item, "en")}{rank_text} for {o["platinum"]} platinum. (warframe.market)'
        text = f'【{name(item)} · {c.platform} · 在线{"买家" if c.buy else "卖家"}】\n' + (paginate(lines, c.page, 5) if lines else '暂无符合条件的在线订单。') + '\n' + link + '\n报价缓存最多 30 秒，成交前请确认数量和等级。'

        if not orders:
            return Card(
                text,
                title=f'{name(item)} · {c.platform.upper()} · 在线{"买家" if c.buy else "卖家"}',
                columns=('状态', '说明'),
                rows=[[('暂无在线订单', 'muted'), ('当前没有符合条件的在线或游戏中挂单。', 'text')]],
                footer=f'{link}\n报价缓存最多 30 秒，成交前请确认数量和等级。', artwork=market_art(item),
            )
        footer = f'第 {c.page}/{(len(orders)+4)//5} 页 · 共 {len(orders)} 条 · 报价缓存最多 30 秒'
        if c.reply:
            footer += '\n' + '\n'.join(line.split('\n', 1)[1] for line in lines[(c.page-1)*5:c.page*5])
        return Card(text, title=f'{name(item)} · {c.platform.upper()} · 在线{"买家" if c.buy else "卖家"}',
                    columns=('玩家', '数量', '价格', '等级 / 状态'), rows=card_rows[(c.page-1)*5:c.page*5], footer=footer, artwork=market_art(item))

    async def general_item(self, c):
        rows = await self.client.get(f'{STATUS}/items/search/{quote(c.query, safe="")}?language=zh', ttl=3600)
        if not isinstance(rows, list) or not rows:
            text = '未找到物品。非交易物品请尝试英文名，例如 物品 Excalibur。'
            return Card(
                text,
                title=f'{c.query} · 物品资料',
                columns=('状态', '说明'),
                rows=[[('未找到物品', 'riven_negative'), (text, 'text')]],
                footer='非交易物品建议使用英文原名查询',
            )
        exact = [x for x in rows if normalized(x.get('name', '')) == normalized(c.query)]
        rows = exact or rows
        if len(rows) > 1:
            text = '请使用完整物品名：\n' + paginate([x.get('name', '?') for x in rows], c.page, self.page_size)
            pages = (len(rows) + self.page_size - 1) // self.page_size
            card_rows = [
                [(str(x.get('name', '?')), 'title'), (str(x.get('type', '物品')), 'fissure_map'), (str(x.get('category', '资料库')), 'muted')]
                for x in rows[(c.page - 1) * self.page_size:c.page * self.page_size]
            ]
            return Card(
                text,
                title=f'{c.query} · 候选物品列表',
                columns=('物品名称', '类型', '分类'),
                rows=card_rows,
                footer=f'第 {c.page}/{pages} 页 · 共 {len(rows)} 条 · 请使用完整物品名重新查询',
            )
        x = rows[0]
        lines = [f'【{x.get("name")}】', str(x.get('description', '暂无描述'))]
        card_rows = [
            [('物品名称', 'title'), (str(x.get('name', '?')), 'wm_user')],
            [('物品描述', 'title'), (str(x.get('description', '暂无描述')), 'text')],
        ]
        for key, label in [('type', '类型'), ('masteryReq', '段位要求'), ('health', '生命'), ('shield', '护盾'), ('armor', '护甲'), ('damagePerShot', '每发伤害'), ('criticalChance', '暴击率'), ('criticalMultiplier', '暴击倍率')]:
            if key in x:
                lines.append(f'{label}：{x[key]}')
                card_rows.append([(label, 'title'), (str(x[key]), 'riven_stat')])
        text = '\n'.join(lines)[:3500]
        return Card(
            text,
            title=f'{x.get("name", "?")} · 物品资料',
            columns=('属性项目', '详情内容'),
            rows=card_rows,
            footer='数据来源：WarframeStat 物品库',
        )
