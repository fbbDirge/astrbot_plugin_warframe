from datetime import datetime, timezone, timedelta
from .client import QueryError
from .commands import WORLD
from .cards import Card
from .localization import localize_world, translate
from .world_icons import mission_cell, relic_cell

WORDS = {"day": "白昼", "night": "夜晚", "warm": "温暖", "cold": "寒冷", "fass": "Fass", "vome": "Vome",
         "fear": "恐惧", "anger": "愤怒", "joy": "喜悦", "envy": "嫉妒", "sorrow": "悲伤",
         "grineer": "Grineer", "corpus": "Corpus", "Lith": "古纪", "Meso": "前纪", "Neo": "中纪", "Axi": "后纪", "Requiem": "安魂",
         "Defense": "防御", "Survival": "生存", "Capture": "捕获", "Exterminate": "歼灭", "Extermination": "歼灭", "Rescue": "救援",
         "Mobile Defense": "移动防御", "Interception": "拦截", "Sabotage": "破坏", "Spy": "间谍",
         "Disruption": "中断", "Excavation": "挖掘", "Assassination": "刺杀", "Free Roam": "自由探索"}


def tr(value):
    return WORDS.get(str(value), translate(value))


def stamp(value):
    if not value:
        return "未知"
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone(timedelta(hours=8))).strftime("%m-%d %H:%M")
    except (ValueError, TypeError):
        return str(value)


def active(row):
    if row.get("completed") or row.get("expired"):
        return False
    try:
        return datetime.fromisoformat(row["expiry"].replace("Z", "+00:00")) > datetime.now(timezone.utc)
    except (KeyError, ValueError, TypeError):
        return True


def reward(r):
    return "、".join([str(x) for x in r.get("items", [])] + [f"{x.get('type', '?')} ×{x.get('count', 1)}" for x in r.get("countedItems", [])] + ([f"{r['credits']} 星币"] if r.get("credits") else [])) or "无"


def paginate(lines, page, size):
    if not lines:
        return "暂无可用数据。"
    pages = (len(lines) + size - 1) // size
    if page > pages:
        raise QueryError(f"只有 {pages} 页，请使用 -1 至 -{pages}。")
    return "\n".join(lines[(page-1)*size:page*size]) + f"\n第 {page}/{pages} 页 · 共 {len(lines)} 条"


