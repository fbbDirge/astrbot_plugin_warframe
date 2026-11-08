import json
import re
import sqlite3
from pathlib import Path
from .cards import Card
from .client import QueryError

ARBITRATION_COLORS = {'arb_s':'#B45309', 'arb_a_plus':'#7C3AED', 'arb_a':'#047857', 'arb_a_minus':'#2563EB', 'arb_f':'#BE123C', 'arb_unrated':'#64748B'}

COLORS = {
    **ARBITRATION_COLORS,
    'item_name':'#0369A1','rarity':'#A16207','drop_chance':'#047857','damage':'#C2410C','faction':'#64748B',
    'riven_stat':'#7C3AED', 'riven_range':'#0369A1', 'riven_negative':'#BE185D', 'riven_grade':'#047857',
    'title': '#163D57', 'text': '#334155', 'muted': '#64748B',
    'wm_user': '#2563EB', 'wm_quantity': '#047857', 'wm_price': '#BE185D',
    'tier_lith': '#A16207', 'tier_meso': '#047857', 'tier_neo': '#2563EB',
    'tier_axi': '#7C3AED', 'tier_requiem': '#BE123C', 'tier_omnia': '#0E7490',
    'fissure_map': '#0369A1', 'fissure_type': '#C2410C',
}
FIELDS = {'物品名称':'item_name','稀有度':'rarity','掉率':'drop_chance','伤害数值':'damage','派系':'faction','紫卡属性':'riven_stat','紫卡区间':'riven_range','紫卡负面':'riven_negative','紫卡评级':'riven_grade','标题':'title', '正文':'text', '备注':'muted', '用户名':'wm_user', '数量':'wm_quantity', '价格':'wm_price',
          '古纪':'tier_lith', '前纪':'tier_meso', '中纪':'tier_neo', '后纪':'tier_axi', '安魂':'tier_requiem', '全能':'tier_omnia',
          '地图':'fissure_map', '地图类型':'fissure_type', '任务类型':'fissure_type'}

FIELDS.update(dict(zip(('仲裁S','仲裁A+','仲裁A','仲裁A-','仲裁F','仲裁未评级'), ARBITRATION_COLORS)))

THEME_HELP_ROWS = [
    [('字段配色', 'title'), ('wf 配色 价格 #BE185D\nwf 配色 用户名 #2563EB', 'wm_price'), ('按 #RRGGBB 修改指定字段颜色', 'text')],
    [('字号调节', 'title'), ('wf 字号 28\nwf 字号 标题 42', 'wm_user'), ('正文字号 18—42，标题字号 24—60', 'text')],
    [('背景设置', 'title'), ('wf 背景 #EAF1F6\nwf 背景 图片名.png\nwf 背景 默认', 'wm_quantity'), ('设置纯色背景、预设背景图或恢复默认', 'text')],
    [('重置主题', 'title'), ('wf 主题 重置', 'riven_negative'), ('清空个人主题，恢复管理员默认设置', 'text')],
]


