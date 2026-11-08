"""Build a pinned, complete local weapon artwork bundle. Safe to rerun after interruption."""
import asyncio, hashlib, io, json, sys
from pathlib import Path
from urllib.parse import quote
import aiohttp
from PIL import Image, ImageOps
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/weapons'
CATEGORIES=('Primary','Secondary','Melee','Arch-Gun','Arch-Melee','SentinelWeapons')
async def build(ref='master'):
    OUT.mkdir(parents=True,exist_ok=True)
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
        async def get(url):
            for attempt in range(3):
                try:
                    async with session.get(url) as r:
                        r.raise_for_status();return await r.read()
                except (aiohttp.ClientError,asyncio.TimeoutError):
                    if attempt==2:raise
                    await asyncio.sleep(attempt+1)
        if ref=='master':
            ref=json.loads(await get('https://api.github.com/repos/WFCD/warframe-items/commits/master'))['sha']
        base=f'https://raw.githubusercontent.com/WFCD/warframe-items/{ref}/'
        groups=await asyncio.gather(*(get(base+'data/json/'+quote(c)+'.json') for c in CATEGORIES))
        local=json.loads((ROOT/'core/data/weapons_stats.json').read_text())
        names=json.loads((ROOT/'core/data/de/name_zh.json').read_text())
        if 'names' in names:names=names['names']
        rows={}
        for group in groups:
            for item in json.loads(group):
                if item.get('imageName'):rows[item['uniqueName'].lower()]=item
        # Include weapon records from additional categories when present in our local weapon catalog.
        missing=set(local)-set(rows)
        if missing:
            extra=await asyncio.gather(*(get(base+'data/json/'+c+'.json') for c in ('Misc','Gear','Sentinels','Pets','Warframes')))
            all_items=[item for group in extra for item in json.loads(group)]
            for item in all_items:
                key=item.get('uniqueName','').lower()
                if key in missing and item.get('imageName'):rows[key]=item
        # A local #melee entry is a firing/melee mode of the same weapon, not a new model.
        for key in set(local)-set(rows):
            base_key,sep,mode=key.partition('#')
            if sep and base_key in rows:
                rows[key]={**rows[base_key], 'name':local[key]['name'], 'uniqueName':local[key].get('uniqueName',key)}
        semaphore=asyncio.Semaphore(8);done=0;failures=[]
        async def cache(key,item):
            nonlocal done
            source=base+'data/img/'+quote(item['imageName'])
            digest=hashlib.sha256(item['imageName'].encode()).hexdigest()[:24]
            path=OUT/(digest+'.png')
            async with semaphore:
                try:
                    if not path.exists():
                        data=await get(source)
                        with Image.open(io.BytesIO(data)) as im:
                            im=ImageOps.contain(im.convert('RGBA'),(256,256))
                            tmp=path.with_suffix('.'+hashlib.sha256(key.encode()).hexdigest()[:12]+'.tmp')
                            try:
                                im.save(tmp,format='PNG');tmp.replace(path)
                            finally:tmp.unlink(missing_ok=True)
                    with Image.open(path) as im:im.verify()
                except Exception as exc:
                    failures.append({'name':item['name'],'url':source,'error':str(exc)});return None
                done+=1
                if done%100==0:print(f'{done}/{len(rows)} cached',flush=True)
                aliases=[item['name'],item['uniqueName'],local.get(key,{}).get('zh','')]
                translated=names.get(key,'')
                if isinstance(translated,str):aliases.append(translated)
                return {'name':item['name'],'uniqueName':item['uniqueName'],'category':item.get('category',''),
                        'aliases':sorted(set(a for a in aliases if a)),'file':path.name,'url':source}
        result=await asyncio.gather(*(cache(k,v) for k,v in rows.items()))
        unavailable=[{'uniqueName':key,'name':local[key]['name']} for key in sorted(set(local)-set(rows))]
        manifest={'source':'https://github.com/WFCD/warframe-items','revision':ref,'size':256,
                  'weapons':[r for r in result if r],'unavailable':unavailable,'failed':failures}
        (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        (OUT/'ATTRIBUTION.txt').write_text('Warframe artwork © Digital Extremes. Distributed via WFCD/warframe-items.\nSource revision: '+ref+'\nEach source URL is recorded in manifest.json.\nImages resized to fit 256 × 256, preserving transparency.\n')
        (OUT/'WFCD-LICENSE.txt').write_bytes(await get(base+'LICENSE'))
        print(f'{done} weapons; {len(unavailable)} without upstream image; {len(failures)} failed',flush=True)
        if failures:raise SystemExit(1)
if __name__=='__main__':asyncio.run(build(sys.argv[1] if len(sys.argv)>1 else 'master'))
