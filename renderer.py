"""Local Pillow renderer. No browser service or remote image rendering needed."""
import logging
import math
import re
import uuid
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
from .cards import Card
from .bundled_assets import image_path
from .stat_icons import STAT_ICONS
from .cycle_icons import CYCLE_ICONS
from .planet_icons import PLANET_ASSETS
from .reward_icons import REWARD_ASSETS
from .display_icons import line_icon, ELEMENT_ICONS, CURRENCY_ICONS, icon_lines

FONT = Path(__file__).parent / 'assets/fonts/NotoSansSC.ttf'
if not FONT.is_file():
    FONT = Path(__file__).parent / 'core/data/fonts/NotoSansCJKsc-Subset-Regular.otf'
LOG = logging.getLogger(__name__)
ICON_DIR = Path(__file__).parent / 'assets/icons'
ICON_NAMES = {*PLANET_ASSETS, 'regal_aya', *('reward_category_'+v for v in ('scene','glyph','cosmetic','decoration','bundle','music','item')), 'bounty_document', *REWARD_ASSETS, *CYCLE_ICONS.values(), *STAT_ICONS.values(), 'forma', 'moonflesh','void', 'tau', 'true', 'narmer', 'duviri', 'murmur', 'techrot', 'scaldra', *CURRENCY_ICONS.values(), 'platinum', *ELEMENT_ICONS.values(), 'grineer', 'corpus', 'infested', 'sentient', 'orokin', 'lith', 'meso', 'neo', 'axi', 'requiem'}


def load_icon(name, size):
    if name.startswith('blueprint:'):
        base=load_icon(name.removeprefix('blueprint:'),max(16,size-6))
        if base is None:return None
        tile=Image.new('RGBA',(size,size),(26,76,119,255));d=ImageDraw.Draw(tile)
        d.rectangle((0,0,size-1,size-1),outline='#92D7FF',width=1)
        tile.alpha_composite(base,((size-base.width)//2,(size-base.height)//2))
        d.line((3,size-4,size-4,size-4),fill='#C5E8FF',width=1)
        return tile
    if name.startswith('bounty:'):
        from .bounty_art import bounty_path
        path=bounty_path(name.removeprefix('bounty:'))
        if path is None:return None
    elif name.startswith('component:'):
        from .component_art import component_path
        path=component_path(name.removeprefix('component:'))
        if path is None:return None
    elif name.startswith('equipment:'):
        from .equipment_art import equipment_path
        path = equipment_path(name.removeprefix('equipment:'))
        if path is None:return None
    elif name.startswith('weapon:'):
        from .weapon_art import weapon_path
        path = weapon_path(name.removeprefix('weapon:'))
        if path is None:return None
    elif name in ICON_NAMES:
        path = ICON_DIR / (name + '.png')
    else:
        return None
    try:
        resolved = image_path(path)
        return _read_icon(str(resolved), size, name, resolved.stat().st_mtime_ns)
    except (OSError, ValueError):
        return None


@lru_cache(maxsize=256)
def _read_icon(path, size, name, mtime):
    # Cache successful reads only; missing/corrupt assets can recover after refresh.
    with Image.open(path) as source:
        icon = ImageOps.contain(source.convert('RGBA'), (size, size))
        if name == 'ducats':
            light = Image.new('RGBA', icon.size, (255, 255, 255, 255))
            light.putalpha(icon.getchannel('A'))
            icon = light
        return icon



PILL_ROLES = {
    'tier_lith', 'tier_meso', 'tier_neo', 'tier_axi', 'tier_requiem', 'tier_omnia',
    'riven_grade', 'fissure_type', 'rarity',
    'roll_s','roll_a','roll_b','roll_c','roll_d','roll_unknown',
    'arb_s', 'arb_a_plus', 'arb_a', 'arb_a_minus', 'arb_f', 'arb_unrated',
}

FACTION_STYLES = {
    'G佬': ('#DC2626', (254, 242, 242)), 'Grineer': ('#DC2626', (254, 242, 242)),
    'C佬': ('#0284C7', (240, 249, 255)), 'Corpus': ('#0284C7', (240, 249, 255)),
    'I佬': ('#7C3AED', (250, 245, 255)), 'Infested': ('#7C3AED', (250, 245, 255)), 'Infestation': ('#7C3AED', (250, 245, 255)),
    '堕落者': ('#B45309', (255, 251, 235)), 'Orokin': ('#B45309', (255, 251, 235)), 'Corrupted': ('#B45309', (255, 251, 235)),
    '合一众': ('#C2410C', (255, 247, 237)), 'Sentient': ('#C2410C', (255, 247, 237)), 'S佬': ('#C2410C', (255, 247, 237)),
    '低语者': ('#0F766E', (240, 253, 250)), '科腐者': ('#15803D', (240, 253, 244)), '炽蛇军': ('#B91C1C', (254, 242, 242)),
    '双衍王境': ('#6D28D9', (245, 243, 255)), 'Duviri': ('#6D28D9', (245, 243, 255)),
}

COL_ACCENTS = ('#0284C7', '#7C3AED', '#D97706', '#059669', '#E11D48', '#0D9488')
_PLANET_PAREN_RE = re.compile(
    r'([A-Za-z0-9\u4e00-\u9fa5_\s\'-]+?)\s*[（(]'
    r'([\u4e00-\u9fa5]{2,6}|Earth|Venus|Mercury|Mars|Phobos|Deimos|Ceres|Jupiter|Europa|Saturn|Uranus|Neptune|Pluto|Sedna|Eris|Void|Lua|Zariman)'
    r'[）)]$'
)
ROW_FALLBACK_ACCENTS = ('#0284C7', '#7C3AED', '#0D9488', '#D97706', '#2563EB', '#E11D48')


def _rgb(value, default=(51, 65, 85)):
    if isinstance(value, str) and len(value) == 7 and value.startswith('#'):
        try:
            return int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)
        except ValueError:
            pass
    return default


def _mix(c1, c2, weight=0.5):
    return tuple(int(a * (1 - weight) + b * weight) for a, b in zip(c1, c2))


def _draw_centered(d, box, text, font, fill):
    x1, y1, x2, y2 = box
    l, t, r, b = font.getbbox(text)
    tx = x1 + (x2 - x1 - (r - l)) // 2 - l
    ty = y1 + (y2 - y1 - (b - t)) // 2 - t
    d.text((tx, ty), text, font=font, fill=fill, anchor='la')


def _icon_badge_style(name):
    if not name:
        return (35, 49, 65, 245), (100, 116, 139, 150)
    if name.startswith(('weapon:', 'equipment:', 'component:', 'blueprint:')):
        return (232, 240, 250, 248), (56, 189, 248, 175)
    if name in PLANET_ASSETS:
        return (17, 28, 48, 248), (56, 189, 248, 210)
    if name in {'lith', 'forma', 'ducats', 'aya', 'regal_aya', 'endo'}:
        return (48, 34, 20, 245), (245, 158, 11, 215)
    if name in {'meso', 'toxin', 'viral', 'gas'}:
        return (18, 45, 38, 245), (16, 185, 129, 210)
    if name in {'neo', 'credits', 'platinum', 'cold', 'magnetic', 'electricity', 'corpus'}:
        return (18, 36, 58, 245), (14, 165, 233, 215)
    if name in {'axi', 'infested', 'corrosive'} or name.startswith('stat_'):
        return (36, 24, 58, 245), (168, 85, 247, 210)
    if name in {'requiem', 'grineer', 'heat', 'blast', 'kuva', 'sentient'}:
        return (52, 22, 30, 245), (244, 63, 94, 210)
    return (28, 40, 56, 245), (125, 211, 252, 175)


def _draw_clock(d, cx, cy, r, color):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color, width=2)
    d.line((cx, cy, cx, cy - r + 3), fill=color, width=2)
    d.line((cx, cy, cx + r - 3, cy + 1), fill=color, width=2)


def _draw_hex_badge(d, x, y, size, label, font, is_neg=False):
    cx, cy = x + size // 2, y + size // 2
    r = size // 2
    pts = [(cx + int(r * math.cos(math.radians(60 * k - 30))), cy + int(r * math.sin(math.radians(60 * k - 30)))) for k in range(6)]
    fill = (255, 228, 230, 245) if is_neg else (204, 251, 241, 245)
    outline = (225, 29, 72, 220) if is_neg else (13, 148, 136, 220)
    fg = '#BE123C' if is_neg else '#0F766E'
    d.polygon(pts, fill=fill, outline=outline)
    _draw_centered(d, (x, y, x + size, y + size), label, font, fg)
    return size + 8


def _draw_row_bracket(d, x, y, w, h, main_hex, sub_hex='#06B6D4'):
    c1 = _rgb(main_hex)
    c2 = _rgb(sub_hex)
    # Soft left glow strip
    d.rounded_rectangle((x + 1, y + 2, x + 16, y + h - 2), radius=10, fill=(*c1, 18))
    # Hooked bracket [ spine + top/bottom hooks
    d.rounded_rectangle((x, y + 4, x + 5, y + h - 4), radius=2, fill=(*c1, 245))
    d.rounded_rectangle((x, y + 3, x + 14, y + 6), radius=2, fill=(*c1, 235))
    d.rounded_rectangle((x, y + h - 6, x + 14, y + h - 3), radius=2, fill=(*c1, 235))
    # Mid-spine accent diamond/dot
    my = y + h // 2
    d.polygon([(x + 3, my - 4), (x + 7, my), (x + 3, my + 4)], fill=(*c2, 230))
    # Right-top & right-bottom subtle corner ticks
    rx = x + w
    d.line((rx - 12, y + 4, rx - 4, y + 4), fill=(*c1, 95), width=2)
    d.line((rx - 4, y + 4, rx - 4, y + 12), fill=(*c1, 95), width=2)
    d.line((rx - 12, y + h - 4, rx - 4, y + h - 4), fill=(*c2, 85), width=2)
    d.line((rx - 4, y + h - 12, rx - 4, y + h - 4), fill=(*c2, 85), width=2)