def color(value):
    if not isinstance(value, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
        raise QueryError('颜色请使用 #RRGGBB，例如 #FF8800。')
    return value.upper()


def theme_from(config, personal=None):
    t = {'background_color':'#EAF1F6', 'background_image':'', 'font_path':'', 'font_bold_path':'', 'font_size':26, 'title_size':38, 'panel_opacity':235, 'panel_color':'#FFFFFF', 'line_color':'#DDE6F0', 'logo_image':'', 'background_fit':'cover', 'background_pos':'c', 'background_scale':60, 'background_dim':0}
    t.update(COLORS)
    for key in t:
        value = config.get(key, t[key])
        if key in COLORS or key in {'background_color','panel_color','line_color'}:
            try: value = color(value)
            except QueryError: value = t[key]
        t[key] = value
    for key, value in (personal or {}).items():
        if key in t:
            t[key] = value
    t['font_size'] = max(18,min(42,int(t['font_size'])))
    t['title_size'] = max(24,min(60,int(t['title_size'])))
    t['panel_opacity'] = max(0,min(255,int(t['panel_opacity'])))
    return t


class ThemeStore:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.backgrounds = self.directory / 'backgrounds'
        self.backgrounds.mkdir(exist_ok=True)
        self.db = self.directory / 'themes.sqlite3'
        with sqlite3.connect(self.db) as db:
            db.execute('CREATE TABLE IF NOT EXISTS themes (user TEXT PRIMARY KEY, value TEXT NOT NULL)')

    def get(self, user):
        with sqlite3.connect(self.db) as db:
            row = db.execute('SELECT value FROM themes WHERE user=?',(user,)).fetchone()
        return json.loads(row[0]) if row else {}

    def save(self, user, values):
        with sqlite3.connect(self.db) as db:
            db.execute('INSERT OR REPLACE INTO themes VALUES (?,?)',(user,json.dumps(values)))

    def handle(self, user, text, default_prefixes=None):
        parts = text.strip().removeprefix('/').split()
        if len(parts) < 2 or parts[0].lower() != 'wf' or parts[1] not in {'配色','字号','背景','主题','前缀'}:
            return None
        values = self.get(user)
        cmd, args = parts[1], parts[2:]
        if cmd == '前缀':
            if not args:
                current = '、'.join(x or '无' for x in values.get('command_prefixes', default_prefixes if default_prefixes is not None else ['','/','.']))
                msg = '当前个人前缀：' + current + '\n设置：wf 前缀 无 / .\n恢复全局：wf 前缀 默认\n固定入口 wf 和 /wf 始终可用。'
                return Card(
                    msg,
                    title='个人指令前缀设置',
                    columns=('设置项目', '当前配置 / 指令'),
                    rows=[
                        [('当前个人前缀', 'title'), (current, 'wm_user')],
                        [('自定义前缀', 'title'), ('wf 前缀 无 / .', 'riven_stat')],
                        [('恢复默认前缀', 'title'), ('wf 前缀 默认', 'muted')],
                    ],
                    footer='固定入口 wf 和 /wf 始终可用',
                )
            if args == ['默认']:
                values.pop('command_prefixes',None)
            else:
                prefixes=['' if x=='无' else x for x in args]
                if len(prefixes)>8 or any(x and not re.fullmatch(r'[^\w\s]{1,4}',x) for x in prefixes):
                    raise QueryError('前缀可为 无 或 1—4 个标点，例如 / . !；最多 8 种。')
                values['command_prefixes']=list(dict.fromkeys(prefixes))
            self.save(user,values)
            msg = '指令前缀已保存。固定入口 wf 前缀 默认 可恢复设置。'
            return Card(
                msg,
                title='指令前缀 · 设置已保存',
                columns=('状态', '说明'),
                rows=[[('设置生效', 'wm_quantity'), (msg, 'text')]],
                footer='固定入口 wf 和 /wf 始终可用',
            )
        if cmd == '主题' and args == ['重置']:
            self.save(user,{'command_prefixes': values['command_prefixes']} if 'command_prefixes' in values else {})
            msg = '个人主题已重置，恢复管理员设置的默认主题。'
            return Card(
                msg,
                title='个人主题 · 已重置',
                columns=('状态', '说明'),
                rows=[[('恢复默认', 'wm_quantity'), (msg, 'text')]],
                footer='之后的查询图片会使用管理员默认主题',
            )
        if cmd == '主题' and not args:
            msg = ('主题设置（仅影响你自己的查询）\nwf 配色 价格 #BE185D\nwf 配色 用户名 #2563EB\nwf 字号 28\nwf 字号 标题 42\nwf 背景 #EAF1F6\nwf 背景 图片名.png\nwf 背景 默认\nwf 主题 重置\n可用配色字段：' + '、'.join(FIELDS))
            return Card(
                msg,
                title='个人图片主题 · 设置指南',
                columns=('定制项目', '指令示例', '说明'),
                rows=THEME_HELP_ROWS,
                footer='可用配色字段：' + '、'.join(FIELDS),
            )
        if cmd == '配色' and len(args) == 2:
            field = FIELDS.get(args[0], args[0])
            if field not in COLORS:
                raise QueryError('未知配色字段：' + '、'.join(FIELDS))
            values[field] = color(args[1])
        elif cmd == '字号' and len(args) in {1,2}:
            field = 'font_size'
            if len(args) == 2:
                if args[0] not in {'标题','正文'}:
                    raise QueryError('用法：wf 字号 标题 42 或 wf 字号 28')
                field = 'title_size' if args[0] == '标题' else 'font_size'
            if not args[-1].isdigit():
                raise QueryError('字号需要填写整数。')
            n = int(args[-1]); low,high = (24,60) if field == 'title_size' else (18,42)
            if not low <= n <= high:
                raise QueryError(f'字号范围：{low}—{high}。')
            values[field] = n
        elif cmd == '背景' and not args:
            files = sorted(p.name for p in self.backgrounds.iterdir() if p.suffix.lower() in {'.png','.jpg','.jpeg','.webp'})[:30]
            msg = '可用背景：\n' + ('\n'.join(files) or '暂无图片，请管理员将背景图片放入插件数据目录的 backgrounds 文件夹。') + '\n也可发送 wf 背景 #EAF1F6 设置纯色背景。'
            rows = (
                [[(f'背景 #{i}', 'title'), (fn, 'wm_user')] for i, fn in enumerate(files, 1)]
                if files else
                [[('暂无背景图', 'muted'), ('请管理员将背景图片放入插件数据目录的 backgrounds 文件夹。', 'text')]]
            )
            return Card(
                msg,
                title='个人背景图片 · 可选列表',
                columns=('项目', '文件名称 / 说明'),
                rows=rows,
                footer='发送 wf 背景 文件名 切换图片，或发送 wf 背景 #EAF1F6 设置纯色背景',
            )
        elif cmd == '背景' and len(args) == 1:
            if args[0] == '默认':
                values.pop('background_image',None); values.pop('background_color',None)
            elif args[0].startswith('#'):
                values['background_color'] = color(args[0]); values['background_image'] = ''
            else:
                p = (self.backgrounds / args[0]).resolve()
                if p.parent != self.backgrounds.resolve() or not p.is_file() or p.suffix.lower() not in {'.png','.jpg','.jpeg','.webp'}:
                    raise QueryError('背景不存在，请发送 wf 背景 查看可用图片。')
                values['background_image'] = str(p)
        else:
            raise QueryError('主题指令格式不正确，请发送 wf 主题 查看用法。')
        self.save(user,values)
        msg = '个人主题已保存。之后的查询图片会使用此设置。'
        return Card(
            msg,
            title='个人主题 · 设置已保存',
            columns=('状态', '说明'),
            rows=[[('设置生效', 'wm_quantity'), (msg, 'text')]],
            footer='仅影响你自己的查询图片 · 发送 wf 主题 重置 可恢复默认',
        )