def render_world(c, data, size=10):
    data = localize_world(data)
    title = f"【{c.name} · {c.platform}】"
    card_title = f"{c.name} · {c.platform.upper()}"
    time_note = f"数据时间：{stamp(data.get('timestamp'))}（北京时间）"
    footer = f"\n{time_note}"
    if c.name == "时间":
        lines = []
        card_rows = []
        for label, key in WORLD.items():
            if key.endswith("Cycle"):
                raw_state = (data.get(key) or {}).get('state', '未知')
                st = tr(raw_state)
                exp = stamp((data.get(key) or {}).get('expiry'))
                lines.append(f"{label}：{st} · 切换 {exp}")
                role = 'fissure_type' if str(raw_state).lower() in {'day', 'warm', 'fass', 'joy'} else 'fissure_map'
                card_rows.append([(label, 'title'), (st, role), (f"切换 {exp}", 'muted')])
        text = title + "\n" + "\n".join(lines) + footer
        return Card(text, title=card_title, columns=('地区 / 周期', '当前状态', '切换时间'),
                    rows=card_rows, footer=time_note)
    key = WORLD[c.name]
    value = data.get(key)
    if not value:
        text = title + "\n当前无数据，可能尚未开放或接口暂未提供。" + footer
        return Card(text, title=card_title, columns=('状态', '说明'),
                    rows=[[('暂无数据', 'muted'), ('当前无数据，可能尚未开放或接口暂未提供。', 'text')]],
                    footer=time_note)
    lines = []
    card_rows = []
    columns = ('项目', '内容', '备注')
    if key.endswith("Cycle"):
        columns = ('项目', '当前状态 / 候选', '时间 / 备注')
        raw_state = value.get('state', '未知')
        st = tr(raw_state)
        exp = stamp(value.get('expiry'))
        role = 'fissure_type' if str(raw_state).lower() in {'day', 'warm', 'fass', 'joy'} else 'fissure_map'
        lines = [f"当前：{st}", f"切换时间：{exp}"]
        card_rows = [
            [('当前状态', 'title'), (st, role), ('实时周期', 'muted')],
            [('切换时间', 'title'), (exp, 'fissure_map'), ('北京时间', 'muted')],
        ]
        for x in value.get("choices", []):
            cat = '普通回廊' if x.get('category') == 'normal' else '钢铁回廊'
            ch = '、'.join(x.get('choices', []))
            lines.append(f"{cat}：{ch}")
            card_rows.append([(cat, 'riven_stat' if cat == '钢铁回廊' else 'wm_quantity'), (ch or '无', 'text'), ('本周轮换', 'muted')])
    elif key in {"sortie", "archonHunt"}:
        columns = ('阶段', '节点 / 首领', '任务类型', '限定 / 时间')
        boss = value.get('boss', '未知')
        exp = stamp(value.get('expiry'))
        lines = [f"首领：{boss} · 截止 {exp}"]
        card_rows = [[('首领', 'riven_negative'), (str(boss), 'title'), ('突击战役' if key == 'sortie' else '执刑官猎杀', 'fissure_type'), (f"截止 {exp}", 'muted')]]
        for i, x in enumerate(value.get('variants') or value.get('missions') or [], 1):
            node = x.get('node', '?')
            mtype = tr(x.get('missionType', x.get('type', '?')))
            mod = x.get('modifier', '')
            lines.append(f"{i}. {node} · {mtype} {mod}")
            card_rows.append([(f"阶段 {i}", 'wm_user'), (str(node), 'fissure_map'), (mission_cell(mtype, x, value.get('faction')), 'fissure_type'), (str(mod or '标准模式'), 'text')])
    elif key == "voidTrader":
        columns = ('商品 / 信息', '杜卡德 / 地点', '星币 / 时间', '备注')
        char = value.get('character', 'Baro')
        loc = value.get('location', '未知')
        act = stamp(value.get('activation'))
        exp = stamp(value.get('expiry'))
        lines = [f"{char} · {loc}", f"到达 {act} / 离开 {exp}"]
        card_rows = [
            [('虚空商人', 'title'), (str(loc), 'fissure_map'), (str(char), 'wm_user'), ('中继站位置', 'muted')],
            [('停留时间', 'title'), (f"到达 {act}", 'text'), (f"离开 {exp}", 'riven_negative'), ('北京时间', 'muted')],
        ]
        for x in value.get('inventory', []):
            lines.append(f"{x.get('item')}：{x.get('ducats', 0)} 杜卡德 + {x.get('credits', 0)} 星币")
            card_rows.append([(str(x.get('item', '?')), 'title'), (f"{x.get('ducats', 0)} 杜卡德", 'tier_lith'), (f"{x.get('credits', 0)} 星币", 'wm_quantity'), ('在售商品', 'muted')])
    elif key == "steelPath":
        columns = ('项目', '奖励 / 时间', '兑换消耗')
        x = value.get('currentReward', {})
        lines = [f"本周：{x.get('name', '未知')} · {x.get('cost', '?')} 钢铁精华", f"轮换：{stamp(value.get('expiry'))}"]
        card_rows = [
            [('本周奖励', 'title'), (str(x.get('name', '未知')), 'riven_stat'), (f"{x.get('cost', '?')} 钢铁精华", 'wm_price')],
            [('轮换时间', 'title'), (stamp(value.get('expiry')), 'fissure_map'), ('北京时间', 'muted')],
        ]
    elif key == "fissures":
        columns = ('遗物等级', '地图', '任务类型', '截止时间')
        for x in sorted(value, key=lambda x: (x.get('tierNum', 0), x.get('expiry', ''))):
            if not active(x):
                continue
            if c.name == "钢铁裂缝" and not x.get('isHard'):
                continue
            if c.name == "虚空风暴" and not x.get('isStorm'):
                continue
            if c.name == "裂缝" and (x.get('isHard') or x.get('isStorm')):
                continue
            line = f"{tr(x.get('tier'))} · {tr(x.get('missionType'))} · {x.get('node')} · 截止 {stamp(x.get('expiry'))}"
            if not c.query or translate(c.query).casefold() in (line + ' ' + str(x.get('tier')) + ' ' + str(x.get('missionType'))).casefold():
                lines.append(line)
                tier_key = 'tier_' + str(x.get('tier', '')).lower()
                card_rows.append([(relic_cell(tr(x.get('tier')), x.get('tier')), tier_key), (str(x.get('node', '?')), 'fissure_map'), (mission_cell(tr(x.get('missionType')), x), 'fissure_type'), (stamp(x.get('expiry')), 'muted')])
    elif key == "invasions":
        columns = ('节点 / 进度', '进攻方奖励', '防守方奖励')
        for x in value:
            if active(x):
                atk = reward(x.get('attacker', {}).get('reward', {}))
                dfn = reward(x.get('defender', {}).get('reward', {}))
                lines.append(f"{x.get('node')} · {x.get('completion', 0):.1f}%\n进攻：{atk} / 防守：{dfn}")
                card_rows.append([(f"{x.get('node', '?')}\n进度 {x.get('completion', 0):.1f}%", 'fissure_map'), (atk, 'riven_negative'), (dfn, 'wm_user')])
    elif key == "nightwave":
        columns = ('挑战名称', '挑战描述', '声望', '截止时间')
        for x in value.get('activeChallenges', []):
            if active(x):
                lines.append(f"{x.get('title')}：{x.get('desc')} · 声望 {x.get('reputation')} · 截止 {stamp(x.get('expiry'))}")
                card_rows.append([(str(x.get('title', '?')), 'title'), (str(x.get('desc', '?')), 'text'), (f"{x.get('reputation', '?')} 声望", 'riven_stat'), (stamp(x.get('expiry')), 'muted')])
    elif key == "dailyDeals":
        columns = ('特惠商品', '折扣价 / 原价', '剩余数量', '截止时间')
        for x in value:
            if active(x):
                rem = x.get('total', 0) - x.get('sold', 0)
                lines.append(f"{x.get('item')}：{x.get('salePrice')} 白金（原价 {x.get('originalPrice')}）· 剩余 {rem} · 截止 {stamp(x.get('expiry'))}")
                card_rows.append([(str(x.get('item', '?')), 'title'), (f"{x.get('salePrice')} 白金（原价 {x.get('originalPrice')}）", 'wm_price'), (f"剩余 {rem}", 'wm_quantity'), (stamp(x.get('expiry')), 'muted')])
    elif key == "news":
        columns = ('时间', '新闻内容', '相关链接')
        for x in sorted(value, key=lambda x: x.get('date', ''), reverse=True):
            lines.append(f"{stamp(x.get('date'))} {x.get('message')}\n{x.get('link', '')}")
            card_rows.append([(stamp(x.get('date')), 'muted'), (str(x.get('message', '?')), 'title'), (str(x.get('link', '') or '—'), 'wm_user')])
    elif key == "arbitration":
        columns = ('任务节点', '任务类型', '派系 / 状态', '截止时间')
        if active(value):
            lines = [f"{value.get('node', '?')} · {tr(value.get('type', value.get('typeKey', '?')))} · 截止 {stamp(value.get('expiry'))}"]
            card_rows = [[(str(value.get('node', '?')), 'fissure_map'), (mission_cell(tr(value.get('type', value.get('typeKey', '?'))), value), 'fissure_type'), (str(value.get('enemy', '仲裁任务')), 'text'), (stamp(value.get('expiry')), 'muted')]]
    elif key == "sentientOutposts":
        columns = ('任务节点', '派系', '状态', '截止时间')
        mission = value.get('mission', {})
        if active(value):
            lines = [f"{mission.get('node', '?')} · {mission.get('faction', '')} · 截止 {stamp(value.get('expiry'))}"]
            card_rows = [[(str(mission.get('node', '?')), 'fissure_map'), (str(mission.get('faction', 'Sentient')), 'riven_negative'), (mission_cell(tr(mission.get('type', '异常调查')), mission), 'fissure_type'), (stamp(value.get('expiry')), 'muted')]]
    elif key == "alerts":
        columns = ('任务节点', '任务类型', '警报奖励', '截止时间')
        for x in value:
            if active(x):
                m = x.get('mission', {})
                rw = reward(m.get('reward', {}))
                lines.append(f"{m.get('node')} · {tr(m.get('type'))} · 奖励 {rw} · 截止 {stamp(x.get('expiry'))}")
                card_rows.append([(str(m.get('node', '?')), 'fissure_map'), (mission_cell(tr(m.get('type', '?')), m), 'fissure_type'), (rw, 'wm_price'), (stamp(x.get('expiry')), 'muted')])
    elif key == "events":
        columns = ('活动名称', '相关节点', '截止时间')
        for x in value:
            if active(x):
                lines.append(f"{x.get('description', '活动')} · 截止 {stamp(x.get('expiry'))}")
                card_rows.append([(str(x.get('description', '活动')), 'title'), (str(x.get('node') or x.get('victimNode') or '星图活动'), 'fissure_map'), (stamp(x.get('expiry')), 'muted')])
    text = title + "\n" + paginate(lines, c.page, size) + footer
    if not card_rows:
        return Card(text, title=card_title, columns=('状态', '说明'),
                    rows=[[('暂无可用数据', 'muted'), ('当前没有进行中的项目或筛选条件无匹配。', 'text')]],
                    footer=time_note)
    pages = (len(lines) + size - 1) // size
    return Card(text, title=card_title, columns=columns,
                rows=card_rows[(c.page-1)*size:c.page*size],
                footer=f'第 {c.page}/{pages} 页 · 共 {len(lines)} 条' + footer)
