"""Cache frames, wings, modular equipment, amps, boards, mechs and their components."""
import asyncio, hashlib, io, json, sys, re
from collections import Counter
from pathlib import Path
from urllib.parse import quote
import aiohttp
from PIL import Image, ImageOps
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/equipment'
CATEGORIES=('Warframes','Archwing','Misc','Melee','Primary','Secondary','Gear','Components','Resources')

def classify(item):
    kind=item.get('type','');name=item.get('name','')
    if kind=='Warframe' and item.get('name')!='Helminth':return 'warframe'
    if kind=='Necramech':return 'necramech'
    if kind=='Archwing':return 'archwing'
    if kind=='Zaw Component':return 'zaw'
    if kind=='Kitgun Component':return 'kitgun'
    if kind=='Amp' or name in {'Sirocco','Mote Amp'}:return 'amp'
    if kind=='K-Drive Component':return 'kdrive'
    if name in {'K-Drive Launcher','Necramech Summon'}:return 'kdrive' if name.startswith('K-Drive') else 'necramech'
    if name.startswith('Damaged Necramech'):return 'necramech'
    return ''

async def build(ref='master'):
    OUT.mkdir(parents=True,exist_ok=True)
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
        async def get(url):
            for attempt in range(3):
                try:
                    async with session.get(url) as r:r.raise_for_status();return await r.read()
                except (aiohttp.ClientError,asyncio.TimeoutError):
                    if attempt==2:raise
                    await asyncio.sleep(attempt+1)
        if ref=='master':ref=json.loads(await get('https://api.github.com/repos/WFCD/warframe-items/commits/master'))['sha']
        base=f'https://raw.githubusercontent.com/WFCD/warframe-items/{ref}/'
        groups=await asyncio.gather(*(get(base+'data/json/'+c+'.json') for c in CATEGORIES))
        all_items={i['uniqueName'].lower():i for group in groups for i in json.loads(group)}
        all_items['wiki:mote_amp']={'name':'Mote Amp','uniqueName':'wiki:Mote_Amp','type':'Amp',
            'imageName':'MoteAmp.png','imageUrl':'https://wiki.warframe.com/images/MoteAmp.png?a1576',
            'descriptionurl':'https://wiki.warframe.com/w/File:MoteAmp.png','extraAliases':['微尘增幅器']}
        selected={k:classify(v) for k,v in all_items.items() if classify(v)}
        # Only recipe/components belonging to selected equipment; no generic crafting resources.
        parts={k:v for k,v in all_items.items() if v.get('category')=='Components'}
        while True:
            extra={k:next((selected[p.lower()] for p in v.get('parentUniqueNames',[]) if p.lower() in selected),'') for k,v in parts.items() if k not in selected}
            extra={k:v for k,v in extra.items() if v}
            if not extra:break
            selected.update(extra)
        names=json.loads((ROOT/'core/data/de/name_zh_wfcd.json').read_text()).get('names',{})
        names.update(json.loads((ROOT/'core/data/de/name_zh.json').read_text()))
        suffix={'Blueprint':'蓝图','Chassis':'机体','Neuroptics':'头部神经光元','Systems':'系统','Harness':'外甲','Wings':'机翼'}
        def aliases(k,i,seen=frozenset()):
            if k in seen:return []
            seen=seen|{k}
            out=[i['uniqueName'],*i.get('extraAliases',[])]
            if k not in parts:out.append(i['name'])
            else:out.extend(d['type'] for d in i.get('drops',[]) if d.get('type'))
            if isinstance(names.get(k),str):out.append(names[k])
            for parent in i.get('parentUniqueNames',[]):
                p=all_items.get(parent.lower())
                if not p:continue
                for parent_name in aliases(parent.lower(),p,seen):
                    if parent_name.startswith(('/', 'wiki:')):continue
                    chinese=any('\u4e00'<=c<='\u9fff' for c in parent_name)
                    if chinese and i['name'] in suffix:out.append(parent_name+' '+suffix[i['name']])
                    elif not chinese:out.append(parent_name+' '+i['name'])
            return sorted(set(re.sub(r'<[^>]+>\s*','',v) for v in out if v))
        semaphore=asyncio.Semaphore(8);locks={};done=0;failed=[];missing=[]
        async def cache(k,group):
            nonlocal done
            i=all_items[k];filename=i.get('imageName')
            if not filename:missing.append({'name':i['name'],'uniqueName':i['uniqueName']});return None
            digest=hashlib.sha256(filename.encode()).hexdigest()[:24];path=OUT/(digest+'.png')
            url=i.get('imageUrl') or base+'data/img/'+quote(filename)
            async with semaphore,locks.setdefault(digest,asyncio.Lock()):
                try:
                    if not path.exists():
                        existing=ROOT/'assets/weapons'/path.name
                        data=existing.read_bytes() if existing.exists() else await get(url)
                        with Image.open(io.BytesIO(data)) as im:
                            im=ImageOps.contain(im.convert('RGBA'),(256,256));tmp=path.with_suffix('.tmp')
                            try:im.save(tmp,format='PNG');tmp.replace(path)
                            finally:tmp.unlink(missing_ok=True)
                    with Image.open(path) as im:im.verify()
                except Exception as exc:failed.append({'name':i['name'],'url':url,'error':str(exc)});return None
                done+=1
                if done%100==0:print(f'{done}/{len(selected)} cached',flush=True)
                return {'name':i['name'],'uniqueName':i['uniqueName'],'group':group,'component':k in parts,
                        'aliases':aliases(k,i),'file':path.name,'url':url,
                        **({'descriptionurl':i['descriptionurl']} if i.get('descriptionurl') else {})}
        entries=[v for v in await asyncio.gather(*(cache(k,g) for k,g in selected.items())) if v]
        manifest={'source':'https://github.com/WFCD/warframe-items','revision':ref,'size':256,'items':entries,
                  'counts':dict(Counter(r['group'] for r in entries)),'unavailable':missing,'failed':failed}
        tmp=OUT/'manifest.tmp';tmp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');tmp.replace(OUT/'manifest.json')
        (OUT/'ATTRIBUTION.txt').write_text('Warframe artwork © Digital Extremes. Via WFCD/warframe-items.\nSource revision: '+ref+'\nSource URLs recorded per item in manifest.json. Transparent images resized to fit 256 × 256.\nSupplement: Mote Amp via WARFRAME Wiki; description URL in manifest.json.\nBlueprints/components may share official generic icons. Modular combinations use their individual parts, not invented assembled images.\n')
        (OUT/'WFCD-LICENSE.txt').write_bytes(await get(base+'LICENSE'))
        print(json.dumps({'cached':len(entries),'images':len({r['file'] for r in entries}),'groups':manifest['counts'],'missing':missing,'failed':failed},ensure_ascii=False),flush=True)
        if failed or missing:raise SystemExit(1)
if __name__=='__main__':asyncio.run(build(sys.argv[1] if len(sys.argv)>1 else 'master'))
