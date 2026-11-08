"""Build the offline bounty catalogue from pinned WFCD exports and local DE names.
Usage: python scripts/cache_bounty_art.py assets/bounties/catalogue-source.json
The index stores selected source filenames and existing icon references.
"""
import concurrent.futures,hashlib,io,json,re,sys
from pathlib import Path
from urllib.parse import quote
import httpx
from PIL import Image,ImageOps
ROOT=Path(__file__).resolve().parents[1]
REF='23804b64bc248069ce39adb9f52e9f546d8f343e'
BASE=f'https://raw.githubusercontent.com/WFCD/warframe-items/{REF}/data/img/'

def cache(index):
 out=ROOT/'assets/bounties';out.mkdir(exist_ok=True)
 def download(pair):
  label,row=pair
  if 'image' not in row:return label,row
  name=row['image'];key=hashlib.sha256(name.encode()).hexdigest()[:24];dest=out/(key+'.png')
  url=BASE+quote(name)
  if not dest.exists():
   for attempt in range(3):
    try:
     r=httpx.get(url,timeout=40);r.raise_for_status()
     with Image.open(io.BytesIO(r.content)) as im:ImageOps.contain(im.convert('RGBA'),(128,128)).save(dest)
     break
    except Exception:
     if attempt==2:raise
  return label,{'icon':('blueprint:' if row.get('blueprint') else '')+'bounty:'+key,'file':dest.name,'url':url,'uniqueName':row.get('path','')}
 # Deduplicate image downloads before parallel work.
 unique={r['image']:r for r in index.values() if 'image' in r}
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as p:list(p.map(download,unique.items()))
 result=dict(download(p) for p in index.items())
 (out/'manifest.json').write_text(json.dumps({'revision':REF,'items':result},ensure_ascii=False,indent=2)+'\n')
 (out/'ATTRIBUTION.txt').write_text('Warframe artwork © Digital Extremes. Via WFCD/warframe-items, revision '+REF+'. Exact URLs in manifest.json. Resized to 128px. Category fallback icons are labeled in the manifest.\n')
 print('cached',len(result),'rewards,',len(unique),'images',flush=True)
if __name__=='__main__':cache(json.loads(Path(sys.argv[1]).read_text()))
