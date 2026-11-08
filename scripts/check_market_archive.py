"""Check the actual market archive, not the full developer checkout."""
import importlib,sys,tempfile,zipfile,json,shutil
from pathlib import Path
from PIL import Image
archive=Path(sys.argv[1]).resolve()
assert archive.stat().st_size<16_000_000,'Market archive exceeds 16 MB'
with tempfile.TemporaryDirectory() as tmp:
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None;z.extractall(tmp)
 sys.path.insert(0,tmp)
 root=Path(tmp)/'astrbot_plugin_warframe'
 render=importlib.import_module('astrbot_plugin_warframe.renderer')
 presentation=importlib.import_module('astrbot_plugin_warframe.presentation')
 theme=importlib.import_module('astrbot_plugin_warframe.theme')
 checked=0
 for group in ('weapons','equipment','bounties'):
  data=json.loads((root/'assets'/group/'manifest.json').read_text())['weapons' if group=='weapons' else 'items']
  entries=data.values() if isinstance(data,dict) else data
  for row in entries:
   if row.get('file'):
    with Image.open((root/'assets'/group/row['file']).with_suffix('.webp')) as im:im.verify()
    checked+=1
 for name in render.ICON_NAMES:assert render.load_icon(name,40) is not None,name
 c=presentation.table('市场安装包测试',['节点','奖励物品'],[['Stephano（天王星）','福马蓝图'],['Galatea（海王星）','Volt Prime 系统蓝图']])
 result=render.CardRenderer(Path(tmp)/'output').render(c,theme.theme_from({}))
 shutil.copyfile(result,archive.parent/'market-package-preview.png')
 print('Market archive OK:',archive.stat().st_size,'bytes;',checked,'catalogue records; all standard icons; font and render OK')
