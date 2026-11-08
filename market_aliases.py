"""Explicit WM frame nicknames, never arbitrary substring/fuzzy corrections.

Community reference: https://news.17173.com/z/xjzj/content/04042023/114537015.shtml
The two spelling corrections below were explicitly requested by the user.
"""
import re

FRAME_NAMES = {
    'ash': ('轮椅',),
    'atlas': ('土甲', '一拳超人'),
    'baruuk': ('武僧', '和尚'),
    'banshee': ('音妈',),
    'chroma': ('龙甲',),
    'equinox': ('阴阳',),
    'ember': ('火鸡',),
    'frost': ('冰男',),
    'gara': ('玻璃甲',),
    'garuda': ('血甲', '血妈'),
    'gauss': ('高斯', '快男', '跑男'),
    'grendel': ('肥宅', '胖子'),
    'harrow': ('主教',),
    'hydroid': ('水男',),
    'hildryn': ('母牛', '牛妹'),
    'inaros': ('沙甲',),
    'ivara': ('弓妹',),
    'khora': ('猫甲', '蜘蛛甲'),
    'limbo': ('小明', '李明博'),
    'loki': ('洛基',),
    'mag': ('磁妹',),
    'mirage': ('小丑',),
    'mesa': ('女枪',),
    'nekros': ('摸尸',),
    'nezha': ('哪吒',),
    'nidus': ('感染甲', '蛆甲', '蛆爹'),
    'nova': ('诺娃',),
    'oberon': ('奶爸',),
    'octavia': ('音乐甲', 'dj'),
    'rhino': ('犀牛', '牛甲'),
    'revenant': ('夜灵甲',),
    'saryn': ('毒妈',),
    'trinity': ('奶妈',),
    'titania': ('蝶甲', '蝶妹'),
    'valkyr': ('瓦喵', '女武神'),
    'vauban': ('工程甲',),
    'volt': ('电男', '伏特'),
    'wukong': ('猴子', '悟空'),
    'wisp': ('幽浮', '鬼妹', '花甲'),
    'zephyr': ('鸟姐',),
}
ALIASES = {alias: frame for frame, aliases in FRAME_NAMES.items()
           for alias in (frame, *aliases)}
PARTS = {
    '': 'set', '一套': 'set', '整套': 'set', '套装': 'set', '全套': 'set', '套': 'set', 'set': 'set',
    '头': 'neuroptics', '头部': 'neuroptics', '头部神经光元': 'neuroptics', '神经光元': 'neuroptics', 'neuroptics': 'neuroptics',
    '机体': 'chassis', 'chassis': 'chassis',
    '系统': 'systems', 'systems': 'systems',
    '蓝图': 'blueprint', '总图': 'blueprint', 'blueprint': 'blueprint',
}


def market_alias_slug(query):
    """Return an exact catalogue target, or None for an unrecognized query."""
    text = re.sub(r'[\s_·・\-]+', '', query).casefold()
    for typo, canonical in (('measprime', 'mesaprime'), ('ahsprim', 'ashprime')):
        if text.startswith(typo):
            text = canonical + text[len(typo):]
            break
    for alias in sorted(ALIASES, key=len, reverse=True):
        if not text.startswith(alias):
            continue
        suffix = text[len(alias):]
        if suffix.startswith('prime'):
            suffix = suffix[5:]
        elif suffix.startswith('p'):
            suffix = suffix[1:]
        # Components are traded as blueprints in the current WM catalogue.
        for ending in ('蓝图', 'blueprint'):
            if suffix.endswith(ending) and suffix[:-len(ending)] in PARTS and PARTS[suffix[:-len(ending)]] in {'chassis', 'systems', 'neuroptics'}:
                suffix = suffix[:-len(ending)]
                break
        if suffix in PARTS:
            part = PARTS[suffix]
            if part in {'chassis', 'systems', 'neuroptics'}:
                part += '_blueprint'
            return f'{ALIASES[alias]}_prime_{part}'
    return None
