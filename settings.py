"""One configuration for native services; read v0.6 settings on upgrade."""
import json
from pathlib import Path

class GameConfig(dict):
    def __init__(self,parent):
        self.parent=parent
        schema=json.loads((Path(__file__).parent/'core/default_config.json').read_text())
        super().__init__({k:v['default'] for k,v in schema.items() if 'default' in v})
        self.update(parent.get('sdjk',{}))
        self.update(parent.get('game',{}))
        self['default_platform']={'ps4':'ps','xb1':'xb','swi':'sw'}.get(parent.get('default_platform'),parent.get('default_platform','pc'))
        self['page_size']=parent.get('page_size',10)
        self['render_mode']='image'
        configured=parent.get('game') or parent.get('sdjk') or {}
        self['vision_routes_isolated']=configured.get('vision_routes_isolated',True)
        common=self.get('vision_provider_id') or parent.get('riven_vision_provider','')
        for key in ('vision_provider_id_riven','vision_provider_id_scan'):
            if not self.get(key):self[key]=common
        self['flaresolverr_enabled']=False
    def save_config(self,*args,**kwargs):
        self.parent['game']=dict(self)
        self.parent['page_size']=self.get('page_size',10)
        self.parent['default_platform']={'ps':'ps4','xb':'xb1','sw':'swi'}.get(self.get('default_platform'),self.get('default_platform','pc'))
        self.parent.pop('sdjk',None)
        save=getattr(self.parent,'save_config',None)
        if save:save()
