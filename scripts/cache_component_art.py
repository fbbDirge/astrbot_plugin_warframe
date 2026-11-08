"""Cache shared part icons from pinned WFCD game assets."""
import asyncio,json,importlib.util,sys,io
from pathlib import Path
import aiohttp
from PIL import Image,ImageOps
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('wf_plugin',ROOT/'__init__.py',submodule_search_locations=[str(ROOT)])
pkg=importlib.util.module_from_spec(spec);sys.modules['wf_plugin']=pkg;spec.loader.exec_module(pkg)
from wf_plugin.component_art import PARTS
REF='23804b64bc248069ce39adb9f52e9f546d8f343e'
async def main():
 out=ROOT/'assets/components';out.mkdir(exist_ok=True)
 files={k+suffix:v for k,(a,b,_) in PARTS.items() for suffix,v in [('',a),('_prime',b)]}
 sources={};sem=asyncio.Semaphore(6)
 async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=45)) as session:
  async def get(name):
   url=f'https://raw.githubusercontent.com/WFCD/warframe-items/{REF}/data/img/{name}'
   sources[name]=url
   if (out/name).exists():return
   async with sem:
    for attempt in range(3):
     try:
      async with session.get(url) as response:response.raise_for_status();data=await response.read()
      with Image.open(io.BytesIO(data)) as im:ImageOps.contain(im.convert('RGBA'),(256,256)).save(out/name)
      return
     except Exception:
      if attempt==2:raise
      await asyncio.sleep(1)
  await asyncio.gather(*(get(name) for name in set(files.values())))
 (out/'manifest.json').write_text(json.dumps({'revision':REF,'files':files,'sources':sources},ensure_ascii=False,indent=2)+'\n')
 (out/'ATTRIBUTION.txt').write_text('Warframe artwork © Digital Extremes. Via WFCD/warframe-items. Exact source URLs and revision in manifest.json. Shared part icons resized to 256px; Prime and ordinary parts kept separate.\n')
 print(f'{len(files)} part variants, {len(set(files.values()))} shared images cached')
if __name__=='__main__':asyncio.run(main())
