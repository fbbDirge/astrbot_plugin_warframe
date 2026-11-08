"""Build offline compact artwork alongside original PNGs for git archive exports."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image,ImageOps
ROOT=Path(__file__).resolve().parents[1]
def convert(path):
    with Image.open(path) as im:
        ImageOps.contain(im.convert('RGBA'),(128,128)).save(path.with_suffix('.webp'),format='WEBP',quality=75,method=1)
paths=[p for group in ('weapons','equipment','bounties','components','icons') for p in (ROOT/'assets'/group).glob('*.png')]
with ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(convert,paths))
print('Compact artwork generated; original PNGs retained.')
