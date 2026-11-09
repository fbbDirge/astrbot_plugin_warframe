"""Native report layouts: semantic tables, sections, charts and instructions.

Business formatters expose section/table delimiters as a stable internal contract.
They are parsed once here; no plugin invocation, message forwarding or text response.
"""
import re
from .cards import Card, IconText
from .core.render import parse_ranges, parse_chart, _expand_tents_line, display_footer
from .world_icons import RELICS, FACTIONS
from .localization import translate

ROLE_HEADERS={
    '商品':'item_name','物品':'item_name','星球':'fissure_map','地区':'fissure_map','地区信息':'fissure_map',
    '在售':'wm_price','收购':'wm_price','价格':'wm_price','白金':'wm_price','单价':'wm_price','合计':'wm_price','一口价':'wm_price',
    '卖家':'wm_user','买家':'wm_user','玩家':'wm_user','用户':'wm_user','数量':'wm_quantity',
    '挂牌价差':'wm_price','加权占比':'drop_chance','挂牌中位数':'wm_price','正词条 / 负词条':'riven_stat','元素':'damage','限制':'damage','词条':'riven_stat','属性':'riven_stat','区间':'riven_range','理论区间':'riven_range',
    '距中':'riven_grade','区间位':'riven_grade','评级':'riven_grade',
    '地图 / 星球':'fissure_map','任务类型':'fissure_type','节点':'fissure_map','地图':'fissure_map','地点':'fissure_map','类型':'fissure_type','任务':'fissure_type',
    '剩余':'muted','时间':'muted','状态':'muted','信誉':'muted','等级':'wm_quantity',
    '奖励物品':'item_name','奖励':'item_name','稀有度':'rarity','概率':'drop_chance','掉率':'drop_chance',
    '伤害':'damage','DPS':'damage','持续DPS':'damage','总伤害':'damage',
}
TIER_ROLES={'古纪':'tier_lith','前纪':'tier_meso','中纪':'tier_neo','后纪':'tier_axi','安魂':'tier_requiem','全能':'tier_omnia','先锋':'tier_omnia'}
MARK_ROLES={'v':'riven_stat','r':'riven_negative','g':'wm_quantity','m':'wm_price','c':'fissure_map','b':'wm_user'}


def clean(text):
    text=re.sub(r'⟦pol:([^⟧]+)⟧',lambda m:'极性 '+m[1],str(text))
    text=re.sub(r'⟦/?[^⟧]+⟧','',text)
    return text.replace('Warframe SDJKBOT','Warframe 助手').replace('SDJKBOT','Warframe 助手')


def roll_role(value):
    match=re.match(r'^([SABCD])\s+\d',str(value))
    return 'roll_'+match[1].lower() if match else 'roll_unknown'


def cell(value,header='',default='text'):
    raw=str(value); text=clean(raw).strip()
    role=ROLE_HEADERS.get(header,default)
    if re.fullmatch(r'[23]\+[01]',header):role='riven_range'
    if any(k in header for k in ('最低价','最高价','一口价')):role='wm_price'
    if 'DPS' in header or header in {'实战伤害','单发伤害'}:role='damage'
    if text.startswith('▼'):role='riven_negative'
    elif text.startswith('▲'):role='riven_stat'
    elif role=='text':
        marker=re.search(r'⟦([a-z])⟧',raw)
        if marker:role=MARK_ROLES.get(marker[1],role)
    if header in {'纪元','遗物等级','档位'} or text.strip('[]') in TIER_ROLES:
        tier=text.strip('[]');role=TIER_ROLES.get(tier,role)
        if tier in RELICS:return (IconText(tier,RELICS[tier]),role)
    if header in {'杜卡德','杜卡币','现金','星币','内融核心','赤毒'} and re.fullmatch(r'\d[\d,.]*',text):
        from .display_icons import CURRENCY_ICONS
        return IconText(text,CURRENCY_ICONS[header]),role
    if header in {'派系','敌人','攻击方','防御方'}:
        icon,label=FACTIONS.get(text.casefold(),('',text))
        return (IconText(label,icon),'faction')
    if role in {'fissure_map','fissure_type','item_name'}:text=translate(text)
    if role in {'text','title','fissure_map'} and header not in {'卖家','买家','用户名','玩家','用户'}:
        from .cycle_icons import cycle_icon
        icon=cycle_icon(text)
        if icon:return IconText(text,icon),role
        from .planet_icons import planet_icon
        icon=planet_icon(text)
        if icon:return IconText(text,icon),role
    if header=='奖励' and text.startswith('Forma '):text=text.replace('Forma ','福马 ',1)
    if role=='wm_price':text=re.sub(r'(?<=\d)p\b',' 白金',text)
    if header in {'评分','数值评分'}:role=roll_role(text)
    return text,role


