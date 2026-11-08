"""Explicit faction identities; never infer the enemy from the planet."""
from .cards import IconText

FACTIONS = {
    'grineer': ('grineer', 'G佬'), '克隆尼': ('grineer', 'G佬'),
    'corpus': ('corpus', 'C佬'), '科普斯': ('corpus', 'C佬'),
    'infested': ('infested', 'I佬'), '感染者': ('infested', 'I佬'),
    'sentient': ('sentient', 'S佬'), 'sentients': ('sentient', 'S佬'), 'sentient无人机': ('sentient', 'S佬'),
    's佬': ('sentient', 'S佬'), 'g佬': ('grineer', 'G佬'), 'c佬': ('corpus', 'C佬'), 'i佬': ('infested', 'I佬'),
    'orokin': ('orokin', '堕落者'), 'corrupted': ('orokin', '堕落者'), '堕落者': ('orokin', '堕落者'),
}
# API codes, localized labels and the names used by world-state providers.
for icon, label, aliases in (
    ('grineer', 'G佬', ('fc_grineer', 'grineer帝国')),
    ('corpus', 'C佬', ('fc_corpus',)),
    ('infested', 'I佬', ('fc_infestation', 'fc_infested', 'infestation', '感染体')),
    ('sentient', 'S佬', ('fc_sentient', 'sentient无人机', 'sentient无人机群')),
    ('orokin', '堕落者', ('fc_orokin', 'fc_corrupted', '奥罗金')),
    ('murmur', '低语者', ('murmur', 'the murmur', 'fc_murmur', 'fc_mitw', '低语者', '喃喃者')),
    ('narmer', '合一众', ('narmer', 'fc_narmer', '合一众')),
    ('duviri', '双衍王境', ('duviri', 'fc_duviri', '双衍王境')),
    ('scaldra', '炽蛇军', ('scaldra', 'fc_scaldra', '炽蛇军')),
    ('techrot', '科腐者', ('techrot', 'fc_techrot', '科腐者')),
):
    for alias in aliases:
        FACTIONS[alias] = (icon, label)
RELICS = {'Lith': 'lith', 'Meso': 'meso', 'Neo': 'neo', 'Axi': 'axi', 'Requiem': 'requiem',
          '古纪': 'lith', '前纪': 'meso', '中纪': 'neo', '后纪': 'axi', '安魂': 'requiem'}


def mission_cell(text, mission, fallback=None):
    faction = mission.get('enemy') or mission.get('faction') or mission.get('faction_code') or fallback
    if not faction:
        return IconText(text)
    icon, label = FACTIONS.get(str(faction).casefold(), ('', str(faction)))
    return IconText(f'{text}\n{label}', icon)


def relic_cell(text, tier):
    return IconText(text, RELICS.get(str(tier), ''))
