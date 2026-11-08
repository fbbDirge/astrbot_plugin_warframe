"""Shared game part artwork; whole-item blueprints retain the item's own thumbnail."""
import json,re
from pathlib import Path
from functools import lru_cache
from .bundled_assets import image_path

ROOT=Path(__file__).parent
PARTS={
 'neuroptics':('GenericWarframeHelmet.png','GenericWarframePrimeHelmet.png',('头部神经光元','头部','Neuroptics')),
 'chassis':('GenericWarframeChassis.png','GenericWarframePrimeChassis.png',('机体','Chassis')),
 'systems':('GenericWarframeSystem.png','GenericWarframePrimeSystem.png',('系统','Systems')),
 'barrel':('GenericGunBarrel.png','GenericGunPrimeBarrel.png',('枪管','Barrel','Barrels')),
 'receiver':('GenericGunReceiver.png','GenericGunPrimeReceiver.png',('枪机','Receiver','Receivers')),
 'stock':('GenericGunStock.png','GenericGunPrimeStock.png',('枪托','Stock')),
 'blade':('GenericWeaponBlade.png','GenericWeaponPrimeBlade.png',('刀刃','Blade','Blades')),
 'handle':('GenericWeaponHilt.png','GenericWeaponPrimeHilt.png',('握柄','刀柄','Handle','Hilt')),
 'link':('GenericComponentPlug.png','GenericComponentPrimePlug.png',('连接器','Link')),
 'grip':('GenericComponentLatch.png','GenericComponentPrimeLatch.png',('握把','Grip')),
 'guard':('GenericWeaponGuard.png','GenericWeaponPrimeGuard.png',('护手','Guard')),
 'string':('GenericGunStock.png','GenericGunPrimeStock.png',('弓弦','String')),
 'upper_limb':('GenericWeaponBlade.png','GenericWeaponPrimeBlade.png',('上弓臂','Upper Limb')),
 'lower_limb':('GenericWeaponBlade.png','GenericWeaponPrimeBlade.png',('下弓臂','Lower Limb')),
 'pouch':('GenericComponentLatch.png','GenericComponentPrimeLatch.png',('镖袋','Pouch')),
 'head':('GenericWeaponBlade.png','GenericWeaponPrimeBlade.png',('锤头','Head')),
 'disc':('GenericComponentPlug.png','GenericWeaponPrimeBlade.png',('圆盘','Disc')),
 'ornament':('GenericComponentPlug.png','GenericComponentPrimePlug.png',('饰物','Ornament')),
 'harness':('GenericArchwingHarness.png','GenericArchwingHarnessPrime.png',('外甲','Harness')),
 'wings':('GenericArchwingWings.png','GenericArchwingWingsPrime.png',('机翼','Wings')),
}

@lru_cache(maxsize=1)
def files():
    return json.loads((ROOT/'assets/components/manifest.json').read_text())['files']

def component_path(key):
    filename=files().get(key)
    return image_path(ROOT/'assets/components'/filename) if filename else None

def component_icon(value):
    from .localization import strip_item_tags
    text=strip_item_tags(value)
    # Component blueprint labels still display their shared component art.
    base=re.sub(r'\s*(?:蓝图|Blueprint)$','',text,flags=re.I).strip()
    prime=bool(re.search(r'prime|圣装',base,re.I))
    for key,(_,__,aliases) in PARTS.items():
        for alias in sorted(aliases,key=len,reverse=True):
            if re.search(r'(?i)'+(r'\s+' if alias.isascii() else '')+re.escape(alias)+r'$',base) and len(base)>len(alias):
                name=key+('_prime' if prime else '')
                if component_path(name):return 'component:'+name
    if base!=text:
        from .weapon_art import exact_weapon
        from .equipment_art import exact_equipment
        key=exact_weapon(base)
        if key:return 'blueprint:weapon:'+key
        key=exact_equipment(base)
        if key:return 'blueprint:equipment:'+key
        if base.casefold() in {'forma','福马'}:return 'blueprint:forma'
    return ''
