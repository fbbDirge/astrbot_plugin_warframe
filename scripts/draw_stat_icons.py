"""Rebuild original semantic stat glyphs; requires Pillow, no remote assets."""
from pathlib import Path
import importlib.util,sys,math
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('wf_plugin',ROOT/'__init__.py',submodule_search_locations=[str(ROOT)])
pkg=importlib.util.module_from_spec(spec);sys.modules['wf_plugin']=pkg;spec.loader.exec_module(pkg)
from wf_plugin.stat_icons import STAT_LABELS,STAT_ICONS
font=ImageFont.truetype(str(ROOT/'assets/fonts/NotoSansSC.ttf'),52)
try:font.set_variation_by_axes([700])
except (AttributeError,OSError):pass
for key,label in STAT_LABELS.items():
    im=Image.new('RGBA',(128,128));d=ImageDraw.Draw(im);white='#FFFFFF'
    if key=='multishot':
        for x,y in [(25,44),(64,20),(103,44)]:
            d.polygon([(x-11,y+16),(x,y),(x+11,y+16),(x+11,y+57),(x-11,y+57)],fill=white)
            d.line((x,y+65,x,y+78),fill=white,width=5)
    elif key=='crit_chance':
        d.ellipse((25,25,103,103),outline=white,width=7);d.ellipse((52,52,76,76),fill=white)
        for line in [(64,8,64,35),(64,93,64,120),(8,64,35,64),(93,64,120,64)]:d.line(line,fill=white,width=6)
    elif key=='crit_damage':
        points=[(64+math.cos(i*math.pi/8)* (55 if i%2==0 else 29),64+math.sin(i*math.pi/8)*(55 if i%2==0 else 29)) for i in range(16)]
        d.polygon(points,fill=white);d.line((64,37,64,69),fill='#233141',width=9);d.ellipse((59,80,69,90),fill='#233141')
    else:
        def line(points,width=7):d.line(points,fill=white,width=width,joint='curve')
        def circle(box):d.ellipse(box,outline=white,width=6)
        def arrow(x,y):line([(x-12,y+12),(x,y),(x+12,y+12)])
        def clock():
            circle((30,20,106,96));line([(68,33),(68,58),(85,68)])
        def sword():
            d.polygon([(25,89),(76,24),(96,15),(92,40),(40,99)],outline=white,width=5)
            line([(17,78),(52,109)]);line([(32,94),(16,114)])
        def target():
            circle((22,22,106,106));circle((46,46,82,82));line([(64,8),(64,34)]);line([(64,94),(64,120)])
        def bullet(x,y):
            d.polygon([(x,y),(x-9,y+16),(x-9,y+58),(x+9,y+58),(x+9,y+16)],outline=white,width=5)
        if key in {'melee_damage','attack_speed','finisher_damage'}:
            sword()
            if key=='attack_speed':line([(89,69),(108,84),(89,99)]);line([(70,69),(89,84),(70,99)])
            if key=='finisher_damage':line([(75,78),(112,115)]);line([(112,78),(75,115)])
        elif key in {'fire_rate','ammo_max','magazine_capacity','ammo_efficiency','reload_holstered'}:
            bullet(35,24);bullet(64,24);bullet(93,24)
            if key=='fire_rate':line([(20,104),(96,104),(83,92)])
            elif key=='magazine_capacity':line([(16,18),(16,102),(112,102),(112,18)])
            elif key=='ammo_max':line([(20,103),(108,103)]);line([(20,115),(108,115)])
            elif key=='ammo_efficiency':circle((83,83,118,118));line([(90,100),(98,108),(113,92)],5)
            else:arrow(102,90);line([(102,90),(102,120)])
        elif key in {'status_duration','combo_duration','melee_heavy_attack_charge'}:
            clock()
            if key=='combo_duration':circle((12,83,49,116));circle((41,83,78,116))
            elif key=='melee_heavy_attack_charge':d.polygon([(18,70),(10,100),(25,100),(17,122),(45,91),(29,91)],fill=white)
        elif key in {'status_chance','status_damage'}:
            d.polygon([(64,12),(27,66),(20,88),(31,108),(64,118),(97,108),(108,88),(101,66)],outline=white,width=6)
            if key=='status_chance':circle((53,65,75,87))
            else:line([(64,55),(64,84)]);circle((60,96,68,104))
        elif key=='range':
            line([(12,64),(116,64)]);line([(33,43),(12,64),(33,85)]);line([(95,43),(116,64),(95,85)])
        elif key in {'initial_combo','extra_combo_count','combo_gain_chance'}:
            d.rounded_rectangle((12,32,72,82),radius=22,outline=white,width=6)
            d.rounded_rectangle((56,48,116,98),radius=22,outline=white,width=6)
            if key=='initial_combo':line([(20,14),(20,33)])
            elif key=='extra_combo_count':line([(91,10),(91,36)]);line([(78,23),(104,23)])
            else:line([(14,108),(70,108),(59,97)])
        elif key in {'heavy_attack_efficiency','melee_heavy_attack_damage'}:
            d.polygon([(25,15),(94,37),(84,66),(15,44)],outline=white,width=6);line([(55,55),(34,115)],10)
            if key=='heavy_attack_efficiency':circle((75,79,115,119))
            else:line([(83,80),(114,110)]);line([(114,80),(83,110)])
        elif key=='slide_crit':
            line([(14,91),(105,91),(87,73)]);circle((50,18,90,58));line([(70,8),(70,68)])
        elif key=='projectile_speed':
            bullet(86,15);line([(12,39),(55,39)]);line([(12,60),(55,60)]);line([(12,81),(112,81),(99,94)])
        elif key=='punch_through':
            line([(48,15),(48,115)],10);line([(78,15),(78,115)],10);line([(12,65),(116,65),(101,50)])
        elif key=='reload_speed':
            d.arc((20,20,108,108),35,330,fill=white,width=8);d.polygon([(107,24),(114,61),(81,49)],fill=white)
        elif key=='recoil':
            line([(17,105),(39,76),(32,51),(63,28),(100,28)]);line([(84,12),(103,28),(84,44)])
        elif key=='zoom':
            circle((18,14,88,84));line([(78,74),(112,110)],12);line([(36,49),(70,49)],5);line([(53,32),(53,66)],5)
        elif key in {'weakpoint_damage','weakpoint_crit_chance'}:
            target()
            if key=='weakpoint_damage':d.polygon([(64,45),(80,64),(64,83),(48,64)],fill=white)
            else:line([(48,64),(80,64)]);line([(64,48),(64,80)])
        elif key=='melee_parry_angle':
            d.arc((10,10,118,118),185,355,fill=white,width=8);line([(64,64),(24,108)]);line([(64,64),(104,108)])
        elif key=='melee_slam_damage':
            line([(64,12),(64,78)]);line([(40,54),(64,80),(88,54)]);line([(10,100),(34,87),(49,105),(65,91),(83,108),(115,94)])
    im.save(ROOT/'assets/icons'/f'{STAT_ICONS[key]}.png')
print(f'{len(STAT_LABELS)} original stat icons generated')