def arbitration_rating_role(value):
    # Read the displayed grade, never infer it from the community yield number.
    match=re.match(r'^(S|A[+−-]?|F)(?=$|[\s*＊（(])', str(value).strip())
    return {'S':'arb_s','A+':'arb_a_plus','A':'arb_a','A-':'arb_a_minus','A−':'arb_a_minus','F':'arb_f'}.get(match[1] if match else '', 'arb_unrated')


def table(title,headers,rows):
    # Keep every supplied value, even if an upstream header omitted a column.
    count=max([len(headers),*[len(r) for r in rows]])
    headers=list(headers)+['补充信息']*max(0,count-len(headers))
    return Card('',title=title,columns=tuple(headers),rows=[
        [quality_cell(row,i,h,headers) for i,h in enumerate(headers)] for row in rows])


def quality_cell(row, i, header, headers):
    text, role = arbitration_cell(row[i] if i < len(row) else '', header, headers)
    if '评分' in headers and header in {'词条','距中','区间位','评分'}:
        index = headers.index('评分')
        role = roll_role(row[index] if index < len(row) else '')
    return text, role


def arbitration_cell(value, header, headers):
    text,role=cell(value,header)
    if header=='名称' and any(h in headers for h in ('价格','权重','类别')):role='item_name'
    if header=='评级' and '派系' in headers:
        role=arbitration_rating_role(text)
    return text,role


def sections(lines,title):
    """Turn formatter sections into content-specific table/document blocks."""
    result=[]; heading=''; headers=None; rows=[]; paragraphs=[]; notes=[]
    def flush():
        nonlocal headers,rows,paragraphs,notes
        if rows:
            result.append(table(heading or title,headers or ['内容'],rows))
        if paragraphs:
            result.append(Card('',title=heading or title,columns=('说明',),rows=[[cell(p)] for p in paragraphs]))
        if notes:
            if result:result[-1].footer+='\n'+'\n'.join(map(clean,notes))
            else:result.append(Card('',title=heading or title,columns=('提示',),rows=[[cell(p,default='muted')] for p in notes]))
        headers=None;rows=[];paragraphs=[];notes=[]
    for original in lines:
        ranges=parse_ranges(original);chart=parse_chart(original)
        if ranges:
            flush();result.append(table('词条数值区间',['词条',*ranges['cols']],ranges['rows']));continue
        if chart:
            flush()
            block=table(chart['title'],['时间',chart['unit']],[
                [label or str(i+1),'无数据' if value is None else f'{value:g} {chart["unit"]}']
                for i,(label,value) in enumerate(zip(chart['labels'],chart['values']))])
            block.chart=chart;result.append(block);continue
        for raw in _expand_tents_line(original):
            if not raw.strip():continue
            plain=clean(raw).strip()
            if plain.startswith('◆'):
                flush();heading=clean(raw).lstrip('◆ ').strip()
                label,sep,value=heading.partition('：')
                if sep and value and len(label)<=30:
                    result.append(Card('',title=label,columns=(label,),rows=[[cell(value,label)]]))
                    heading=''
                else:
                    heading=translate(heading)
                continue
            if plain=='奖励物品' and raw.startswith('　'):
                if rows or paragraphs:flush()
                headers=['奖励物品'];continue
            if headers==['奖励物品'] and plain.startswith('· '):
                rows.append([plain[2:].strip()]);continue
            if plain.startswith('※'):
                notes.append(plain.lstrip('※ '));continue
            # Full-width spaces are the formatter's actual table-cell delimiter.
            if '\u3000' in raw and not plain.startswith(('http','/w ')):
                value=raw.strip(' \n')
                value=value.removeprefix('· ') if plain.startswith('·') else value.lstrip('\u3000')
                cells=value.split('\u3000')
                if len(cells)==1:
                    notes.append(clean(value))
                    continue
                is_header=not plain.startswith('·') and not rows and len(cells)>1
                if is_header:
                    if paragraphs:flush()
                    headers=[clean(v).strip() for v in cells]
                elif headers:
                    rows.append(cells)
                else:
                    # Implicit tables (e.g. reward lists) receive domain labels.
                    inferred=['名称','数值'] if len(cells)==2 else ['名称']+['详情']*(len(cells)-1)
                    headers=inferred;rows.append(cells)
            else:
                if rows:flush()
                paragraphs.append(raw.lstrip('· '))
    flush()
    return merge_summaries(result)


