"""One-image Circuit detail: equipment tiles and the complete rotation table."""
import uuid
from PIL import ImageDraw,ImageFont
from .renderer import FONT,load_icon,_rgb,_mix,_draw_centered,_draw_clock,_draw_row_bracket,_draw_panel_decor,ROW_FALLBACK_ACCENTS
from .weapon_art import exact_weapon
from .equipment_art import exact_equipment

def render(renderer,card,theme):
    data=card.incarnon;width=renderer.WIDTH;panel_x=8;x=18;inner=width-2*x;gap=12
    def face(size,bold=False,weight=None):
        path=theme.get('font_bold_path' if bold else 'font_path') or str(FONT)
        try:font=ImageFont.truetype(path,size)
        except OSError:font=ImageFont.truetype(str(FONT),size)
        w_val = weight if weight is not None else (680 if bold else 500)
        try:
            font.set_variation_by_axes([max(a['minimum'],min(a['maximum'],w_val)) if a['name']==b'Weight' else a['default'] for a in font.get_variation_axes()])
        except (OSError,AttributeError):pass
        return font
    body_sz=round(52*(theme['font_size']/26)**0.48)
    small_sz=max(38,round(body_sz*0.85))
    badge_sz=max(34,round(body_sz*0.74))
    title_sz=round(70*(theme['title_size']/38)**0.48)
    font=face(body_sz);bold=face(body_sz,True);small=face(small_sz,False,520)
    badge=face(badge_sz,True,660)
    heading=face(body_sz+2,True,700);titlefont=face(title_sz,True,750)
    step=body_sz+10;smallstep=small_sz+8
    titlelines=renderer.wrap(card.title,titlefont,inner)
    ops=[];y=88+len(titlelines)*(title_sz+12)+18
    def section(label,accent='#0284C7'):
        nonlocal y
        ops.append(('heading',y,label,accent));y+=body_sz+24
    def grid(entries,columns,compact=False,accent='#0284C7'):
        nonlocal y
        cw=(inner-(columns-1)*gap)//columns;size=58 if compact else 74
        for start in range(0,len(entries),columns):
            cells=[];rh=0
            for entry in entries[start:start+columns]:
                if isinstance(entry,str):entry={'name':entry,'identity':entry}
                lines=renderer.wrap(entry['name'],bold,max(40,cw-size-32))
                h=max(size,len(lines)*step)+18;rh=max(rh,h)
                cells.append((entry,lines))
            ops.append(('tiles',y,cells,cw,rh,size,accent));y+=rh+8
        y+=4
    section('本周战甲','#0284C7');grid(data['frames'],3,False,'#0284C7')
    section('下周战甲','#0D9488');grid(data['next_frames'],3,True,'#0D9488')
    section('本周灵化武器','#7C3AED');grid(data['weapons'],5 if theme['font_size']<=30 else 3,False,'#7C3AED')
    section('下周灵化武器','#D97706');grid(data['next_weapons'],5 if theme['font_size']<=30 else 3,True,'#D97706')
    seconds=data['remaining_seconds'];days,seconds=divmod(seconds,86400);hours,seconds=divmod(seconds,3600);minutes,seconds=divmod(seconds,60)
    remaining=f'距离换轮：{days}天{hours}小时{minutes}分{seconds}秒'
    ops.append(('remaining',y,remaining));y+=step+20
    section('灵化武器完整轮换表','#2563EB')
    # Keep all weeks, including wrapped names; never truncate or paginate this report.
    labelw=max(220,int(small.getlength('第1周·本周'))+28);cw=(inner-labelw)/5
    for index,week in enumerate(data['weeks']):
        cells=[renderer.wrap(w['name'],small,int(cw)-18) for w in week]
        rh=max(1,max(map(len,cells),default=1))*smallstep+16
        ops.append(('rotation',y,index,cells,rh,labelw,cw));y+=rh+5
    footer='每周一北京时间 08:00 换轮 · 普通回廊选战甲，钢铁回廊选灵化适配器'
    footlines=renderer.wrap(footer,small,inner-32);y+=10
    footer_h=len(footlines)*smallstep+20
    height=int(y+footer_h+64)
    canvas=renderer.background(theme,width,height);draw=ImageDraw.Draw(canvas,'RGBA')
    alpha=theme['panel_opacity'];title_rgb=_rgb(theme['title'])
    draw.rounded_rectangle((panel_x+4,22,width-panel_x+4,height-10),radius=28,fill=(15,23,42,min(20,alpha//10)))
    draw.rounded_rectangle((panel_x+2,19,width-panel_x+2,height-13),radius=28,fill=(15,23,42,min(32,alpha//7)))
    draw.rounded_rectangle((panel_x,16,width-panel_x,height-16),radius=28,fill=(*_rgb(theme['panel_color']),alpha),outline=(*_mix(title_rgb,(186,230,253),.65),min(240,alpha)),width=2)
    _draw_panel_decor(draw,width,height,panel_x,title_rgb,88+len(titlelines)*(title_sz+12)+14,small,badge)

    # Top brand capsule + category pill
    _,b_top,_,b_bot=badge.getbbox('WARFRAME')
    bh=(b_bot-b_top)+14;bw=int(badge.getlength('WARFRAME'))+38;sw=int(badge.getlength('星际战甲助手'))+26
    cap_y=24
    draw.rounded_rectangle((x,cap_y,x+bw+sw,cap_y+bh),radius=10,fill=(*_mix(title_rgb,(224,242,254),.85),240),outline=(*title_rgb,110),width=1)
    draw.rounded_rectangle((x,cap_y,x+bw,cap_y+bh),radius=10,fill=(*title_rgb,248))
    draw.polygon([(x+12,cap_y+bh//2),(x+18,cap_y+bh//2-6),(x+24,cap_y+bh//2),(x+18,cap_y+bh//2+6)],fill='#F59E0B')
    _draw_centered(draw,(x+16,cap_y,x+bw,cap_y+bh),'WARFRAME',badge,'#FFFFFF')
    _draw_centered(draw,(x+bw,cap_y,x+bw+sw,cap_y+bh),'星际战甲助手',badge,theme['title'])
    cw_cat=int(badge.getlength('❖ 双衍回廊'))+24
    draw.rounded_rectangle((x+bw+sw+10,cap_y,x+bw+sw+10+cw_cat,cap_y+bh),radius=10,fill=(243,232,255,235),outline=(139,92,246,165),width=1)
    _draw_centered(draw,(x+bw+sw+10,cap_y,x+bw+sw+10+cw_cat,cap_y+bh),'❖ 双衍回廊',badge,'#7C3AED')
    tw=int(badge.getlength('CIRCUIT'))+26
    draw.rounded_rectangle((x+inner-tw,cap_y,x+inner,cap_y+bh),radius=10,fill=(220,252,231,235),outline=(16,185,129,175),width=1)
    _draw_centered(draw,(x+inner-tw,cap_y,x+inner,cap_y+bh),'CIRCUIT',badge,'#047857')

    ty=88
    th_total=len(titlelines)*(title_sz+12)-12
    draw.rounded_rectangle((x,ty,x+7,ty+th_total),radius=3,fill=theme['title'])
    draw.rounded_rectangle((x,ty,x+17,ty+4),radius=2,fill='#06B6D4')
    draw.rounded_rectangle((x,ty+th_total-4,x+17,ty+th_total),radius=2,fill='#7C3AED')
    for line in titlelines:draw.text((x+24,ty),line,font=titlefont,fill=theme['title'],anchor='lt');ty+=title_sz+12
    div_y=ty+4
    draw.rounded_rectangle((x,div_y-1,x+84,div_y+2),radius=1,fill=theme['title'])
    draw.polygon([(x+94,div_y-5),(x+100,div_y),(x+94,div_y+5),(x+88,div_y)],fill='#F59E0B')
    draw.line((x+106,div_y,x+inner,div_y),fill=(100,116,139,65),width=1)

    def artwork(identity,px,py,size):
        key=exact_weapon(identity);name='weapon:'+key if key else ''
        if not key:
            key=exact_equipment(identity);name='equipment:'+key if key else ''
        im=load_icon(name,size)
        if im:
            draw.rounded_rectangle((px-2,py-2,px+size+2,py+size+2),radius=10,fill=(232,240,250,235),outline=(56,189,248,155),width=1)
            canvas.paste(im,(int(px+(size-im.width)/2),int(py+(size-im.height)/2)),im)
    for op in ops:
        kind,oy,*args=op
        if kind=='heading':
            lbl,acc=args
            draw.rounded_rectangle((x,oy,x+6,oy+body_sz+10),radius=3,fill=acc)
            draw.rounded_rectangle((x,oy,x+15,oy+4),radius=1,fill=theme['title'])
            draw.text((x+22,oy+1),lbl,font=heading,fill=theme['title'],anchor='lt')
        elif kind=='tiles':
            cells,cw,rh,size,acc=args
            for i,(entry,lines) in enumerate(cells):
                px=x+i*(cw+gap)
                draw.rounded_rectangle((px,oy,px+cw,oy+rh),radius=14,fill=(248,251,254,min(alpha,236)),outline=(*_rgb(theme['line_color']),215),width=1)
                _draw_row_bracket(draw,px,oy,cw,rh,acc,ROW_FALLBACK_ACCENTS[(i+1)%len(ROW_FALLBACK_ACCENTS)])
                artwork(entry['identity'],px+12,int(oy+(rh-size)/2),size)
                for j,line in enumerate(lines):draw.text((px+size+22,oy+(rh-len(lines)*step)/2+j*step+2),line,font=bold,fill=theme['item_name'],anchor='lt')
        elif kind=='remaining':
            rem_txt=args[0]
            pw=min(inner,int(bold.getlength(rem_txt))+82);ph=step+10
            draw.rounded_rectangle((x,oy-4,x+pw,oy-4+ph),radius=ph//2,fill=(255,251,235,244),outline=(245,158,11,195),width=1)
            cr=max(9,body_sz//2-2)
            _draw_clock(draw,x+18+cr,oy-4+ph//2,cr,'#B45309')
            draw.text((x+28+cr*2,oy+1),rem_txt,font=bold,fill=theme['fissure_type'],anchor='lt')
        elif kind=='rotation':
            index,cells,rh,labelw,cw=args
            current=index==data['current_week'];nxt=index==data['next_week']
            color=theme['riven_stat'] if current else theme['item_name'] if nxt else theme['text']
            c_rgb=_rgb(color)
            bg_fill=(*c_rgb,28) if (current or nxt) else ((248,250,253,225) if index%2==0 else (241,245,250,225))
            bd_col=(*c_rgb,160) if (current or nxt) else (*_rgb(theme['line_color']),180)
            draw.rounded_rectangle((x,oy,x+inner,oy+rh),radius=10,fill=bg_fill,outline=bd_col,width=1)
            draw.rounded_rectangle((x,oy+5,x+5,oy+rh-5),radius=2,fill=color if (current or nxt) else '#94A3B8')
            label=f'第{index+1}周·本周' if current else f'第{index+1}周·下周' if nxt else f'第{index+1}周'
            draw.text((x+12,oy+8),label,font=small,fill=color,anchor='lt')
            for i,lines in enumerate(cells):
                for j,line in enumerate(lines):draw.text((x+labelw+i*cw+8,oy+8+j*smallstep),line,font=small,fill=color,anchor='lt')
    draw.rounded_rectangle((x,y-8,x+inner,y-8+footer_h),radius=11,fill=(237,243,250,min(215,alpha)),outline=(186,230,253,185),width=1)
    draw.rounded_rectangle((x,y-3,x+4,y-13+footer_h),radius=2,fill='#06B6D4')
    for i,line in enumerate(footlines):draw.text((x+16,y+4+i*smallstep),line,font=small,fill=theme['muted'],anchor='lt')
    path=renderer.output/(uuid.uuid4().hex+'.png');canvas.save(path);return path