def _draw_panel_decor(d, width, height, panel_x, title_rgb, header_bottom, small_font, badge_font, skip_art=False):
    # Subtle top header banner tint
    d.rounded_rectangle(
        (panel_x + 3, 19, width - panel_x - 3, min(height - 22, header_bottom)),
        radius=25,
        fill=(*_mix(title_rgb, (236, 246, 255), 0.88), 150),
    )
    # Inner 1px highlight frame
    d.rounded_rectangle(
        (panel_x + 4, 20, width - panel_x - 4, height - 20),
        radius=24,
        outline=(186, 230, 253, 120),
        width=1,
    )
    # Four corner tech brackets
    L = 24
    p1, p2, q1, q2 = panel_x + 8, 24, width - panel_x - 8, height - 24
    for (bx, by, dx, dy, col) in (
        (p1, p2, 1, 1, (14, 165, 233, 180)),
        (q1, p2, -1, 1, (245, 158, 11, 180)),
        (p1, q2, 1, -1, (124, 58, 237, 165)),
        (q1, q2, -1, -1, (16, 185, 129, 175)),
    ):
        d.line((bx, by, bx + dx * L, by), fill=col, width=2)
        d.line((bx, by, bx, by + dy * L), fill=col, width=2)
    # Subtle geometric octagonal / star-compass watermarks in negative space
    centers = [(width - 145, height - 130, 74, (124, 58, 237, 13), (14, 165, 233, 15))]
    if not skip_art:
        centers.append((width - 150, 150, 58, (14, 165, 233, 15), (245, 158, 11, 14)))
    if height > 620:
        centers.append((145, height // 2 + 40, 62, (16, 185, 129, 11), (14, 165, 233, 12)))
    for wcx, wcy, wr, wc1, wc2 in centers:
        oct1 = [(wcx + int(wr * math.cos(math.radians(45 * k + 22.5))), wcy + int(wr * math.sin(math.radians(45 * k + 22.5)))) for k in range(8)]
        oct2 = [(wcx + int(wr * 0.68 * math.cos(math.radians(45 * k))), wcy + int(wr * 0.68 * math.sin(math.radians(45 * k)))) for k in range(8)]
        d.polygon(oct1, outline=wc1)
        d.polygon(oct2, outline=wc2)
        d.ellipse((wcx - wr // 3, wcy - wr // 3, wcx + wr // 3, wcy + wr // 3), outline=wc1)
    # Bottom status bar inside the bottom margin
    _, b_top, _, b_bot = badge_font.getbbox('PC')
    bh = (b_bot - b_top) + 8
    by = height - bh - 16
    d.line((panel_x + 16, by - 6, width - panel_x - 16, by - 6), fill=(203, 213, 225, 125), width=1)
    pc_w = int(badge_font.getlength('PC')) + 20
    pc_box = (panel_x + 16, by, panel_x + 16 + pc_w, by + bh)
    d.rounded_rectangle(pc_box, radius=bh // 2, fill=(220, 252, 231, 235), outline=(16, 185, 129, 190), width=1)
    _draw_centered(d, pc_box, 'PC', badge_font, '#047857')
    _draw_centered(
        d,
        (panel_x + 24 + pc_w, by, panel_x + 24 + pc_w + int(badge_font.getlength('Warframe 智库终端  ·  星际战甲全息数据视图')), by + bh),
        'Warframe 智库终端  ·  星际战甲全息数据视图',
        badge_font,
        (100, 116, 139, 215),
    )
    # Right side multi-color status dots
    for idx, dot_c in enumerate(((14, 165, 233, 205), (124, 58, 237, 205), (245, 158, 11, 205), (16, 185, 129, 205))):
        dx = width - panel_x - 22 - idx * 16
        d.ellipse((dx - 4, by + bh // 2 - 4, dx + 4, by + bh // 2 + 4), fill=dot_c)


class CardRenderer:
    WIDTH = 1900
    MARGIN = 10

    def __init__(self, output):
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def wrap(text, font, width):
        result = []
        for raw in str(text).split('\n'):
            line = ''
            # Keep Latin words and numbers together unless a token exceeds a column.
            for token in re.findall(r'[+−-]?\d+(?:\.\d+)?(?:%|m|s)?|[A-Za-z0-9_]+(?:[.,%-][A-Za-z0-9_]+)*|[^A-Za-z0-9_]', raw):
                if line and token in '）)，。；：':
                    line += token
                    continue
                if line and font.getlength(line + token) > width:
                    result.append(line.rstrip())
                    line = ''
                if not line and token.isspace():
                    continue
                for char in token:
                    if line and font.getlength(line + char) > width:
                        result.append(line)
                        line = ''
                    line += char
            result.append(line)
        return result

    @classmethod
    def wrap_cell(cls, text, role, font, width, icon_size):
        lines, icons = [], []
        for raw in icon_lines(text, role):
            icon = line_icon(raw, role)
            if load_icon(icon, icon_size) is None:
                icon = ''
            if icon=='platinum' and re.fullmatch(r'\d[\d,.]*\s*(?:白金|platinum)(?:\s*[（(][^）)]{1,10}[）)])?',raw,re.I):
                raw=re.sub(r'\s*(?:白金|platinum)','',raw,count=1,flags=re.I)
                if re.fullmatch(r'\d+\.0+',raw):raw=str(int(float(raw)))
            avail = max(40, width - (icon_size + 10 if icon else 0))
            spec_re = r'(?:循环\s*\d+|等级\s*\d+(?:/\d+)?|\d+\s*洗|MR\s*\d+|段位\s*\d+|信誉\s*[\d—-]+|[23]正[01]负|\d+级)'
            s_parts = [p.strip() for p in raw.split('·') if p.strip()] if '·' in raw else []
            s_raw = raw.strip()
            m_np = _PLANET_PAREN_RE.fullmatch(s_raw)
            m_pol = re.match(r'^(正\s*·\s*|正·|正面[：:]\s*|▲\s*|负\s*·\s*|负·|负面[：:]\s*|▼\s*)(.+)$', s_raw)
            is_pill_tok = (
                s_raw in FACTION_STYLES
                or s_raw in {'钢铁', '九重天', '无', '设置生效'}
                or (role in PILL_ROLES and len(s_raw) <= (10 if role.startswith('arb_') else 6))
                or (role in {'wm_quantity', 'drop_chance'} and len(s_raw) <= 12)
            )
            is_time_tok = (
                role in {'muted', 'text', 'title'}
                and bool(re.fullmatch(r'(?:剩[余]?|约\s*)?\d+\s*(?:天|小时|时|分钟|分|秒)(?:\s*\d+\s*(?:小时|时|分钟|分|秒))*|\d{1,2}日\d{1,2}时(?:\d{1,2}分)?', s_raw))
            )
            if s_parts and all(re.fullmatch(spec_re, p) for p in s_parts) and sum(font.getlength(p) * 0.72 + 16 for p in s_parts) <= avail + 24:
                wrapped = [s_raw]
            elif m_np and (font.getlength(m_np.group(1).strip()) * 0.89 + font.getlength(m_np.group(2).strip()) * 0.72 + 20 <= avail + 16):
                wrapped = [s_raw]
            elif is_pill_tok and font.getlength(s_raw) * 0.72 <= avail + 12:
                wrapped = [s_raw]
            elif is_time_tok and font.getlength(s_raw) * 0.75 <= avail + 16:
                wrapped = [s_raw]
            elif m_pol and font.getlength(m_pol.group(2).strip()) + icon_size + 10 <= avail + 16:
                wrapped = [s_raw]
            else:
                wrapped = cls.wrap(raw, font, avail)
            lines.extend(wrapped)
            icons.extend([icon] + [''] * (len(wrapped) - 1))
        return lines, icons

    @staticmethod
    def draw_inline_icon(canvas, draw, name, x, y, size):
        icon = load_icon(name, size)
        if icon is None:
            return 0
        bg_fill, bg_outline = _icon_badge_style(name)
        draw.rounded_rectangle((x - 2, y - 2, x + size + 2, y + size + 2), radius=6, fill=bg_fill, outline=bg_outline, width=1)
        canvas.paste(icon, (int(x + (size - icon.width) // 2), int(y + (size - icon.height) // 2)), icon)
        return size + 10

    @staticmethod
    def _column_ratios(columns, rows=None):
        if tuple(columns) == ('词条','区间','距中','区间位','评分'):
            return (.36,.28,.11,.10,.15)
        if tuple(columns) == ('档位','词条','挂牌价差','对照样本'):
            return (.08,.32,.25,.35)
        if tuple(columns) == ('词条','数值','评分'):
            return (.48,.28,.24)
        if tuple(columns) == ('档位','词条','适用条件'):
            return (.12,.32,.56)
        n = len(columns)
        if n <= 1:
            return (1.0,)
        if n == 6 and columns[0] in {'遗物等级', '纪元', '档位'}:
            return (.13, .13, .29, .16, .11, .18)
        if n == 6 and columns[0] in {'地点', '节点', '地图'}:
            return (.25, .12, .14, .11, .22, .16)
        if n == 6 and columns[0] == '时间':
            return (.15, .27, .15, .15, .19, .09)
        if n == 6 and columns[0] == '阶段':
            return (.07, .28, .12, .17, .15, .21)
        if n == 6 and columns[0] == '稀有度':
            return (.11, .41, .12, .15, .11, .10)
        if n == 6 and columns[0] in {'卖家', '买家'}:
            return (.25, .10, .20, .11, .18, .16)
        if tuple(columns) == ('纪元', '节点', '类型', '派系', '剩余'):
            return (.15, .33, .14, .18, .20)
        if n == 5 and columns[0] in {'遗物等级', '纪元', '档位'}:
            return (.15, .14, .33, .18, .20)
        if n == 5 and columns[0] in {'地点', '节点', '地图', '任务节点'}:
            return (.28, .14, .11, .30, .17)
        if n == 5 and columns[0] == '阶段':
            return (.08, .31, .16, .25, .20)
        if tuple(columns)==('轮换','商品','价格','说明'):return (.10,.42,.18,.30)
        if tuple(columns)==('商品','杜卡德','现金'):return (.56,.18,.26)
        if tuple(columns)==('商品','价格','每周限购'):return (.62,.29,.09)
        if tuple(columns)==('奖励','稀有度','几率'):return (.58,.21,.21)
        if tuple(columns)==('名称','详情','详情'):return (.24,.26,.50)
        if tuple(columns) == ('词条', '区间', '距中', '区间位'):
            return (.40, .32, .14, .14)
        if tuple(columns) == ('匹配词条', '最低', '在线最低', '中位'):
            return (.44, .20, .20, .16)
        if n > 4:
            return tuple(1 / n for _ in columns)
        first = columns[0]
        if n == 2:
            if first == '奖励物品':
                return (.75, .25)
            if first == '商品':
                return (.68, .32)
            if first in {'词条', '元素', '派系'}:
                return (.64, .36)
            if first in {'指令示例', '检索词', '筛选条件', '识别项目'}:
                return (.34, .66)
            if tuple(columns) == ('名称', '数值') and rows:
                max_c0 = max((len(str(r[0][0])) for r in rows if r), default=0)
                max_c1 = max((len(str(r[1][0])) for r in rows if len(r) > 1), default=0)
                if max_c0 > max_c1:
                    return (.62, .38)
            return (.26, .74)
        if n == 3:
            if first == '功能分类':
                return (.18, .37, .45)
            if first == '时间':
                return (.20, .48, .32)
            if first == '节点 / 进度':
                return (.28, .36, .36)
            if first == '中文名称':
                return (.28, .44, .28)
            return (.26, .42, .32)
        if columns == ('节点','任务类型','派系','剩余'):return (.34,.23,.18,.25)
        if first == '类型':return (.24,.22,.22,.32)
        if first == '项目':return (.32,.19,.11,.38)
        if first == '阵营':return (.18,.22,.18,.42)
        if first == '结构 / 等级':return (.15,.46,.18,.21)
        if first == '任务节点':
            return (.29, .23, .28, .20)
        if first == '遗物等级':
            return (.20, .30, .28, .22)
        if first == '属性 / 实际值':
            return (.31, .29, .24, .16)
        if first == '词条':
            return (.34, .34, .16, .16)
        if first == '武器':
            return (.30, .18, .24, .28)
        if first == '属性':
            return (.23, .33, .34, .10)
        if tuple(columns) == ('卖家', '一口价 / 状态', '完整词条', '卡片信息'):
            return (.20, .15, .46, .19)
        if first == '卖家':
            return (.26, .20, .32, .22)
        if first == '玩家':
            return (.32, .13, .23, .32)
        return (.24, .32, .24, .20)

    @staticmethod
    def _compact_cell_text(text, role):
        if getattr(text, 'icon', '') or not isinstance(text, str):
            return text
        if role in {'riven_stat', 'riven_negative'}:
            text = re.sub(r'射速\s*/\s*攻击速度', '射速/攻速', text)
            text = re.sub(r'基础伤害\s*/\s*近战伤害', '基础伤害', text)
        if '\n' not in text:
            return text
        raw_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if len(raw_lines) <= 1:
            return text
        spec_re = r'(?:循环\s*\d+|等级\s*\d+(?:/\d+)?|\d+\s*洗|MR\s*\d+|段位\s*\d+|信誉\s*[\d—-]+|[23]正[01]负|\d+级)'
        if role == 'wm_user' and len(raw_lines) >= 3:
            sub_tokens = [p.strip() for ln in raw_lines[1:] for p in ln.split('·') if p.strip()]
            if sub_tokens and all(re.fullmatch(spec_re, p) for p in sub_tokens):
                return raw_lines[0] + '\n' + ' · '.join(sub_tokens)
        if role == 'muted' and len(raw_lines) == 3 and all(re.fullmatch(spec_re, ln) for ln in raw_lines):
            return f'{raw_lines[0]} · {raw_lines[2]}\n{raw_lines[1]}'
        return text

    @staticmethod
    def _line_color(line, role, line_idx, theme):
        stripped = line.strip()
        if role == 'riven_stat':
            if stripped.startswith(('负 ·', '负·', '负面')):
                return theme.get('riven_negative', theme['text'])
            if stripped.startswith(('正 ·', '正·')):
                return theme.get('riven_stat', theme['text'])
        if role == 'wm_price' and line_idx > 0:
            if stripped in {'游戏中', '在线'}:
                return theme.get('wm_quantity', theme['muted'])
            if stripped == '离线':
                return theme['muted']
        if line_idx > 0 and role in {'title', 'fissure_map'} and stripped.startswith(('进度 ', '离开 ', '到达 ')):
            return theme['muted']
        return theme.get(role, theme['text'])

    def render(self, result, theme):
        if isinstance(result, Card) and '紫卡分析' in result.title and self.WIDTH < 2400:
            # A per-call renderer keeps concurrent queries at their own widths.
            wide = CardRenderer(self.output)
            wide.WIDTH = 2400
            return wide.render(result, theme)
        if getattr(result,'kind','')=='incarnon_detail':
            from .incarnon_card import render
            return render(self,result,theme)
        from .weapon_art import decorate
        decorate(result)
        if getattr(result, "blocks", None):
            return self.render_report(result, theme)
        font_path = theme.get('font_path') or str(FONT)
        bold_path = theme.get('font_bold_path') or font_path
        body_size = round(56 * (theme['font_size'] / 26) ** 0.50)
        eff_title_size = round(70 * (theme['title_size'] / 38) ** 0.50)
        small_size = max(38, round(body_size * 0.80))
        pill_size = max(42, round(body_size * 0.90))
        badge_size = max(36, round(body_size * 0.73))
        if theme.get('_sub_tile'):
            eff_title_size = max(small_size + 4, round(body_size * 1.04))
        try:
            font = ImageFont.truetype(font_path, body_size)
            bold_font = ImageFont.truetype(bold_path, body_size)
            title_font = ImageFont.truetype(bold_path, eff_title_size)
            small = ImageFont.truetype(font_path, small_size)
            header_font = ImageFont.truetype(font_path, small_size)
            pill_font = ImageFont.truetype(bold_path, pill_size)
            badge_font = ImageFont.truetype(font_path, badge_size)
        except OSError:
            font = ImageFont.truetype(str(FONT), body_size)
            bold_font = ImageFont.truetype(str(FONT), body_size)
            title_font = ImageFont.truetype(str(FONT), eff_title_size)
            small = ImageFont.truetype(str(FONT), small_size)
            header_font = ImageFont.truetype(str(FONT), small_size)
            pill_font = ImageFont.truetype(str(FONT), pill_size)
            badge_font = ImageFont.truetype(str(FONT), badge_size)
        for face, weight in (
            (font, 500),
            (bold_font, 700),
            (title_font, 750),
            (small, 480),
            (header_font, 650),
            (pill_font, 680),
            (badge_font, 660),
        ):
            try:
                axes = face.get_variation_axes()
                face.set_variation_by_axes([
                    max(a['minimum'], min(a['maximum'], weight)) if a['name'] == b'Weight' else a['default']
                    for a in axes
                ])
            except (OSError, AttributeError):
                pass

        structured = isinstance(result, Card) and bool(result.rows)
        raw = str(result).splitlines()
        if isinstance(result, Card) and result.title:
            title = result.title
        else:
            title = raw[0].strip('【】') if raw else 'Warframe 助手'
        body = '\n'.join(raw[1:]) if not structured else ''
        if not structured and not body:
            body, title = title, 'Warframe 助手 · 提示'

        width = self.WIDTH
        panel_x = 8
        x = self.MARGIN + panel_x
        inner = width - 2 * x
        is_tile = bool(theme.get('_report_tile'))
        is_sub_tile = bool(theme.get('_sub_tile'))
        hide_title = bool(theme.get('_hide_title'))
        hide_col_header = bool(theme.get('_hide_col_header'))

        artwork = None
        art_path = getattr(result, 'artwork_path', None)
        if art_path:
            try:
                with Image.open(art_path) as source:
                    if source.width * source.height <= 4_000_000:
                        artwork = ImageOps.contain(source.convert('RGBA'), (158, 158))
            except (OSError, ValueError, Image.DecompressionBombError):
                pass
        title_lines = [] if hide_title else self.wrap(title, title_font, inner - (204 if artwork else 20))
        _, t_top, _, t_bot = title_font.getbbox('国Ag0')
        t_opt_h = t_bot - t_top
        title_line_step = t_opt_h + 10
        title_block_h = 0 if hide_title else (max(1, len(title_lines)) * t_opt_h + max(0, len(title_lines) - 1) * 10)

        if artwork is not None and not hide_title:
            title_block_h = max(title_block_h, 166)

        _, f_top, _, f_bot = font.getbbox('国Ag0')
        f_opt_h = f_bot - f_top
        line_gap = 8
        line_step = f_opt_h + line_gap

        _, s_top, _, s_bot = small.getbbox('国Ag0')
        s_opt_h = s_bot - s_top
        small_gap = 6
        small_step = s_opt_h + small_gap

        icon_size = max(60, min(86, body_size + 6))
        icon_gap = icon_size + 10
        blocks = []
        use_two_col_grid = False
        show_col_header = False
        if structured:
            show_col_header = len(result.columns) > 1 and not hide_col_header
            ratios = self._column_ratios(result.columns, result.rows)
            col_gap = 16
            half_inner = (inner - col_gap) // 2
            can_two_col = (
                len(result.rows) >= 2
                and (
                    (len(result.columns) in {1, 2} and result.columns[0] in {'奖励物品', '奖励', '物品', '商品', '元素', '派系'})
                    or (tuple(result.columns) == ('词条', '数值'))
                    or tuple(result.columns) in {
                        ('奖励', '稀有度', '几率'),
                        ('商品', '价格', '每周限购'),
                    }
                )
            )
            if can_two_col:
                h_widths = [int(half_inner * r) for r in ratios]
                h_widths[-1] = half_inner - sum(h_widths[:-1])
                test_blocks = []
                max_observed_lines = 1
                single_count = 0
                for row in result.rows:
                    cell_data = [
                        self.wrap_cell(
                            self._compact_cell_text(text, role),
                            role if not getattr(text, 'icon', '') else 'muted',
                            font,
                            max(40, w - 22 - (icon_gap if load_icon(getattr(text, 'icon', ''), icon_size) is not None else 0)),
                            f_opt_h,
                        )
                        for (text, role), w in zip(row, h_widths)
                    ]
                    cells = [entry[0] for entry in cell_data]
                    max_lines = max(max(1, len(c)) for c in cells)
                    max_observed_lines = max(max_observed_lines, max_lines)
                    if max_lines == 1:
                        single_count += 1
                    content_h = max_lines * f_opt_h + (max_lines - 1) * line_gap
                    row_h = max(content_h, icon_size if any(getattr(text, 'icon', '') for text, _ in row) else 0) + 18
                    test_blocks.append((row, cells, row_h, [entry[1] for entry in cell_data]))
                if max_observed_lines == 1 or (max_observed_lines <= 2 and len(result.rows) >= 4 and single_count * 2 >= len(result.rows)):
                    use_two_col_grid = True
                    widths = h_widths
                    blocks = test_blocks
            if not use_two_col_grid:
                widths = [int(inner * r) for r in ratios]
                widths[-1] = inner - sum(widths[:-1])
                for row in result.rows:
                    cell_data = []
                    for (text, role), w in zip(row, widths):
                        comp_text = self._compact_cell_text(text, role)
                        raw_stat_lines = [s.strip() for s in str(comp_text).splitlines() if s.strip()] if (role == 'riven_stat' and not getattr(text, 'icon', '')) else []
                        if len(raw_stat_lines) >= 3 and w >= round(inner * 0.42) and all(re.match(r'^(?:正|负|正面|负面|▲|▼)', s) for s in raw_stat_lines):
                            # Pair Riven stats 2-per-line inside wide stat columns
                            paired_lines = [
                                raw_stat_lines[k] + '\t' + raw_stat_lines[k + 1] if k + 1 < len(raw_stat_lines) else raw_stat_lines[k]
                                for k in range(0, len(raw_stat_lines), 2)
                            ]
                            paired_icons = [line_icon(raw_stat_lines[k], role) for k in range(0, len(raw_stat_lines), 2)]
                            cell_data.append((paired_lines, paired_icons))
                        else:
                            cell_data.append(
                                self.wrap_cell(
                                    comp_text,
                                    role if not getattr(text, 'icon', '') else 'muted',
                                    font,
                                    max(40, w - 22 - (icon_gap if load_icon(getattr(text, 'icon', ''), icon_size) is not None else 0)),
                                    f_opt_h,
                                )
                            )
                    cells = [entry[0] for entry in cell_data]
                    max_lines = max(max(1, len(c)) for c in cells)
                    content_h = max_lines * f_opt_h + (max_lines - 1) * line_gap
                    row_h = max(content_h, icon_size if any(getattr(text, 'icon', '') for text, _ in row) else 0) + 18
                    blocks.append((row, cells, row_h, [entry[1] for entry in cell_data]))
            header_bar_h = (s_opt_h + 18) if show_col_header else 0
            if use_two_col_grid:
                row_pairs = [blocks[k:k + 2] for k in range(0, len(blocks), 2)]
                rows_total_h = sum(max(b[2] for b in pair) + 7 for pair in row_pairs)
            else:
                rows_total_h = sum(b[2] + 7 for b in blocks)
            body_height = (header_bar_h + 9 if show_col_header else 0) + rows_total_h
            footer_raw = result.footer
        else:
            footer_raw = result.footer if isinstance(result, Card) else ''
            raw_body_lines = [line for line in body.splitlines() if line.strip() or body]
            if not footer_raw and len(raw_body_lines) > 1:
                kept, extracted = [], []
                for line in raw_body_lines:
                    if re.match(r'^(数据时间：|第 \d+/\d+ 页|报价缓存)', line.strip()):
                        extracted.append(line.strip())
                    else:
                        kept.append(line)
                if kept and extracted:
                    body = '\n'.join(kept)
                    footer_raw = '\n'.join(extracted)
            body_lines, body_icons = self.wrap_cell(body, 'text', font, inner - 36, f_opt_h)
            n_body = max(1, len(body_lines))
            content_h = n_body * f_opt_h + (n_body - 1) * line_gap
            plain_box_h = content_h + 26
            body_height = plain_box_h + 6

        footer = [line for line in self.wrap(footer_raw, small, inner - 32) if line.strip()] if footer_raw else []
        footer_box_h = (len(footer) * s_opt_h + (len(footer) - 1) * small_gap + 20) if footer else 0

        chart=getattr(result,'chart',None)
        chart_h=240 if chart else 0
        divider_space = 0 if hide_title else (10 if is_sub_tile else 24)
        top_header_h = 86 + title_block_h + divider_space + chart_h
        bottom_pad = 68
        height = top_header_h + body_height + (footer_box_h + 10 if footer else 0) + bottom_pad

        if is_tile:
            canvas = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        else:
            canvas = self.background(theme, width, height)

        d = ImageDraw.Draw(canvas, 'RGBA')
        title_rgb = _rgb(theme.get('title', '#163D57'), (22, 61, 87))
        muted_rgb = _rgb(theme.get('muted', '#64748B'), (100, 116, 139))
        panel_alpha = theme['panel_opacity']

        if not is_tile:
            # Multi-layer soft ambient drop shadow and main panel
            d.rounded_rectangle(
                (panel_x + 4, 22, width - panel_x + 4, height - 10),
                radius=28,
                fill=(15, 23, 42, min(20, panel_alpha // 10)),
            )
            d.rounded_rectangle(
                (panel_x + 2, 19, width - panel_x + 2, height - 13),
                radius=28,
                fill=(15, 23, 42, min(32, panel_alpha // 7)),
            )
            d.rounded_rectangle(
                (panel_x, 16, width - panel_x, height - 16),
                radius=28,
                fill=(*_rgb(theme.get('panel_color', '#FFFFFF')), panel_alpha),
                outline=(*_mix(title_rgb, (186, 230, 253), 0.65), min(240, panel_alpha)),
                width=2,
            )
            _draw_panel_decor(d, width, height, panel_x, title_rgb, 84 + title_block_h + 12, small, badge_font, skip_art=(artwork is not None))

        # Split two-tone Brand Capsule + Category Tag
        _, b_top, _, b_bot = badge_font.getbbox('WARFRAME')
        badge_h = (b_bot - b_top) + 12
        badge_text = 'WARFRAME'
        badge_w = int(badge_font.getlength(badge_text)) + 36
        sub_text = '星际战甲助手'
        sub_w = int(badge_font.getlength(sub_text)) + 24
        cap_y = 24
        if not is_sub_tile:
            cap_box = (x, cap_y, x + badge_w + sub_w, cap_y + badge_h)
            d.rounded_rectangle(cap_box, radius=10, fill=(*_mix(title_rgb, (224, 242, 254), 0.85), 240), outline=(*title_rgb, 110), width=1)
            badge_box = (x, cap_y, x + badge_w, cap_y + badge_h)
            d.rounded_rectangle(badge_box, radius=10, fill=(*title_rgb, 248))
            # Mini golden diamond emblem inside WARFRAME pill
            d.polygon([(x + 12, cap_y + badge_h // 2), (x + 18, cap_y + badge_h // 2 - 6), (x + 24, cap_y + badge_h // 2), (x + 18, cap_y + badge_h // 2 + 6)], fill='#F59E0B')
            _draw_centered(d, (x + 16, cap_y, x + badge_w, cap_y + badge_h), badge_text, badge_font, '#FFFFFF')
            _draw_centered(d, (x + badge_w, cap_y, x + badge_w + sub_w, cap_y + badge_h), sub_text, badge_font, theme['title'])

            # Auto-inferred colorful category pill next to brand capsule
            cat_label, cat_fg, cat_bg, cat_bd = '◆ 智库视图', '#0284C7', (224, 242, 254), (14, 165, 233)
            if any(k in title for k in ('紫卡', 'WMR', '词条', '洗卡', '倾向')):
                cat_label, cat_fg, cat_bg, cat_bd = '紫卡中枢', '#7C3AED', (243, 232, 255), (139, 92, 246)
            elif any(k in title for k in ('在售', '收购', '市场', 'WM', '卖家', '赤毒', '信条')):
                cat_label, cat_fg, cat_bg, cat_bd = '❖ 交易终端', '#059669', (209, 250, 229), (16, 185, 129)
            elif any(k in title for k in ('裂隙', '裂缝', '遗物', '虚空')):
                cat_label, cat_fg, cat_bg, cat_bd = '◆ 虚空裂隙', '#D97706', (254, 243, 199), (245, 158, 11)
            elif any(k in title for k in ('警报', '突击', '入侵', '仲裁', '执刑官', '赏金')):
                cat_label, cat_fg, cat_bg, cat_bd = '★ 星图警讯', '#E11D48', (255, 228, 230), (244, 63, 94)
            cat_w = int(badge_font.getlength(cat_label)) + 24
            cat_x = x + badge_w + sub_w + 10
            cat_box = (cat_x, cap_y, cat_x + cat_w, cap_y + badge_h)
            d.rounded_rectangle(cat_box, radius=10, fill=(*cat_bg, 235), outline=(*cat_bd, 165), width=1)
            _draw_centered(d, cat_box, cat_label, badge_font, cat_fg)

            # Right-side context tag + green (PC) pill
            parts = [p.strip('（）()[]【】 ') for p in title.split('·') if p.strip('（）()[]【】 ')]
            tag_text = parts[-1].upper() if len(parts) > 1 and len(parts[-1]) <= 10 else 'TENNO'
            tag_w = int(badge_font.getlength(tag_text)) + 26
            tag_box = (x + inner - tag_w, cap_y, x + inner, cap_y + badge_h)
            d.rounded_rectangle(
                tag_box,
                radius=10,
                fill=(237, 233, 254, 235) if tag_text != 'PC' else (220, 252, 231, 235),
                outline=(139, 92, 246, 165) if tag_text != 'PC' else (16, 185, 129, 175),
                width=1,
            )
            _draw_centered(d, tag_box, tag_text, badge_font, '#6D28D9' if tag_text != 'PC' else '#047857')
            if tag_text != 'PC':
                pc_w = int(badge_font.getlength('PC')) + 24
                pc_box = (tag_box[0] - pc_w - 8, cap_y, tag_box[0] - 8, cap_y + badge_h)
                d.rounded_rectangle(pc_box, radius=10, fill=(220, 252, 231, 235), outline=(16, 185, 129, 175), width=1)
                _draw_centered(d, pc_box, 'PC', badge_font, '#047857')
                logo_right = pc_box[0]
            else:
                logo_right = tag_box[0]
            if theme.get('logo_image'):
                try:
                    with Image.open(theme['logo_image']) as source:
                        if source.width*source.height <= 4_000_000:
                            logo=ImageOps.contain(source.convert('RGBA'),(36,36))
                            canvas.paste(logo,(int(logo_right-46),cap_y),logo)
                except (OSError,ValueError,Image.DecompressionBombError):
                    pass

        if artwork is not None:
            ax, ay = x + inner - 172, 86
            d.rounded_rectangle((ax - 3, ay - 3, ax + 173, ay + 169), radius=16, fill=(241, 245, 249, 180), outline=(56, 189, 248, 165), width=1)
            d.rounded_rectangle((ax, ay, ax + 170, ay + 166), radius=14, fill=(226, 232, 240, 225), outline=(148, 163, 184, 140), width=1)
            canvas.paste(artwork, (ax + (170 - artwork.width) // 2, ay + (166 - artwork.height) // 2), artwork)
            overlay_path = getattr(result, 'artwork_overlay_path', None)
            if overlay_path:
                try:
                    with Image.open(overlay_path) as source:
                        if source.width * source.height <= 4_000_000:
                            overlay = ImageOps.contain(source.convert('RGBA'), (46, 46))
                            canvas.paste(overlay, (ax + 118, ay + 114), overlay)
                except (OSError, ValueError, Image.DecompressionBombError):
                    pass

            if not overlay_path and 'blueprint' in str(getattr(result, 'artwork', ('', ''))[1]):
                d.rounded_rectangle((ax + 86, ay + 124, ax + 164, ay + 160), radius=7, fill=(22, 61, 87, 245), outline=(125, 211, 252, 200), width=1)
                _draw_centered(d, (ax + 86, ay + 124, ax + 164, ay + 160), '蓝图', badge_font, '#FFFFFF')

        # Title with hooked multi-color bracket emblem & inline metadata pills
        y = 86
        if not hide_title:
            actual_text_h = max(1, len(title_lines)) * t_opt_h + max(0, len(title_lines) - 1) * 10
            bar_y = y + (title_block_h - actual_text_h) // 2 if artwork is not None and len(title_lines) == 1 else y
            d.rounded_rectangle((x, bar_y, x + 7, bar_y + actual_text_h), radius=3, fill=theme['title'])
            d.rounded_rectangle((x, bar_y, x + 17, bar_y + 4), radius=2, fill='#06B6D4')
            d.rounded_rectangle((x, bar_y + actual_text_h - 4, x + 17, bar_y + actual_text_h), radius=2, fill='#7C3AED')
            d.polygon([(x + 10, bar_y + actual_text_h // 2 - 5), (x + 17, bar_y + actual_text_h // 2), (x + 10, bar_y + actual_text_h // 2 + 5)], fill='#F59E0B')
            ty = bar_y - t_top
            max_title_w = inner - (204 if artwork else 24)
            for line_i, line in enumerate(title_lines):
                m_paren = re.match(r'^(.+?)\s*[（(]([^）)]+)[）)]$', line.strip()) if len(title_lines) == 1 else None
                if m_paren:
                    main_t, sub_t = m_paren.group(1).strip(), m_paren.group(2).strip()
                    mw = int(title_font.getlength(main_t))
                    sub_parts = [p.strip() for p in re.split(r'[，,·]', sub_t) if p.strip()]
                    chips_w = sum(int(header_font.getlength(sp)) + 28 for sp in sub_parts) + 8 * len(sub_parts)
                    if 24 + mw + 14 + chips_w <= max_title_w:
                        d.text((x + 24, ty), main_t, font=title_font, fill=theme['title'], anchor='la')
                        px = x + 24 + mw + 14
                        chip_pal = (('#047857', (209, 250, 229), (16, 185, 129)), ('#0284C7', (224, 242, 254), (14, 165, 233)), ('#7C3AED', (243, 232, 255), (139, 92, 246)))
                        for sp_i, sp in enumerate(sub_parts):
                            cfg, cbg, cbd = chip_pal[sp_i % len(chip_pal)]
                            cw = int(header_font.getlength(sp)) + 26
                            ch = s_opt_h + 10
                            cy_box = bar_y + (t_opt_h - ch) // 2
                            d.rounded_rectangle((px, cy_box, px + cw, cy_box + ch), radius=9, fill=(*cbg, 238), outline=(*cbd, 185), width=1)
                            _draw_centered(d, (px, cy_box, px + cw, cy_box + ch), sp, header_font, cfg)
                            px += cw + 8
                    else:
                        d.text((x + 24, ty), line, font=title_font, fill=theme['title'], anchor='la')
                else:
                    d.text((x + 24, ty), line, font=title_font, fill=theme['title'], anchor='la')
                ty += title_line_step
            if is_sub_tile:
                y += title_block_h + 10
            else:
                y += title_block_h + 12
                # Ornamental multi-segment divider
                d.rounded_rectangle((x, y - 1, x + 84, y + 2), radius=1, fill=theme['title'])
                d.polygon([(x + 94, y - 5), (x + 100, y), (x + 94, y + 5), (x + 88, y)], fill='#F59E0B')
                d.rounded_rectangle((x + 106, y - 1, x + 230, y + 1), radius=1, fill=(6, 182, 212, 210))
                d.line((x + 236, y, x + inner - 36, y), fill=(*muted_rgb, 65), width=1)
                for d_i, d_c in enumerate(((6, 182, 212, 180), (124, 58, 237, 180), (245, 158, 11, 180))):
                    dx = x + inner - 24 + d_i * 9
                    d.ellipse((dx - 2, y - 2, dx + 2, y + 2), fill=d_c)
                y += 12

        if chart:
            left,right,top,bottom=x+84,x+inner-24,y+32,y+200
            d.rounded_rectangle((x,y,x+inner,y+226),radius=14,fill=(244,248,253,238),outline=(186,230,253,185),width=1)
            d.rounded_rectangle((x,y+6,x+5,y+220),radius=2,fill=theme['wm_price'])
            values=chart.get('values',[])
            finite=[v for v in values if isinstance(v,(int,float)) and math.isfinite(v)]
            if finite:
                low,high=min(finite),max(finite)
                span=high-low or max(abs(high)*.1,1)
                for frac in (0,.5,1):
                    yy=bottom-(bottom-top)*frac
                    d.line((left,yy,right,yy),fill=(*muted_rgb,55))
                    d.text((x+12,yy-12),f'{low+span*frac:g}',font=badge_font,fill=theme['muted'])
                previous=None
                for index,value in enumerate(values):
                    if not isinstance(value,(int,float)) or not math.isfinite(value):previous=None;continue
                    point=(left+(right-left)*index/max(1,len(values)-1),bottom-(value-low)/span*(bottom-top))
                    if previous:d.line((*previous,*point),fill=theme['wm_price'],width=3)
                    d.ellipse((point[0]-5,point[1]-5,point[0]+5,point[1]+5),fill='#FFFFFF',outline=theme['wm_price'],width=2)
                    previous=point
                d.text((left,y+5),str(chart.get('title','走势'))+' / '+str(chart.get('unit','')),font=badge_font,fill=theme['title'])
            y+=chart_h

        if structured:
            if show_col_header:
                # Rich Two-Tone Column Header Bar with colored diamond nodes
                d.rounded_rectangle(
                    (x, y, x + inner, y + header_bar_h),
                    radius=11,
                    fill=(*_mix(title_rgb, (232, 241, 250), 0.84), min(238, panel_alpha)),
                    outline=(*_mix(title_rgb, (186, 230, 253), 0.72), 185),
                    width=1,
                )
                d.rounded_rectangle((x, y + 4, x + 5, y + header_bar_h - 4), radius=2, fill='#0284C7')
                d.line((x + 10, y + header_bar_h - 1, x + inner - 10, y + header_bar_h - 1), fill=(*title_rgb, 65), width=1)
                header_ty = y + (header_bar_h - s_opt_h) // 2 - s_top
                h_mid_y = y + header_bar_h // 2
                sides = (0, (inner - 16) // 2 + 16) if use_two_col_grid else (0,)
                for side_off in sides:
                    cx = x + side_off
                    if side_off > 0:
                        d.line((cx - 8, y + 5, cx - 8, y + header_bar_h - 5), fill=(*title_rgb, 55), width=1)
                    for col_i, (label, w) in enumerate(zip(result.columns, widths)):
                        if col_i > 0:
                            d.line((cx, y + 7, cx, y + header_bar_h - 7), fill=(*title_rgb, 38), width=1)
                        dot_c = _rgb(COL_ACCENTS[col_i % len(COL_ACCENTS)])
                        d.polygon([(cx + 12, h_mid_y - 5), (cx + 17, h_mid_y), (cx + 12, h_mid_y + 5), (cx + 7, h_mid_y)], fill=(*dot_c, 225))
                        d.text((cx + 23, header_ty), label, font=header_font, fill=theme['title'], anchor='la')
                        cx += w
                y += header_bar_h + 9

            def _draw_riven_stat_item(stat_str, sub_x, sub_w, ly, opt_y, role, col_idx, compact_mode=False):
                s_stripped = stat_str.strip()
                s_color = self._line_color(s_stripped, role, 0, theme)
                icon_nm = line_icon(s_stripped, role)
                ico_sz = f_opt_h - 4 if compact_mode else f_opt_h
                in_inset = self.draw_inline_icon(canvas, d, icon_nm, sub_x, opt_y + (f_opt_h - ico_sz) // 2, ico_sz)
                cur_x = sub_x + in_inset
                m_pol = re.match(r'^(正\s*·\s*|正·|正面[：:]\s*|▲\s*|负\s*·\s*|负·|负面[：:]\s*|▼\s*)(.+)$', s_stripped)
                if m_pol:
                    pref, rest = m_pol.group(1), m_pol.group(2).strip()
                    is_neg = pref.startswith(('负', '▼'))
                else:
                    rest = s_stripped
                    is_neg = (role == 'riven_negative')
                name_face = pill_font if compact_mode else bold_font
                val_face = badge_font if compact_mode else pill_font
                hex_sz = max(24, f_opt_h - 2) if compact_mode else max(28, f_opt_h + 2)
                m_sv = re.match(r'^(.+?)\s+([+-]?\d[\d.]*(?:%|m|s|米|秒)?(?:\([^)]+\))?)$', rest)
                if m_sv:
                    s_name, s_val = m_sv.group(1).strip(), m_sv.group(2).strip()
                    nw = int(name_face.getlength(s_name))
                    vw = int(val_face.getlength(s_val)) + (14 if compact_mode else 18)
                    if cur_x + hex_sz + 8 + nw + 6 + vw <= sub_x + sub_w:
                        cur_x += _draw_hex_badge(d, cur_x, opt_y + (f_opt_h - hex_sz) // 2, hex_sz, '负' if is_neg else '正', badge_font, is_neg=is_neg)
                    if cur_x + nw + 6 + vw > sub_x + sub_w + 4 and compact_mode:
                        name_face = badge_font
                        nw = int(name_face.getlength(s_name))
                    if cur_x + nw + 6 + vw <= sub_x + sub_w + 4:
                        name_ty = opt_y + (f_opt_h - (name_face.getbbox('国Ag0')[3] - name_face.getbbox('国Ag0')[1])) // 2 - name_face.getbbox('国Ag0')[1]
                        d.text((cur_x, name_ty), s_name, font=name_face, fill=s_color, anchor='la')
                        vx = cur_x + nw + 6
                        vh = f_opt_h + (4 if compact_mode else 8)
                        vy = opt_y - (2 if compact_mode else 4)
                        v_bg = (255, 228, 230, 240) if is_neg else (209, 250, 229, 240)
                        v_bd = (244, 63, 94, 185) if is_neg else (16, 185, 129, 185)
                        v_fg = '#BE123C' if is_neg else '#047857'
                        d.rounded_rectangle((vx, vy, vx + vw, vy + vh), radius=8, fill=v_bg, outline=v_bd, width=1)
                        _draw_centered(d, (vx, vy, vx + vw, vy + vh), s_val, val_face, v_fg)
                        return
                if cur_x + hex_sz + 8 + int(name_face.getlength(rest.split()[0])) <= sub_x + sub_w:
                    cur_x += _draw_hex_badge(d, cur_x, opt_y + (f_opt_h - hex_sz) // 2, hex_sz, '负' if is_neg else '正', badge_font, is_neg=is_neg)
                d.text((cur_x, ly), rest, font=name_face if col_idx == 0 else font, fill=s_color, anchor='la')

            # Structured rows (supports 1-up full width or 2-up side-by-side grid)
            row_groups = [blocks[k:k + 2] for k in range(0, len(blocks), 2)] if use_two_col_grid else [[b] for b in blocks]
            card_w = (inner - 16) // 2 if use_two_col_grid else inner
            row_counter = 0
            for group in row_groups:
                band_h = max(b[2] for b in group)
                for side_i, (row, cells, _rh, line_icons) in enumerate(group):
                    h = band_h
                    row_idx = row_counter
                    row_counter += 1
                    row_x = x + side_i * (card_w + 16)
                    row_bg = (249, 251, 254, min(236, panel_alpha)) if row_idx % 2 == 0 else (241, 246, 252, min(236, panel_alpha))
                    d.rounded_rectangle(
                        (row_x, y, row_x + card_w, y + h),
                        radius=13,
                        fill=row_bg,
                        outline=(*_rgb(theme.get('line_color', '#DDE6F0')), 215),
                        width=1,
                    )
                    first_role = row[0][1] if row else 'title'
                    if first_role not in {'title', 'text', 'muted'}:
                        stripe_color = theme.get(first_role, theme['title'])
                    else:
                        role_hit = next((theme.get(r, '') for _, r in row[1:] if r not in {'text', 'muted', 'title'} and theme.get(r)), '')
                        stripe_color = role_hit or ROW_FALLBACK_ACCENTS[row_idx % len(ROW_FALLBACK_ACCENTS)]
                    sub_accent = ROW_FALLBACK_ACCENTS[(row_idx + 2) % len(ROW_FALLBACK_ACCENTS)]
                    _draw_row_bracket(d, row_x, y, card_w, h, stripe_color, sub_accent)

                    cx = row_x
                    for col_idx, ((cell_text, role), lines, w) in enumerate(zip(row, cells, widths)):
                        if col_idx > 0:
                            d.line((cx, y + 10, cx, y + h - 10), fill=(203, 213, 225, 95), width=1)
                        icon_name = getattr(cell_text, 'icon', '')
                        icon = load_icon(icon_name, icon_size)
                        inset = icon_gap if icon is not None else 0
                        if icon is not None:
                            ix, iy = cx + 14, y + (h - icon_size) // 2
                            badge_fill, badge_outline = _icon_badge_style(icon_name)
                            d.rounded_rectangle((ix - 2, iy - 2, ix + icon_size + 2, iy + icon_size + 2), radius=9, fill=badge_fill, outline=badge_outline, width=1)
                            canvas.paste(icon, (ix + (icon_size - icon.width) // 2, iy + (icon_size - icon.height) // 2), icon)
                        n_lines = max(1, len(lines))
                        cell_opt_h = n_lines * f_opt_h + (n_lines - 1) * line_gap
                        cy = y + (h - cell_opt_h) // 2 - f_top
                        single = lines[0].strip() if len(lines) == 1 else ''
                        no_inline = not any(line_icons[col_idx])

                        # 1. Faction pill (e.g. G佬, C佬, I佬, 堕落者)
                        if len(lines) == 1 and single in FACTION_STYLES and no_inline:
                            f_hex, f_bg = FACTION_STYLES[single]
                            f_rgb = _rgb(f_hex)
                            p_face = bold_font if int(bold_font.getlength(single)) + 22 <= w - 14 - inset else (pill_font if int(pill_font.getlength(single)) + 18 <= w - 14 - inset else badge_font)
                            pill_w = min(w - 14 - inset, int(p_face.getlength(single)) + 20)
                            pill_h = f_opt_h + 8
                            pill_y = y + (h - pill_h) // 2
                            pill_box = (cx + 10 + inset, pill_y, cx + 10 + inset + pill_w, pill_y + pill_h)
                            d.rounded_rectangle(pill_box, radius=10, fill=(*f_bg, 240), outline=(*f_rgb, 180), width=1)
                            _draw_centered(d, pill_box, single, p_face, f_hex)
                            cx += w
                            continue

                        # 2. Countdown / Schedule time pill with vector clock icon (e.g. 剩9天9小时, 33分钟, 7日17时)
                        is_time_cell = (
                            len(lines) == 1
                            and no_inline
                            and role in {'muted', 'text', 'title'}
                            and bool(re.fullmatch(r'(?:剩[余]?|约\s*)?\d+\s*(?:天|小时|时|分钟|分|秒)(?:\s*\d+\s*(?:小时|时|分钟|分|秒))*|\d{1,2}日\d{1,2}时(?:\d{1,2}分)?', single))
                        )
                        if is_time_cell:
                            is_sched = '日' in single and '剩' not in single
                            t_fg = '#1D4ED8' if is_sched else '#B45309'
                            t_bg = (239, 246, 255, 240) if is_sched else (255, 251, 235, 244)
                            t_bd = (96, 165, 250, 190) if is_sched else (245, 158, 11, 200)
                            clock_r = max(7, f_opt_h // 2 - 4)
                            p_face = bold_font if int(bold_font.getlength(single)) + clock_r * 2 + 24 <= w - 12 - inset else (pill_font if int(pill_font.getlength(single)) + clock_r * 2 + 20 <= w - 12 - inset else badge_font)
                            text_w = int(p_face.getlength(single))
                            pill_w = min(w - 12 - inset, text_w + clock_r * 2 + 22)
                            pill_h = f_opt_h + 8
                            pill_y = y + (h - pill_h) // 2
                            px1 = cx + 10 + inset
                            pill_box = (px1, pill_y, px1 + pill_w, pill_y + pill_h)
                            d.rounded_rectangle(pill_box, radius=pill_h // 2, fill=t_bg, outline=t_bd, width=1)
                            _draw_clock(d, px1 + 9 + clock_r, pill_y + pill_h // 2, clock_r, t_fg)
                            _draw_centered(d, (px1 + clock_r * 2 + 10, pill_y, px1 + pill_w - 3, pill_y + pill_h), single, p_face, t_fg)
                            cx += w
                            continue

                        # 3. Standard Pill Roles (Relic tiers, Mission types, Arbitration/Riven grades, Rarities, Mode tags)
                        use_pill = (
                            len(lines) == 1
                            and single
                            and single != '—'
                            and no_inline
                            and (
                                (role in PILL_ROLES and len(single) <= (10 if role.startswith('arb_') else 6))
                                or single in {'钢铁', '九重天', '无', '设置生效'}
                            )
                        )
                        if use_pill:
                            if single == '钢铁':
                                c_hex, c_rgb = '#BE123C', (190, 18, 60)
                            elif single == '九重天':
                                c_hex, c_rgb = '#0284C7', (2, 132, 199)
                            elif role == 'rarity':
                                if single in {'金', '稀有', '传说'}:
                                    c_hex, c_rgb = '#D97706', (217, 119, 6)
                                elif single in {'银', '罕见'}:
                                    c_hex, c_rgb = '#0284C7', (2, 132, 199)
                                else:
                                    c_hex = theme.get(role, '#B45309')
                                    c_rgb = _rgb(c_hex)
                            else:
                                c_hex = theme.get(role, theme['text'])
                                c_rgb = _rgb(c_hex)
                            p_face = bold_font if int(bold_font.getlength(single)) + 22 <= w - 12 - inset else (pill_font if int(pill_font.getlength(single)) + 18 <= w - 12 - inset else badge_font)
                            pill_w = min(w - 12 - inset, int(p_face.getlength(single)) + 20)
                            pill_h = f_opt_h + 9
                            pill_y = y + (h - pill_h) // 2
                            px1 = cx + 10 + inset
                            pill_box = (px1, pill_y, px1 + pill_w, pill_y + pill_h)
                            d.rounded_rectangle(pill_box, radius=10, fill=(*c_rgb, 36), outline=(*c_rgb, 170), width=1)
                            d.rounded_rectangle((px1 + 3, pill_y + 5, px1 + 6, pill_y + pill_h - 5), radius=1, fill=(*c_rgb, 215))
                            _draw_centered(d, (px1 + 5, pill_y, px1 + pill_w, pill_y + pill_h), single, p_face, c_hex)
                            cx += w
                            continue

                        # 4. Standalone Quantity / Drop Chance Pill (preserves exact theme[role] color on text)
                        if len(lines) == 1 and single and single != '—' and no_inline and role in {'wm_quantity', 'drop_chance'} and len(single) <= 12:
                            c_hex = theme.get(role, theme['text'])
                            c_rgb = _rgb(c_hex)
                            p_face = bold_font if int(bold_font.getlength(single)) + 20 <= w - 12 - inset else (pill_font if int(pill_font.getlength(single)) + 16 <= w - 12 - inset else badge_font)
                            pill_w = min(w - 12 - inset, int(p_face.getlength(single)) + 18)
                            pill_h = f_opt_h + 8
                            pill_y = y + (h - pill_h) // 2
                            px1 = cx + 10 + inset
                            pill_box = (px1, pill_y, px1 + pill_w, pill_y + pill_h)
                            d.rounded_rectangle(pill_box, radius=9, fill=(*c_rgb, 28), outline=(*c_rgb, 140), width=1)
                            _draw_centered(d, pill_box, single, p_face, c_hex)
                            cx += w
                            continue

                        # 5. Line-by-line rich rendering (Prices, Statuses, Riven Stats, Specs, Planet+Node, General Text)
                        for i, line in enumerate(lines):
                            ly = cy + i * line_step
                            opt_y = ly + f_top
                            if '\t' in line and role == 'riven_stat':
                                # 2-column Riven stat pair on a single horizontal line
                                pair_stats = line.split('\t', 1)
                                half_sw = (w - 24) // 2
                                _draw_riven_stat_item(pair_stats[0], cx + 10, half_sw, ly, opt_y, role, col_idx, compact_mode=True)
                                _draw_riven_stat_item(pair_stats[1], cx + 14 + half_sw, half_sw, ly, opt_y, role, col_idx, compact_mode=True)
                                continue

                            fill_color = self._line_color(line, role, i, theme)
                            face = bold_font if (col_idx == 0 and i == 0 and role in {'title', 'wm_user', 'riven_stat', 'riven_negative'}) else font
                            inline_inset = self.draw_inline_icon(canvas, d, line_icons[col_idx][i], cx + 14 + inset, opt_y, f_opt_h)
                            lx = cx + 14 + inset + inline_inset
                            avail_w = w - (lx - cx) - 8
                            stripped = line.strip()

                            # 5a. Online Status Pill (游戏中 / 在线 / 离线) or Rank + Status (等级 10 · 游戏中)
                            m_rk_st = re.fullmatch(r'(等级\s*\d+)\s*·\s*(游戏中|在线|离线)', stripped)
                            if stripped in {'游戏中', '在线', '离线'} or m_rk_st:
                                cur_x = lx
                                if m_rk_st:
                                    rk_txt, st_txt = m_rk_st.group(1), m_rk_st.group(2)
                                    rkw = int(pill_font.getlength(rk_txt)) + 20
                                    rkh = f_opt_h + 8
                                    rky = opt_y - 4
                                    d.rounded_rectangle((cur_x, rky, cur_x + rkw, rky + rkh), radius=8, fill=(238, 242, 255, 238), outline=(99, 102, 241, 180), width=1)
                                    _draw_centered(d, (cur_x, rky, cur_x + rkw, rky + rkh), rk_txt, pill_font, '#4338CA')
                                    cur_x += rkw + 6
                                else:
                                    st_txt = stripped
                                if st_txt == '游戏中':
                                    s_fg = fill_color if role == 'wm_price' else theme.get('wm_quantity', '#047857')
                                    s_bg, s_bd, s_dot = (220, 252, 231, 238), (16, 185, 129, 190), '#10B981'
                                elif st_txt == '在线':
                                    s_fg = '#0369A1'
                                    s_bg, s_bd, s_dot = (224, 242, 254, 238), (14, 165, 233, 190), '#0EA5E9'
                                else:
                                    s_fg = theme['muted']
                                    s_bg, s_bd, s_dot = (241, 245, 249, 238), (148, 163, 184, 170), '#94A3B8'
                                stw = min(max(56, w - (cur_x - cx) - 6), int(pill_font.getlength(st_txt)) + 32)
                                sth = f_opt_h + 8
                                sty = opt_y - 4
                                d.rounded_rectangle((cur_x, sty, cur_x + stw, sty + sth), radius=sth // 2, fill=s_bg, outline=s_bd, width=1)
                                d.ellipse((cur_x + 9, sty + sth // 2 - 5, cur_x + 19, sty + sth // 2 + 5), fill=s_dot)
                                _draw_centered(d, (cur_x + 16, sty, cur_x + stw - 2, sty + sth), st_txt, pill_font, s_fg)
                                continue

                            # 5b. Split Two-Tone Price Capsule for wm_price (e.g. [一口价 | 500 白金] or [报价 | 18])
                            m_price = re.fullmatch(r'(\d[\d,.]*(?:\s*(?:白金|platinum))?)(?:\s*[（(]([^）)]+)[）)])?', stripped, re.I) if (role == 'wm_price' and i == 0 and '|' not in stripped) else None
                            if m_price:
                                p_val, p_sub = m_price.group(1).strip(), (m_price.group(2) or '').strip()
                                cap_lbl = '一口价' if len(lines) > 1 else '报价'
                                cap_w = int(badge_font.getlength(cap_lbl)) + 16
                                val_w = int(bold_font.getlength(p_val)) + 18
                                sub_w = (int(badge_font.getlength(p_sub)) + 16) if p_sub else 0
                                ph = f_opt_h + 10
                                py = opt_y - 5
                                p_rgb = _rgb(fill_color)
                                if cap_w + val_w + (sub_w + 6 if sub_w else 0) <= avail_w + 6:
                                    d.rounded_rectangle((lx, py, lx + cap_w + val_w, py + ph), radius=ph // 2, fill=(*p_rgb, 24), outline=(217, 119, 6, 190), width=1)
                                    d.rounded_rectangle((lx, py, lx + cap_w, py + ph), radius=ph // 2, fill=(254, 243, 199, 248), outline=(217, 119, 6, 200), width=1)
                                    _draw_centered(d, (lx, py, lx + cap_w, py + ph), cap_lbl, badge_font, '#B45309')
                                    _draw_centered(d, (lx + cap_w, py, lx + cap_w + val_w, py + ph), p_val, bold_font, fill_color)
                                    if p_sub:
                                        sx = lx + cap_w + val_w + 6
                                        d.rounded_rectangle((sx, py + 2, sx + sub_w, py + ph - 2), radius=7, fill=(238, 242, 255, 235), outline=(129, 140, 248, 170), width=1)
                                        _draw_centered(d, (sx, py + 2, sx + sub_w, py + ph - 2), p_sub, badge_font, '#4338CA')
                                elif val_w <= avail_w:
                                    d.rounded_rectangle((lx, py, lx + val_w, py + ph), radius=ph // 2, fill=(*p_rgb, 26), outline=(*p_rgb, 160), width=1)
                                    _draw_centered(d, (lx, py, lx + val_w, py + ph), p_val, bold_font, fill_color)
                                else:
                                    d.text((lx, ly), line, font=bold_font, fill=fill_color, anchor='la')
                                continue

                            # 5c. Riven Stat Lines: Hexagonal [正]/[负] badge + Stat Name + Colored Value Chip
                            m_riven_pol = re.match(r'^(正\s*·\s*|正·|正面[：:]\s*|▲\s*|负\s*·\s*|负·|负面[：:]\s*|▼\s*)(.+)$', stripped)
                            if m_riven_pol or (role in {'riven_stat', 'riven_negative'} and re.fullmatch(r'[^\d+-]+?\s+[+-]?\d[\d.]*%?', stripped)):
                                if m_riven_pol:
                                    pref, rest = m_riven_pol.group(1), m_riven_pol.group(2).strip()
                                    is_neg = pref.startswith(('负', '▼'))
                                else:
                                    rest = stripped
                                    is_neg = (role == 'riven_negative')
                                cur_x = lx
                                hex_sz = max(28, f_opt_h + 2)
                                if cur_x + hex_sz + 8 + int(font.getlength(rest.split()[0])) <= cx + w - 8:
                                    cur_x += _draw_hex_badge(d, cur_x, opt_y + (f_opt_h - hex_sz) // 2, hex_sz, '负' if is_neg else '正', badge_font, is_neg=is_neg)
                                m_sv = re.match(r'^(.+?)\s+([+-]?\d[\d.]*(?:%|m|s|米|秒)?(?:\([^)]+\))?)$', rest)
                                if m_sv:
                                    s_name, s_val = m_sv.group(1).strip(), m_sv.group(2).strip()
                                    nw = int(bold_font.getlength(s_name))
                                    vw = int(pill_font.getlength(s_val)) + 18
                                    if cur_x + nw + 6 + vw <= cx + w - 4:
                                        d.text((cur_x, ly), s_name, font=bold_font, fill=fill_color, anchor='la')
                                        vx = cur_x + nw + 6
                                        vh = f_opt_h + 8
                                        vy = opt_y - 4
                                        v_bg = (255, 228, 230, 240) if is_neg else (209, 250, 229, 240)
                                        v_bd = (244, 63, 94, 185) if is_neg else (16, 185, 129, 185)
                                        v_fg = '#BE123C' if is_neg else '#047857'
                                        if role.startswith('roll_'):
                                            v_fg = fill_color
                                            rgb = _rgb(v_fg)
                                            v_bg, v_bd = (*rgb,26), (*rgb,160)
                                        d.rounded_rectangle((vx, vy, vx + vw, vy + vh), radius=8, fill=v_bg, outline=v_bd, width=1)
                                        _draw_centered(d, (vx, vy, vx + vw, vy + vh), s_val, pill_font, v_fg)
                                        continue
                                d.text((cur_x, ly), rest, font=bold_font if col_idx == 0 else font, fill=fill_color, anchor='la')
                                continue

                            # 5d. Standalone Signed Value / Deviation Pill (e.g. +162.5%, -75.5%, +8.938%, -3.700%, +120%)
                            if not line_icons[col_idx][i] and re.fullmatch(r'[+-]\d[\d.]*%?', stripped):
                                is_neg_v = stripped.startswith('-')
                                v_fg = fill_color if role.startswith('roll_') or role in {'riven_stat', 'riven_negative', 'damage'} else ('#BE123C' if is_neg_v else '#047857')
                                v_rgb = _rgb(v_fg)
                                vw = min(avail_w, int(bold_font.getlength(stripped)) + 22)
                                vh = f_opt_h + 8
                                vy = opt_y - 4
                                d.rounded_rectangle((lx, vy, lx + vw, vy + vh), radius=8, fill=(*v_rgb, 26), outline=(*v_rgb, 150), width=1)
                                _draw_centered(d, (lx, vy, lx + vw, vy + vh), stripped, bold_font, v_fg)
                                continue

                            # 5e. Spec / Metadata Pills (single or ' · '-separated: 循环 X, 等级 X/Y, MR X, 信誉 X, 等级 X · Y 洗)
                            spec_parts = [p.strip() for p in stripped.split('·') if p.strip()]
                            is_spec_line = bool(spec_parts) and all(
                                re.fullmatch(r'(?:循环\s*\d+|等级\s*\d+(?:/\d+)?|\d+\s*洗|MR\s*\d+|段位\s*\d+|信誉\s*[\d—-]+|[23]正[01]负|\d+级)', p)
                                for p in spec_parts
                            )
                            if is_spec_line:
                                total_pw = sum(int(pill_font.getlength(p)) + 16 for p in spec_parts) + 6 * max(0, len(spec_parts) - 1)
                                s_face = pill_font if total_pw <= avail_w + 4 else badge_font
                                pad_w = 16 if s_face is pill_font else 12
                                sh = f_opt_h + 8
                                sy = opt_y - 4
                                cur_px = lx
                                for sp_tok in spec_parts:
                                    if sp_tok.startswith('循环') or sp_tok.endswith('洗'):
                                        sp_fg, sp_bg, sp_bd = '#B45309', (255, 251, 235, 240), (245, 158, 11, 185)
                                    elif sp_tok.startswith(('MR', '段位')):
                                        sp_fg, sp_bg, sp_bd = '#0E7490', (236, 254, 255, 240), (6, 182, 212, 185)
                                    elif sp_tok.startswith('信誉'):
                                        sp_fg, sp_bg, sp_bd = '#6D28D9', (245, 243, 255, 240), (139, 92, 246, 180)
                                    elif '正' in sp_tok or '负' in sp_tok:
                                        sp_fg, sp_bg, sp_bd = '#047857', (209, 250, 229, 240), (16, 185, 129, 185)
                                    else:
                                        sp_fg, sp_bg, sp_bd = '#1D4ED8', (239, 246, 255, 240), (59, 130, 246, 180)
                                    pw = min(max(36, cx + w - cur_px - 4), int(s_face.getlength(sp_tok)) + pad_w)
                                    d.rounded_rectangle((cur_px, sy, cur_px + pw, sy + sh), radius=8, fill=sp_bg, outline=sp_bd, width=1)
                                    _draw_centered(d, (cur_px, sy, cur_px + pw, sy + sh), sp_tok, s_face, sp_fg)
                                    cur_px += pw + 6
                                continue

                            # 5f. Node + Planet Line (e.g. Stephano（天王星） or Ani (Void))
                            m_np = _PLANET_PAREN_RE.fullmatch(stripped) if role in {'title', 'fissure_map'} else None
                            if m_np:
                                n_txt, pl_txt = m_np.group(1).strip(), m_np.group(2).strip()
                                n_face = face
                                nw = int(n_face.getlength(n_txt))
                                pl_face = pill_font
                                plw = int(pl_face.getlength(pl_txt)) + 16
                                if nw + 7 + plw > avail_w + 6:
                                    pl_face = badge_font
                                    plw = int(pl_face.getlength(pl_txt)) + 14
                                if nw + 6 + plw > avail_w + 8:
                                    n_face = pill_font
                                    nw = int(n_face.getlength(n_txt))
                                if nw + 6 + plw <= avail_w + 16:
                                    n_ty = opt_y + (f_opt_h - (n_face.getbbox('国Ag0')[3] - n_face.getbbox('国Ag0')[1])) // 2 - n_face.getbbox('国Ag0')[1]
                                    d.text((lx, n_ty), n_txt, font=n_face, fill=fill_color, anchor='la')
                                    plx = lx + nw + 6
                                    plh = f_opt_h + 6
                                    ply = opt_y - 3
                                    d.rounded_rectangle((plx, ply, plx + plw, ply + plh), radius=plh // 2, fill=(224, 242, 254, 240), outline=(14, 165, 233, 185), width=1)
                                    _draw_centered(d, (plx, ply, plx + plw, ply + plh), pl_txt, pl_face, '#0369A1')
                                    continue

                            d.text((lx, ly), line, font=face, fill=fill_color, anchor='la')
                        cx += w
                y += band_h + 7
        else:
            # Unified card box for non-tabular text
            d.rounded_rectangle(
                (x, y, x + inner, y + plain_box_h),
                radius=14,
                fill=(246, 249, 253, min(234, panel_alpha)),
                outline=(*_rgb(theme.get('line_color', '#DDE6F0')), 210),
                width=1,
            )
            _draw_row_bracket(d, x, y, inner, plain_box_h, theme['title'], '#06B6D4')
            cy = y + 16 - f_top
            for line, inline_name in zip(body_lines, body_icons):
                inline_inset = self.draw_inline_icon(canvas, d, inline_name, x + 18, cy + f_top, f_opt_h)
                stripped = line.strip()
                if stripped.startswith('【') and stripped.endswith('】'):
                    d.text((x + 18 + inline_inset, cy), stripped, font=bold_font, fill=theme['title'], anchor='la')
                else:
                    d.text((x + 18 + inline_inset, cy), line, font=font, fill=theme['text'], anchor='la')
                cy += line_step
            y += plain_box_h + 8

        if footer:
            y += 4
            d.rounded_rectangle(
                (x, y, x + inner, y + footer_box_h),
                radius=11,
                fill=(237, 243, 250, min(215, panel_alpha)),
                outline=(186, 230, 253, 185),
                width=1,
            )
            d.rounded_rectangle((x, y + 5, x + 4, y + footer_box_h - 5), radius=2, fill='#06B6D4')
            fy = y + 13 - s_top
            for line in footer:
                f_opt_y = fy + s_top
                m_page = re.match(r'^(第\s*\d+/\d+\s*页|页码[：:]\s*\d+/\d+)\s*(?:·\s*)?(.*)$', line.strip())
                m_tag = re.match(r'^(筛选|排序|来源|综合|注意|说明)[：:]\s*(.+)$', line.strip())
                if m_page:
                    pg_txt, rest_txt = m_page.group(1).strip(), m_page.group(2).strip()
                    pg_w = int(badge_font.getlength(pg_txt)) + 20
                    pg_h = s_opt_h + 6
                    pg_y = f_opt_y - 3
                    d.rounded_rectangle((x + 14, pg_y, x + 14 + pg_w, pg_y + pg_h), radius=7, fill=(209, 250, 229, 240), outline=(16, 185, 129, 190), width=1)
                    _draw_centered(d, (x + 14, pg_y, x + 14 + pg_w, pg_y + pg_h), pg_txt, badge_font, '#047857')
                    if rest_txt:
                        d.text((x + 14 + pg_w + 10, fy), rest_txt, font=small, fill=theme['muted'], anchor='la')
                elif m_tag:
                    tg_txt, rest_txt = m_tag.group(1).strip(), m_tag.group(2).strip()
                    tg_w = int(badge_font.getlength(tg_txt)) + 18
                    tg_h = s_opt_h + 6
                    tg_y = f_opt_y - 3
                    d.rounded_rectangle((x + 14, tg_y, x + 14 + tg_w, tg_y + tg_h), radius=6, fill=(237, 233, 254, 235), outline=(139, 92, 246, 175), width=1)
                    _draw_centered(d, (x + 14, tg_y, x + 14 + tg_w, tg_y + tg_h), tg_txt, badge_font, '#6D28D9')
                    d.text((x + 14 + tg_w + 10, fy), rest_txt, font=small, fill=theme['muted'], anchor='la')
                else:
                    d.text((x + 16, fy), line, font=small, fill=theme['muted'], anchor='la')
                fy += small_step

        path = self.output / (uuid.uuid4().hex + '.png')
        canvas.save(path)
        return path

    @staticmethod
    def background(theme,width,height):
        canvas = Image.new('RGB', (width, height), theme['background_color'])
        if theme.get('background_image'):
            try:
                with Image.open(theme['background_image']) as source:
                    if source.width * source.height > 25_000_000:
                        raise ValueError('Background exceeds 25 megapixels')
                    src = ImageOps.exif_transpose(source).convert('RGB')
                    mode=theme.get('background_fit','cover')
                    pos={'tl':(0,0),'tc':(.5,0),'tr':(1,0),'cl':(0,.5),'c':(.5,.5),'cr':(1,.5),'bl':(0,1),'bc':(.5,1),'br':(1,1)}.get(theme.get('background_pos'),(.5,.5))
                    if mode=='cover':
                        canvas.paste(ImageOps.fit(src,canvas.size,centering=pos))
                    elif mode in {'tile','width'}:
                        bg=src if mode=='tile' else src.resize((width,max(1,round(src.height*width/src.width))))
                        for by in range(0,height,bg.height):
                            for bx in range(0,width,bg.width):canvas.paste(bg,(bx,by))
                    else:
                        if mode=='custom':
                            bw=max(1,round(width*max(1,min(200,float(theme.get('background_scale',60))))/100))
                            bg=src.resize((bw,max(1,round(src.height*bw/src.width))))
                        else:bg=ImageOps.contain(src,canvas.size)
                        canvas.paste(bg,(round((width-bg.width)*pos[0]),round((height-bg.height)*pos[1])))
                    dim=max(0,min(.95,float(theme.get('background_dim',0))))
                    if dim:canvas=Image.blend(canvas,Image.new('RGB',canvas.size,'black'),dim)
            except (OSError, ValueError, Image.DecompressionBombError):
                LOG.warning('Unable to load custom background; using background color', exc_info=True)

        return canvas

    def _render_alerts_report(self, report, theme):
        """Render each alert and its rewards inside one unified, self-contained card container."""
        font_path = theme.get('font_path') or str(FONT)
        bold_path = theme.get('font_bold_path') or font_path
        body_size = round(56 * (theme['font_size'] / 26) ** 0.50)
        eff_title_size = round(70 * (theme['title_size'] / 38) ** 0.50)
        small_size = max(38, round(body_size * 0.80))
        pill_size = max(42, round(body_size * 0.90))
        badge_size = max(36, round(body_size * 0.73))
        try:
            font = ImageFont.truetype(font_path, body_size)
            bold_font = ImageFont.truetype(bold_path, body_size)
            title_font = ImageFont.truetype(bold_path, eff_title_size)
            small = ImageFont.truetype(font_path, small_size)
            header_font = ImageFont.truetype(font_path, small_size)
            pill_font = ImageFont.truetype(bold_path, pill_size)
            badge_font = ImageFont.truetype(font_path, badge_size)
        except OSError:
            font = ImageFont.truetype(str(FONT), body_size)
            bold_font = ImageFont.truetype(str(FONT), body_size)
            title_font = ImageFont.truetype(str(FONT), eff_title_size)
            small = ImageFont.truetype(str(FONT), small_size)
            header_font = ImageFont.truetype(str(FONT), small_size)
            pill_font = ImageFont.truetype(str(FONT), pill_size)
            badge_font = ImageFont.truetype(str(FONT), badge_size)
        for face, weight in (
            (font, 500),
            (bold_font, 700),
            (title_font, 750),
            (small, 480),
            (header_font, 650),
            (pill_font, 680),
            (badge_font, 660),
        ):
            try:
                axes = face.get_variation_axes()
                face.set_variation_by_axes([
                    max(a['minimum'], min(a['maximum'], weight)) if a['name'] == b'Weight' else a['default']
                    for a in axes
                ])
            except (OSError, AttributeError):
                pass

        width = self.WIDTH
        panel_x = 8
        x = self.MARGIN + panel_x
        inner = width - 2 * x
        icon_size = max(60, min(86, body_size + 6))
        r_ico_size = max(54, icon_size - 4)

        _, t_top, _, t_bot = title_font.getbbox('国Ag0')
        t_opt_h = t_bot - t_top
        _, f_top, _, f_bot = font.getbbox('国Ag0')
        f_opt_h = f_bot - f_top
        _, s_top, _, s_bot = small.getbbox('国Ag0')
        s_opt_h = s_bot - s_top
        small_gap = 6
        small_step = s_opt_h + small_gap

        pairs = [(report.blocks[i], report.blocks[i + 1]) for i in range(0, len(report.blocks), 2)]
        title = report.title or '警报任务'
        if '（' not in title and '(' not in title:
            title = f'{title}（共 {len(pairs)} 条）'
        title_lines = self.wrap(title, title_font, inner - 24)
        title_line_step = t_opt_h + 10
        title_block_h = max(1, len(title_lines)) * t_opt_h + max(0, len(title_lines) - 1) * 10

        top_band_h = max(icon_size + 28, f_opt_h + 32)
        rew_row_h = max(r_ico_size + 18, f_opt_h + 22)
        rew_lbl_txt = '★ 任务奖励'
        rew_lbl_w = int(pill_font.getlength(rew_lbl_txt)) + 34
        rx_start_rel = 18 + rew_lbl_w + 20
        avail_rew_w = inner - rx_start_rel - 18

        alert_layouts = []
        for idx, (m_block, r_block) in enumerate(pairs):
            m_row = m_block.rows[0] if m_block.rows else [('', 'fissure_map'), ('', 'fissure_type'), ('', 'faction'), ('', 'muted')]
            m_desc = re.search(r'警报[：:]\s*([^·\n]+)', m_block.footer or '')
            m_lvl = re.search(r'敌人等级[：:]\s*([^\s·\n]+)', m_block.footer or '')
            desc_str = m_desc.group(1).strip() if m_desc else ''
            level_str = m_lvl.group(1).strip() if m_lvl else ''
            if level_str == '未知':
                level_str = ''

            cap_rows = [[]]
            cur_rx = 0
            for r_row in r_block.rows:
                item_cell = r_row[0][0] if r_row else ''
                qty_cell = str(r_row[1][0]).strip() if len(r_row) > 1 else '—'
                item_str = str(item_cell).strip()
                ico_nm = getattr(item_cell, 'icon', '') or line_icon(item_str, 'item_name')
                has_ico = load_icon(ico_nm, r_ico_size) is not None
                name_w = int(bold_font.getlength(item_str))
                q_disp = f'×{qty_cell}' if (qty_cell and qty_cell != '—') else ''
                qty_w = (int(pill_font.getlength(q_disp)) + 24) if q_disp else 0
                cap_w = 16 + (r_ico_size + 12 if has_ico else 0) + name_w + (12 + qty_w if qty_w else 0) + 18
                if cap_rows[-1] and cur_rx + cap_w > avail_rew_w:
                    cap_rows.append([])
                    cur_rx = 0
                cap_rows[-1].append((item_str, ico_nm, has_ico, name_w, q_disp, qty_w, cap_w))
                cur_rx += cap_w + 26
            bot_band_h = len(cap_rows) * rew_row_h + (len(cap_rows) - 1) * 10 + 22
            card_h = top_band_h + bot_band_h
            alert_layouts.append((m_row, desc_str, level_str, cap_rows, top_band_h, bot_band_h, card_h))

        footer_parts = [b.footer for b in report.blocks if b.footer and not b.footer.startswith(('警报：', '敌人等级：'))]
        if report.footer:
            footer_parts.append(report.footer)
        footer_raw = '\n'.join(filter(None, footer_parts))
        footer = [line for line in self.wrap(footer_raw, small, inner - 32) if line.strip()] if footer_raw else []
        footer_box_h = (len(footer) * s_opt_h + (len(footer) - 1) * small_gap + 20) if footer else 0

        top_header_h = 86 + title_block_h + 24
        alerts_total_h = sum(item[6] for item in alert_layouts) + 20 * max(0, len(alert_layouts) - 1)
        bottom_pad = 68
        height = top_header_h + alerts_total_h + (footer_box_h + 14 if footer else 0) + bottom_pad

        canvas = self.background(theme, width, height)
        d = ImageDraw.Draw(canvas, 'RGBA')
        title_rgb = _rgb(theme.get('title', '#163D57'), (22, 61, 87))
        muted_rgb = _rgb(theme.get('muted', '#64748B'), (100, 116, 139))
        panel_alpha = theme['panel_opacity']

        # Main outer panel
        d.rounded_rectangle((panel_x + 4, 22, width - panel_x + 4, height - 10), radius=28, fill=(15, 23, 42, min(20, panel_alpha // 10)))
        d.rounded_rectangle((panel_x + 2, 19, width - panel_x + 2, height - 13), radius=28, fill=(15, 23, 42, min(32, panel_alpha // 7)))
        d.rounded_rectangle(
            (panel_x, 16, width - panel_x, height - 16),
            radius=28,
            fill=(*_rgb(theme.get('panel_color', '#FFFFFF')), panel_alpha),
            outline=(*_mix(title_rgb, (186, 230, 253), 0.65), min(240, panel_alpha)),
            width=2,
        )
        _draw_panel_decor(d, width, height, panel_x, title_rgb, 84 + title_block_h + 12, small, badge_font)

        # Brand capsule + category tag
        _, b_top, _, b_bot = badge_font.getbbox('WARFRAME')
        badge_h = (b_bot - b_top) + 12
        badge_w = int(badge_font.getlength('WARFRAME')) + 36
        sub_w = int(badge_font.getlength('星际战甲助手')) + 24
        cap_y = 24
        d.rounded_rectangle((x, cap_y, x + badge_w + sub_w, cap_y + badge_h), radius=10, fill=(*_mix(title_rgb, (224, 242, 254), 0.85), 240), outline=(*title_rgb, 110), width=1)
        d.rounded_rectangle((x, cap_y, x + badge_w, cap_y + badge_h), radius=10, fill=(*title_rgb, 248))
        d.polygon([(x + 12, cap_y + badge_h // 2), (x + 18, cap_y + badge_h // 2 - 6), (x + 24, cap_y + badge_h // 2), (x + 18, cap_y + badge_h // 2 + 6)], fill='#F59E0B')
        _draw_centered(d, (x + 16, cap_y, x + badge_w, cap_y + badge_h), 'WARFRAME', badge_font, '#FFFFFF')
        _draw_centered(d, (x + badge_w, cap_y, x + badge_w + sub_w, cap_y + badge_h), '星际战甲助手', badge_font, theme['title'])
        cat_label = '★ 星图警讯'
        cat_w = int(badge_font.getlength(cat_label)) + 24
        cat_x = x + badge_w + sub_w + 10
        d.rounded_rectangle((cat_x, cap_y, cat_x + cat_w, cap_y + badge_h), radius=10, fill=(255, 228, 230, 235), outline=(244, 63, 94, 165), width=1)
        _draw_centered(d, (cat_x, cap_y, cat_x + cat_w, cap_y + badge_h), cat_label, badge_font, '#E11D48')
        tag_w = int(badge_font.getlength('ALERTS')) + 26
        tag_box = (x + inner - tag_w, cap_y, x + inner, cap_y + badge_h)
        d.rounded_rectangle(tag_box, radius=10, fill=(237, 233, 254, 235), outline=(139, 92, 246, 165), width=1)
        _draw_centered(d, tag_box, 'ALERTS', badge_font, '#6D28D9')
        pc_w = int(badge_font.getlength('PC')) + 24
        pc_box = (tag_box[0] - pc_w - 8, cap_y, tag_box[0] - 8, cap_y + badge_h)
        d.rounded_rectangle(pc_box, radius=10, fill=(220, 252, 231, 235), outline=(16, 185, 129, 175), width=1)
        _draw_centered(d, pc_box, 'PC', badge_font, '#047857')

        # Main title & divider
        y = 86
        actual_text_h = max(1, len(title_lines)) * t_opt_h + max(0, len(title_lines) - 1) * 10
        d.rounded_rectangle((x, y, x + 7, y + actual_text_h), radius=3, fill=theme['title'])
        d.rounded_rectangle((x, y, x + 17, y + 4), radius=2, fill='#06B6D4')
        d.rounded_rectangle((x, y + actual_text_h - 4, x + 17, y + actual_text_h), radius=2, fill='#7C3AED')
        d.polygon([(x + 10, y + actual_text_h // 2 - 5), (x + 17, y + actual_text_h // 2), (x + 10, y + actual_text_h // 2 + 5)], fill='#F59E0B')
        ty = y - t_top
        for line in title_lines:
            m_paren = re.match(r'^(.+?)\s*[（(]([^）)]+)[）)]$', line.strip()) if len(title_lines) == 1 else None
            if m_paren:
                main_t, sub_t = m_paren.group(1).strip(), m_paren.group(2).strip()
                mw = int(title_font.getlength(main_t))
                d.text((x + 24, ty), main_t, font=title_font, fill=theme['title'], anchor='la')
                cw = int(header_font.getlength(sub_t)) + 26
                ch = s_opt_h + 10
                cy_box = y + (t_opt_h - ch) // 2
                d.rounded_rectangle((x + 24 + mw + 14, cy_box, x + 24 + mw + 14 + cw, cy_box + ch), radius=9, fill=(209, 250, 229, 238), outline=(16, 185, 129, 185), width=1)
                _draw_centered(d, (x + 24 + mw + 14, cy_box, x + 24 + mw + 14 + cw, cy_box + ch), sub_t, header_font, '#047857')
            else:
                d.text((x + 24, ty), line, font=title_font, fill=theme['title'], anchor='la')
            ty += title_line_step
        y += title_block_h + 12
        d.rounded_rectangle((x, y - 1, x + 84, y + 2), radius=1, fill=theme['title'])
        d.polygon([(x + 94, y - 5), (x + 100, y), (x + 94, y + 5), (x + 88, y)], fill='#F59E0B')
        d.rounded_rectangle((x + 106, y - 1, x + 230, y + 1), radius=1, fill=(6, 182, 212, 210))
        d.line((x + 236, y, x + inner - 36, y), fill=(*muted_rgb, 65), width=1)
        y += 12

        # Draw each unified Alert Card Container
        for idx, (m_row, desc_str, level_str, cap_rows, top_h, bot_h, card_h) in enumerate(alert_layouts):
            node_cell = m_row[0][0] if len(m_row) > 0 else ''
            mission_cell = str(m_row[1][0]).strip() if len(m_row) > 1 else ''
            faction_cell = m_row[2][0] if len(m_row) > 2 else ''
            time_cell = str(m_row[3][0]).strip() if len(m_row) > 3 else ''
            fac_str = str(faction_cell).strip()
            f_hex, f_bg = FACTION_STYLES.get(fac_str, (ROW_FALLBACK_ACCENTS[idx % len(ROW_FALLBACK_ACCENTS)], (241, 245, 249)))
            f_rgb = _rgb(f_hex)
            sub_accent = ROW_FALLBACK_ACCENTS[(idx + 2) % len(ROW_FALLBACK_ACCENTS)]

            # Soft card drop shadow + outer container
            d.rounded_rectangle((x + 2, y + 3, x + inner + 2, y + card_h + 3), radius=18, fill=(15, 23, 42, 18))
            d.rounded_rectangle(
                (x, y, x + inner, y + card_h),
                radius=18,
                fill=(248, 251, 255, min(242, panel_alpha)),
                outline=(*f_rgb, 175),
                width=2,
            )
            # Lower reward band warm tint inside the same card container
            d.rounded_rectangle(
                (x + 2, y + top_h, x + inner - 2, y + card_h - 2),
                radius=16,
                fill=(255, 250, 238, min(238, panel_alpha)),
            )
            d.rectangle((x + 2, y + top_h, x + inner - 2, y + top_h + 14), fill=(255, 250, 238, min(238, panel_alpha)))
            # Crisp internal divider between Mission and Reward bands
            d.line((x + 14, y + top_h, x + inner - 14, y + top_h), fill=(*f_rgb, 85), width=1)
            _draw_row_bracket(d, x, y, inner, card_h, f_hex, sub_accent)

            # --- TOP BAND: MISSION INFO ---
            mid_top_y = y + top_h // 2
            cur_x = x + 18

            # 1) Alert number pill [#01]
            num_txt = f'#{idx + 1:02d}'
            num_w = int(pill_font.getlength(num_txt)) + 24
            num_h = f_opt_h + 8
            num_box = (cur_x, mid_top_y - num_h // 2, cur_x + num_w, mid_top_y + num_h // 2)
            d.rounded_rectangle(num_box, radius=10, fill=(*f_rgb, 235))
            _draw_centered(d, num_box, num_txt, pill_font, '#FFFFFF')
            cur_x += num_w + 16

            # 2) Planet Icon + Node + Planet Pill
            node_ico_name = getattr(node_cell, 'icon', '')
            node_ico = load_icon(node_ico_name, icon_size)
            if node_ico is not None:
                iy = mid_top_y - icon_size // 2
                b_fill, b_out = _icon_badge_style(node_ico_name)
                d.rounded_rectangle((cur_x - 2, iy - 2, cur_x + icon_size + 2, iy + icon_size + 2), radius=9, fill=b_fill, outline=b_out, width=1)
                canvas.paste(node_ico, (cur_x + (icon_size - node_ico.width) // 2, iy + (icon_size - node_ico.height) // 2), node_ico)
                cur_x += icon_size + 14
            node_str = str(node_cell).strip()
            m_np = _PLANET_PAREN_RE.fullmatch(node_str)
            if m_np:
                n_txt, pl_txt = m_np.group(1).strip(), m_np.group(2).strip()
                nw = int(bold_font.getlength(n_txt))
                d.text((cur_x, mid_top_y - f_opt_h // 2 - f_top), n_txt, font=bold_font, fill=theme['fissure_map'], anchor='la')
                cur_x += nw + 8
                plw = int(pill_font.getlength(pl_txt)) + 20
                plh = f_opt_h + 6
                pl_box = (cur_x, mid_top_y - plh // 2, cur_x + plw, mid_top_y + plh // 2)
                d.rounded_rectangle(pl_box, radius=plh // 2, fill=(224, 242, 254, 242), outline=(14, 165, 233, 190), width=1)
                _draw_centered(d, pl_box, pl_txt, pill_font, '#0369A1')
                cur_x += plw + 20
            else:
                nw = int(bold_font.getlength(node_str))
                d.text((cur_x, mid_top_y - f_opt_h // 2 - f_top), node_str, font=bold_font, fill=theme['fissure_map'], anchor='la')
                cur_x += nw + 20

            # 3) Faction Icon + Faction Pill + Mission Type Pill + Enemy Level Pill
            cur_x = max(cur_x, x + 650)
            fac_ico_name = getattr(faction_cell, 'icon', '')
            fac_ico = load_icon(fac_ico_name, icon_size - 4)
            if fac_ico is not None:
                f_sz = icon_size - 4
                iy = mid_top_y - f_sz // 2
                b_fill, b_out = _icon_badge_style(fac_ico_name)
                d.rounded_rectangle((cur_x - 2, iy - 2, cur_x + f_sz + 2, iy + f_sz + 2), radius=9, fill=b_fill, outline=b_out, width=1)
                canvas.paste(fac_ico, (cur_x + (f_sz - fac_ico.width) // 2, iy + (f_sz - fac_ico.height) // 2), fac_ico)
                cur_x += f_sz + 10
            if fac_str:
                fw = int(bold_font.getlength(fac_str)) + 22
                fh = f_opt_h + 8
                f_box = (cur_x, mid_top_y - fh // 2, cur_x + fw, mid_top_y + fh // 2)
                d.rounded_rectangle(f_box, radius=10, fill=(*f_bg, 242), outline=(*f_rgb, 185), width=1)
                _draw_centered(d, f_box, fac_str, bold_font, f_hex)
                cur_x += fw + 14

            if mission_cell:
                m_hex = theme.get('fissure_type', '#C2410C')
                m_rgb = _rgb(m_hex)
                mw = int(bold_font.getlength(mission_cell)) + 24
                mh = f_opt_h + 8
                m_box = (cur_x, mid_top_y - mh // 2, cur_x + mw, mid_top_y + mh // 2)
                d.rounded_rectangle(m_box, radius=10, fill=(*m_rgb, 34), outline=(*m_rgb, 175), width=1)
                d.rounded_rectangle((cur_x + 3, mid_top_y - mh // 2 + 5, cur_x + 6, mid_top_y + mh // 2 - 5), radius=1, fill=(*m_rgb, 215))
                _draw_centered(d, (cur_x + 5, mid_top_y - mh // 2, cur_x + mw, mid_top_y + mh // 2), mission_cell, bold_font, m_hex)
                cur_x += mw + 14

            if level_str:
                lv_disp = f'等级 {level_str}' if not level_str.startswith('等级') else level_str
                lw = int(pill_font.getlength(lv_disp)) + 22
                lh = f_opt_h + 6
                l_box = (cur_x, mid_top_y - lh // 2, cur_x + lw, mid_top_y + lh // 2)
                d.rounded_rectangle(l_box, radius=9, fill=(238, 242, 255, 240), outline=(99, 102, 241, 180), width=1)
                _draw_centered(d, l_box, lv_disp, pill_font, '#4338CA')
                cur_x += lw + 12

            # 4) Right-aligned Countdown Pill
            if time_cell:
                clock_r = max(8, f_opt_h // 2 - 3)
                tw = int(bold_font.getlength(time_cell)) + clock_r * 2 + 28
                th = f_opt_h + 8
                tx1 = x + inner - 18 - tw
                ty1 = mid_top_y - th // 2
                d.rounded_rectangle((tx1, ty1, tx1 + tw, ty1 + th), radius=th // 2, fill=(255, 251, 235, 246), outline=(245, 158, 11, 205), width=1)
                _draw_clock(d, tx1 + 11 + clock_r, mid_top_y, clock_r, '#B45309')
                _draw_centered(d, (tx1 + clock_r * 2 + 12, ty1, tx1 + tw - 4, ty1 + th), time_cell, bold_font, '#B45309')

            # --- BOTTOM BAND: TASK REWARDS ---
            rew_y0 = y + top_h
            lbl_h = f_opt_h + 10
            lbl_y = rew_y0 + (bot_h - lbl_h) // 2
            lbl_box = (x + 18, lbl_y, x + 18 + rew_lbl_w, lbl_y + lbl_h)
            d.rounded_rectangle(lbl_box, radius=11, fill=(254, 243, 199, 248), outline=(217, 119, 6, 215), width=2)
            _draw_centered(d, lbl_box, rew_lbl_txt, pill_font, '#B45309')

            ry = rew_y0 + 11
            for c_row in cap_rows:
                rx = x + rx_start_rel
                for c_i, (item_str, ico_nm, has_ico, name_w, q_disp, qty_w, cap_w) in enumerate(c_row):
                    is_cred = ico_nm == 'credits' or '星币' in item_str or '现金' in item_str
                    c_bd = (14, 165, 233, 195) if is_cred else (245, 158, 11, 205)
                    c_bar = '#0284C7' if is_cred else '#D97706'
                    d.rounded_rectangle((rx, ry, rx + cap_w, ry + rew_row_h), radius=14, fill=(255, 255, 255, 248), outline=c_bd, width=1)
                    d.rounded_rectangle((rx + 2, ry + 6, rx + 6, ry + rew_row_h - 6), radius=2, fill=c_bar)
                    ix = rx + 14
                    mid_ry = ry + rew_row_h // 2
                    if has_ico:
                        r_ico = load_icon(ico_nm, r_ico_size)
                        if r_ico is not None:
                            iy = mid_ry - r_ico_size // 2
                            b_fill, b_out = _icon_badge_style(ico_nm)
                            d.rounded_rectangle((ix - 2, iy - 2, ix + r_ico_size + 2, iy + r_ico_size + 2), radius=8, fill=b_fill, outline=b_out, width=1)
                            canvas.paste(r_ico, (ix + (r_ico_size - r_ico.width) // 2, iy + (r_ico_size - r_ico.height) // 2), r_ico)
                        ix += r_ico_size + 12
                    d.text((ix, mid_ry - f_opt_h // 2 - f_top), item_str, font=bold_font, fill=theme['item_name'], anchor='la')
                    ix += name_w + 12
                    if q_disp:
                        qh = f_opt_h + 6
                        qy = mid_ry - qh // 2
                        d.rounded_rectangle((ix, qy, ix + qty_w, qy + qh), radius=9, fill=(209, 250, 229, 245), outline=(16, 185, 129, 200), width=1)
                        _draw_centered(d, (ix, qy, ix + qty_w, qy + qh), q_disp, pill_font, theme.get('wm_quantity', '#047857'))
                    rx += cap_w + 22
                ry += rew_row_h + 10

            y += card_h + 20

        if footer:
            y -= 6
            d.rounded_rectangle((x, y, x + inner, y + footer_box_h), radius=11, fill=(237, 243, 250, min(215, panel_alpha)), outline=(186, 230, 253, 185), width=1)
            d.rounded_rectangle((x, y + 5, x + 4, y + footer_box_h - 5), radius=2, fill='#06B6D4')
            fy = y + 13 - s_top
            for line in footer:
                d.text((x + 16, fy), line, font=small, fill=theme['muted'], anchor='la')
                fy += small_step

        path = self.output / (uuid.uuid4().hex + '.png')
        canvas.save(path)
        return path

    def render_report(self, report, theme):
        """Render semantic sections inside one continuous panel and shared header."""
        if (
            len(report.blocks) >= 2
            and len(report.blocks) % 2 == 0
            and all(
                tuple(report.blocks[i].columns) == ('节点', '任务类型', '派系', '剩余')
                and tuple(report.blocks[i + 1].columns) == ('奖励物品', '数量')
                for i in range(0, len(report.blocks), 2)
            )
        ):
            return self._render_alerts_report(report, theme)
        tiles=[];brand=None;panel_x=8;x=self.MARGIN+panel_x;first_header_h=152
        seen_cols=set()
        for index,block in enumerate(report.blocks):
            first_title = report.title
            if index == 0 and block.title.startswith('挂单 '):
                first_title += '｜' + block.title
            part=Card('',title=(first_title if index==0 else block.title),columns=block.columns,
                      rows=block.rows,footer=block.footer,chart=block.chart)
            if index==0:
                part.artwork=report.artwork
                part.artwork_path=report.artwork_path
                part.artwork_overlay_path=report.artwork_overlay_path
            if index==len(report.blocks)-1:part.footer+='\n'+report.footer
            is_reward_sub = bool(index and block.title == '任务奖励' and tuple(block.columns) == ('奖励物品', '数量'))
            same_alert_sub = bool(index and block.title == report.blocks[0].title and tuple(block.columns) == tuple(report.blocks[0].columns))
            hide_title = is_reward_sub or same_alert_sub or bool(index and not block.title)
            hide_col = is_reward_sub or bool(index and tuple(block.columns) in seen_cols)
            seen_cols.add(tuple(block.columns))
            local=dict(theme,_report_tile=True,_sub_tile=bool(index),_hide_title=hide_title,_hide_col_header=hide_col)
            if index:local['title_size']=max(24,min(theme['title_size'],theme['font_size']+3))
            path=self.render(part,local)
            with Image.open(path) as source:
                rgba=source.convert('RGBA')
                if brand is None:
                    brand=rgba.crop((x,20,self.WIDTH-x,82)).copy()
                tiles.append(rgba.crop((x,84,self.WIDTH-x,rgba.height-68)).copy())
            path.unlink(missing_ok=True)
        gap=6
        height=84+sum(t.height for t in tiles)+gap*max(0,len(tiles)-1)+68
        canvas=self.background(theme,self.WIDTH,height)
        d=ImageDraw.Draw(canvas,'RGBA');alpha=theme['panel_opacity'];title=_rgb(theme['title'])
        d.rounded_rectangle((panel_x+4,22,self.WIDTH-panel_x+4,height-10),radius=28,fill=(15,23,42,min(20,alpha//10)))
        d.rounded_rectangle((panel_x+2,19,self.WIDTH-panel_x+2,height-13),radius=28,fill=(15,23,42,min(32,alpha//7)))
        d.rounded_rectangle((panel_x,16,self.WIDTH-panel_x,height-16),radius=28,fill=(*_rgb(theme['panel_color']),alpha),outline=(*_mix(title,(186,230,253),.65),min(240,alpha)),width=2)
        font_path = theme.get('font_path') or str(FONT)
        body_sz = round(56 * (theme['font_size'] / 26) ** 0.50)
        small_sz = max(38, round(body_sz * 0.80))
        badge_sz = max(36, round(body_sz * 0.73))
        try:
            small_f = ImageFont.truetype(font_path, small_sz)
            badge_f = ImageFont.truetype(font_path, badge_sz)
        except OSError:
            small_f = ImageFont.truetype(str(FONT), small_sz)
            badge_f = ImageFont.truetype(str(FONT), badge_sz)
        for face, weight in ((small_f, 480), (badge_f, 660)):
            try:
                axes = face.get_variation_axes()
                face.set_variation_by_axes([
                    max(a['minimum'], min(a['maximum'], weight)) if a['name'] == b'Weight' else a['default']
                    for a in axes
                ])
            except (OSError, AttributeError):
                pass
        _draw_panel_decor(d, self.WIDTH, height, panel_x, title, first_header_h, small_f, badge_f, skip_art=bool(getattr(report, 'artwork_path', None)))
        if brand is not None:canvas.paste(brand,(x,20),brand)
        y=84
        for tile in tiles:canvas.paste(tile,(x,y),tile);y+=tile.height+gap
        path=self.output/(uuid.uuid4().hex+'.png');canvas.save(path);return path