def merge_summaries(blocks):
    result=[];pending=[]
    def flush():
        if pending:
            result.append(Card('',title='概览',columns=('指标','结果'),rows=[[(b.title,'title'),b.rows[0][0]] for b in pending],footer='\n'.join(b.footer for b in pending if b.footer)))
            pending.clear()
    for b in blocks:
        if b.columns==(b.title,) and len(b.rows)==1:pending.append(b)
        else:flush();result.append(b)
    flush()
    return result


def present(reply,command='',page_rows=22):
    """Produce bounded native reports, retaining all pages, actions and details."""
    pages=reply.pages or [(reply.title or 'Warframe 查询',reply.lines)]
    if reply.raw_text is not None:pages=[(reply.title or 'Warframe 提示',str(reply.raw_text).splitlines())]
    output=[]
    for title,lines in pages:
        if getattr(lines,'domain','')=='incarnon_detail':
            card=Card('',title=title);card.kind='incarnon_detail';card.incarnon=lines.meta
            output.append(card)
            continue
        if getattr(lines,'domain','') in {'arbitration_now','alerts'}:
            card=Card('',title=clean(title),footer=clean(display_footer(reply.footer)))
            card.blocks=native_blocks(lines,[]);card.kind=command
            output.append(card)
            continue
        if getattr(lines,'domain','')=='fissures':
            # A query is a complete task list, never a separate summary-only first image.
            view=native_blocks(lines,[])[0]
            view.title=clean(title);view.kind=command
            notes=[clean(line).lstrip('※ ') for line in lines if str(line).startswith('※')]
            view.footer='\n'.join(filter(None,[clean(display_footer(reply.footer)),*notes]))
            output.append(view)
            continue
        if command=='bounty' or title=='赏金任务':
            from .bounty_art import bounty_blocks
            blocks=bounty_blocks(lines)
        else:
            blocks=sections(lines,title)
        # A formatter can attach typed views to its output; prefer those over display text.
        blocks=native_blocks(lines,blocks)
        if command=='reroll':
            card=Card('',title=clean(title),footer=clean(display_footer(reply.footer)))
            card.blocks=blocks;card.kind=command;output.append(card)
            continue
        current=[];weight=0
        def emit():
            nonlocal current,weight
            if current:
                card=Card('',title=clean(title),footer=clean(display_footer(reply.footer)))
                card.blocks=current;card.kind=command;card.artwork=getattr(reply,'artwork',('',''))
                output.append(card);current=[];weight=0
        for block in blocks:
            for start in range(0,len(block.rows) or 1,page_rows):
                chunk=Card('',title=block.title,columns=block.columns,rows=block.rows[start:start+page_rows],footer=block.footer if start+page_rows>=len(block.rows) else '',chart=block.chart if start==0 else None)
                cost=sum(max(1,max((len(str(t))//max(16,60//len(block.columns))+1 for t,_ in row),default=1)) for row in chunk.rows)+2+(4 if chunk.chart else 0)
                if current and weight+cost>page_rows:emit()
                current.append(chunk);weight+=cost
        emit()
    extras=[]
    if reply.extra_text:extras.extend(str(reply.extra_text).splitlines())
    if reply.whisper:extras.extend(reply.whisper)
    if reply.actions:extras.extend(f'{a.label}：{a.send}' for a in reply.actions)
    if extras:
        block=Card('',title='交易密语与后续操作',columns=('可复制指令',),rows=[[(clean(x),'text')] for x in extras])
        card=Card('',title='后续操作');card.blocks=[block];output.append(card)
    if not output:output=[Card('暂无结果',title=clean(reply.title or 'Warframe 查询'))]
    # The command overview is one continuous image, including its follow-up hints.
    if command == 'help' or reply.title == 'Warframe 指令一览':
        overview=Card('',title=clean(reply.title or 'Warframe 指令一览'),footer=clean(display_footer(reply.footer)))
        overview.kind='help'
        overview.blocks=[block for card in output for block in (card.blocks or [card])]
        output=[overview]
    for i,card in enumerate(output,1):
        if len(output)>1:card.footer+=f'\n第 {i}/{len(output)} 张'
    return output


def native_blocks(lines,blocks):
    """Build high-density domain views from records, never from a remote bot reply."""
    from .core.formatters import countdown, tier_cn, mission_cn
    domain=getattr(lines,'domain','')
    records=getattr(lines,'records',[])
    replacement=None
    if domain=='alerts':
        from .core.formatters import countdown
        result=[]
        for desc,node,mission,level,rewards,expiry,faction in records:
            block=table(desc or '警报任务',['节点','任务类型','派系','剩余'],
                        [[node,mission,faction or '未知','剩'+countdown(expiry)]])
            block.footer=('警报：'+desc+' · ' if desc else '')+'敌人等级：'+(level or '未知')
            result.append(block)
            reward_rows=[]
            for reward in rewards.split('、'):
                reward=reward.strip()
                match=re.fullmatch(r'(.+?)\s*[×x]\s*([\d,]+)',reward)
                if match:name,quantity=translate(match[1].strip()),match[2]
                else:
                    cash=re.fullmatch(r'([\d,]+)\s*(?:现金|星币|credits)',reward,re.I)
                    name,quantity=('星币',cash[1]) if cash else (translate(reward),'—')
                from .display_icons import line_icon
                icon=line_icon(name+' ×'+quantity,'item_name') if quantity!='—' else line_icon(name,'item_name')
                reward_rows.append([(IconText(name,icon),'item_name'),(quantity,'wm_quantity')])
            result.append(Card('',title='任务奖励',columns=('奖励物品','数量'),rows=reward_rows))
        return result
    if domain=='arbitration_now':
        result=[]
        for record in records:
            node=record['node']+(f"（{record['system']}）" if record['system'] else '')
            block=table(record['label'],['地图 / 星球','任务类型','派系','评级'],
                        [[node,record['mission'],record['faction'] or '未知',record['rating'] or '未评级']])
            block.footer='北京时间：'+record['time']
            if record['label']=='当前仲裁':block.footer+='\n'+lines.meta['rating_detail']
            result.append(block)
        notes=[]
        if lines.meta.get('next_missing'):notes.append('下一小时：排期表已到末尾')
        if lines.meta.get('efficient_missing'):notes.append('下次高效：排期内暂无 S / A+ / A 场次')
        notes.extend(clean(line).lstrip('※ ') for line in lines if str(line).startswith(('※','★')))
        result[-1].footer+='\n'+'\n'.join(notes)
        return result
    if domain=='auctions':
        from .core.formatters import _riven_stat_cn, _riven_rolls
        rows=[]
        for auction in records:
            owner=auction.get('owner') or {};item=auction.get('item') or {}
            positive=[];negative=[]
            for at in item.get('attributes') or []:
                label=_riven_stat_cn(at.get('url_name',''),lines.meta.get('riven_type',''),lines.meta.get('group',''))
                value=abs(at.get('value',0))
                (positive if at.get('positive') else negative).append(f'{label} {value:g}')
            who=f"{owner.get('ingame_name','?')}\n等级 {item.get('mod_rank','?')} · {_riven_rolls(auction)} 洗\n信誉 {owner.get('reputation','—')}"
            price=str(auction['buyout_price'])+' 白金' if auction.get('buyout_price') else '竞价 · 起拍 '+str(auction.get('starting_price','?'))+' 白金'
            state={'ingame':'游戏中','online':'在线','offline':'离线'}.get(owner.get('status'),'离线')
            rows.append([(who,'wm_user'),(price+'\n'+state,'wm_price'),('\n'.join(positive) or '—','riven_stat'),('\n'.join(negative) or '无负面','riven_negative')])
        replacement=Card('',title='紫卡订单',columns=('卖家','价格','正面词条','负面词条'),rows=rows)
        match=lambda b:'一口价' in b.columns and '卖家' in b.columns
    elif domain=='market':
        who='买家' if lines.meta.get('buy') else '卖家'
        status={'online':'在线','ingame':'游戏中','offline':'离线'}
        rows=[]
        for r in records:
            u=r.get('user') or {}
            rows.append([u.get('ingame_name','?'),str(r.get('quantity',1)),str(r.get('platinum','?'))+' 白金',
                         str(r.get('mod_rank','—')),status.get(u.get('status'),'离线'),str(u.get('reputation','—'))])
        replacement=table('公开订单',[who,'数量','价格','等级','状态','信誉'],rows)
        match=lambda b:'价格' in b.columns and any(c in b.columns for c in ('卖家','买家'))
    elif domain=='fissures':
        rows=[]
        for r in records:
            rows.append([tier_cn(r.get('tier','')),mission_cn(r.get('missionType','')),r.get('node',''),
                         r.get('enemy') or r.get('faction',''),
                         ' / '.join(t for t in ('钢铁' if r.get('isHard') else '', '九重天' if r.get('isStorm') else '') if t),
                         countdown(r.get('expiry',''))])
        headers=['遗物等级','类型','节点','派系','标记','剩余']
        if not any(r[4] for r in rows):
            headers.pop(4)
            rows=[r[:4]+r[5:] for r in rows]
        replacement=table('裂缝任务',headers,rows)
        match=lambda b:'纪元' in b.columns
    elif domain=='relic':
        rows=[];prices=lines.meta.get('prices',{})
        for r in records:
            name=r.get('name','?');p=prices.get(name) or prices.get(re.sub(r'\s+','',name)) or {}
            rows.append([r.get('rarity',''),name,str(p.get('ducats','—')),str(p['plat'])+' 白金' if p.get('plat') is not None else '—',
                         str(p.get('dpp','—')),str(r['chance'])+'%' if r.get('chance') is not None else '—'])
        replacement=table('遗物奖励',['稀有度','奖励','杜卡德','白金','杜/白','概率'],rows)
        match=lambda b:'稀有度' in b.columns
    if replacement is not None:
        out=[];replaced=False
        for block in blocks:
            if match(block):
                if not replaced:
                    replacement.footer=block.footer;out.append(replacement);replaced=True
            else:out.append(block)
        if not replaced:out.append(replacement)
        return out
    return blocks
