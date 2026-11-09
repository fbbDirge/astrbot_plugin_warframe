"""Offline display-only localization; never translate API IDs, URLs or user names."""
import json
import re
from functools import lru_cache
from pathlib import Path

# Stable simplified-Chinese labels override older upstream traditional strings.
OVERRIDES = {
    'Forma': '福马', 'Forma Blueprint': '福马蓝图', 'Kuva': '赤毒',
    'Moonflesh': '月华脯',
    'Hive': '清巢', 'Hive Sabotage': '清巢', 'Defense': '防御',
    'Mobile Defense': '移动防御', 'Capture': '捕获', 'Exterminate': '歼灭',
    'Extermination': '歼灭', 'Survival': '生存', 'Rescue': '救援',
    'Interception': '拦截', 'Sabotage': '破坏', 'Spy': '间谍',
    'Disruption': '中断', 'Excavation': '挖掘', 'Assassination': '刺杀',
    'Defection': '叛逃', 'Infested Salvage': 'Infested 回收',
    'Free Roam': '自由探索', 'Void Flood': '虚空洪流',
    'Void Cascade': '虚空覆涌', 'Void Armageddon': '虚空大决战',
    'Alchemy': '炼金', 'Mirror Defense': '镜像防御',
    'Earth': '地球', 'Venus': '金星', 'Mercury': '水星', 'Mars': '火星',
    'Phobos': '火卫一', 'Deimos': '火卫二', 'Ceres': '谷神星', 'Jupiter': '木星',
    'Europa': '欧罗巴', 'Saturn': '土星', 'Uranus': '天王星', 'Neptune': '海王星',
    'Pluto': '冥王星', 'Eris': '阋神星', 'Sedna': '赛德娜', 'Void': '虚空',
    'Lua': '月球', 'Kuva Fortress': '赤毒要塞', 'Zariman': '扎利曼',
}
DISPLAY_FIELDS = {'node', 'victimNode', 'location', 'missionType', 'type', 'typeKey',
                  'item', 'items', 'name', 'boss', 'modifier', 'enemy', 'faction',
                  'title', 'desc', 'description', 'choices', 'character'}


@lru_cache(maxsize=1)
def dictionary():
    path = Path(__file__).parent / 'assets/localization/world_zh.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    data.update(OVERRIDES)
    return {k.casefold(): v for k, v in data.items()}


def strip_item_tags(value):
    """Remove known export category prefixes, not arbitrary angle-bracket text."""
    return re.sub(r'^\s*(?:<ARCHWING>\s*)+', '', str(value), flags=re.I).strip()


def display_place_names(value):
    return str(value).replace('扎里曼号','扎利曼').replace('扎利曼号','扎利曼').replace('扎里曼','扎利曼')


def translate(value):
    text = strip_item_tags(value)
    # Split node/planet before dictionary lookup; official node names often stay Latin.
    match = re.fullmatch(r'(.+?)\s*[（(]([^()（）]+)[）)]', text)
    if match:
        node, planet = match.groups()
        return display_place_names(f'{dictionary().get(node.strip().casefold(), node.strip())}（{translate(planet)}）')
    return display_place_names(dictionary().get(text.casefold(), text).replace('鬩神星', '阋神星'))


def localize_world(value, field=''):
    if isinstance(value, dict):
        return {key: localize_world(item, key) for key, item in value.items()}
    if isinstance(value, list):
        return [localize_world(item, field) for item in value]
    if isinstance(value, str) and field in DISPLAY_FIELDS:
        return translate(value)
    return value
