"""Personal theme and admin appearance integration."""
from .core.render import ImageRenderer
from .core.commands import Reply
from .presentation import present
from .theme import theme_from
from .renderer import FONT

class Appearance(ImageRenderer):
    def __init__(self,owner,directory):
        self.owner=owner
        super().__init__(directory,font_path=owner.config.get("font_path") or str(FONT))
    def style_config(self):
        from .core import render as upstream_render
        config=dict(self.owner.config)
        appearance=self.load_appearance()
        theme=upstream_render._THEME
        mapping={'bg':'background_color','accent':'title','ink':'text','ink_dim':'muted',
                 'cyan':'fissure_type','violet':'riven_stat','red':'riven_negative',
                 'green':'wm_quantity','blue':'wm_user','magenta':'wm_price','teal':'fissure_map',
                 'rarity_gold':'tier_lith','steel':'tier_meso','rarity_silver':'tier_neo',
                 'amber':'tier_axi','panel':'panel_color','line':'line_color'}
        for key,value in (theme.get('colors') or {}).items():
            if key in mapping:
                config[mapping[key]]=value if isinstance(value,str) else '#%02x%02x%02x'%tuple(value)
        if appearance.get('font_regular'):
            config['font_path']=appearance['font_regular']
        if appearance.get('font_bold'):
            config['font_bold_path']=appearance['font_bold']
        if theme.get('bg_image') is not None:
            config['background_image']=str(self.theme_dir/'bg.png')
            config['background_fit']=theme.get('bg_fit','cover')
            config['background_pos']=theme.get('bg_pos','c')
            config['background_scale']=theme.get('bg_scale',60)
            config['background_dim']=theme.get('bg_dim',0)
        if theme.get('logo') is not None:
            config['logo_image']=str(self.theme_dir/'logo.png')
        if appearance.get('theme'):
            config['panel_opacity']=round(float(theme.get('panel_alpha',1))*255)
        return config

    @property
    def available(self):return True
    def render(self,title,lines,footer=''):
        cards=present(Reply(title=title,lines=lines,footer=footer))
        # Panel previews use one page, while chat dispatch preserves every page.
        return str(self.owner.renderer.render(cards[0],theme_from(self.style_config())))
