"""One command registry for all game features. No extension namespaces."""
import re
from dataclasses import dataclass
from .client import QueryError
from .core.parser import ALIAS_TO_COMMAND, Parsed, parse

ADMIN_WORDS={'默认平台','平台','开启','关闭','状态','锚点'}
EXTRA_ALIASES={'玄骇':'xh','赤毒玄骸':'xh','wml':'xh','分析紫卡':'analysis','子卡倾向':'disposition',
    '夜灵电波':'nightwave','夜灵电台':'nightwave','最新新闻':'news','虚空商人':'voidtrader','物品wiki':'wiki'}
ROUTE_WORDS=set(ALIAS_TO_COMMAND)|ADMIN_WORDS|set(EXTRA_ALIASES)

@dataclass
class Request:
    key:str
    parsed:object=None
    admin_text:str=''


def route(text,platform='pc'):
    if text.lower().startswith('wf') and (len(text)==2 or text[2].isspace()):
        text=text[2:].strip() or '帮助'
    suffix=re.fullmatch(r'(.+?)\s+(洗卡推荐|紫卡推荐)(?:\s+(.*))?',text)
    if suffix:text=suffix[2]+' '+suffix[1]+(' '+suffix[3] if suffix[3] else '')
    head=text.split(maxsplit=1)[0].lower() if text else ''
    if head in ADMIN_WORDS and head!='状态':
        return Request('admin',admin_text='.'+text)
    parsed=parse(text,extra_commands=EXTRA_ALIASES)
    if parsed.command:
        if parsed.command in {'analysis','disposition'} and re.search(r'-(?:rank|dispo)=',text):
            from .commands import parse as parse_detail
            return Request('detail',parse_detail(text,platform,True))
        flags=list(parsed.unknown_modifiers)
        content=[]
        for token in parsed.content:
            if re.fullmatch(r'-rank=\d+',token):flags.append(token)
            elif parsed.command in {'wr','rm'} and re.fullmatch(r'-[A-Za-z_\u4e00-\u9fff]+',token):content.append('负'+token[1:])
            elif parsed.command=='analysis' and re.fullmatch(r'[^=]+=[+\-]?\d+(?:\.\d+)?%?',token):
                name,value=token.split('=',1)
                content.append(('负' if value.startswith('-') else '')+name+value.lstrip('+-').rstrip('%'))
            else:content.append(token)
        parsed.content=content
        # Preserve the original WM flags in the unified market grammar.
        for flag in flags:
            if flag=='-cn':raise QueryError('暂不支持国服，请使用国际服平台参数。')
            if flag=='-buy' and parsed.command=='wm':parsed.content.append('收购')
            elif flag=='-all' and parsed.command=='wr':parsed.content.append('离线')
            elif re.fullmatch(r'-rank=\d+',flag) and parsed.command in {'wm','wr'}:
                rank=int(flag.split('=')[1])
                if parsed.command=='wr' and not 0<=rank<=8:raise QueryError('紫卡等级范围为 0—8。')
                parsed.content.append(f'{rank}级' if parsed.command=='wm' else f'等级{rank}')
            elif flag in {'-ps4','-xb1','-swi'}:parsed.platform={'-ps4':'ps','-xb1':'xb','-swi':'sw'}[flag]
            else:raise QueryError(f'无法识别参数 {flag}，发送 帮助 查看用法。')
        parsed.unknown_modifiers=[]
        return Request(parsed.command,parsed)
    # Older convenience commands (single-planet timers, item detail, sisters)
    # are native service handlers, not another plugin.
    from .commands import parse as parse_detail
    legacy=parse_detail(text,platform,True)
    return Request('detail',legacy) if legacy else None
