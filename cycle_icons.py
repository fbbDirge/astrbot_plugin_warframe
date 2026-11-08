"""Region artwork for cycle names, independent of enemy-faction icons."""
import re
CYCLE_ICONS={
    '夜灵平野':'cycle_cetus','夜灵平原':'cycle_cetus','希图斯':'cycle_cetus','cetus':'cycle_cetus','plains of eidolon':'cycle_cetus',
    '奥布山谷':'cycle_vallis','orb vallis':'cycle_vallis','vallis':'cycle_vallis',
    '魔胎之境':'cycle_cambion','cambion drift':'cycle_cambion','cambion':'cycle_cambion',
    '地球':'cycle_earth','earth':'cycle_earth',
    '双衍王境':'cycle_duviri','duviri':'cycle_duviri',
    '扎里曼号':'cycle_zariman','扎里曼':'cycle_zariman','zariman':'cycle_zariman','zariman ten zero':'cycle_zariman',
}

def cycle_icon(text):
    # Optional state in parentheses is used by the nearest-transition summary.
    name=re.split(r'[（(]',str(text).strip(),maxsplit=1)[0].strip().casefold()
    return CYCLE_ICONS.get(name,'')
