"""Single AstrBot entrypoint for the integrated Warframe application."""
import asyncio
import json
import time
from dataclasses import replace
from collections import OrderedDict

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, StarTools, register
from .cards import Card
from .client import ApiClient, QueryError
from .commands import normalize_prefix
from .routing import route
from .settings import GameConfig
from .presentation import present
from .item_art import ArtworkCache
from .service import WarframeService
from .renderer import CardRenderer
from .theme import ThemeStore, theme_from

@register('astrbot_plugin_warframe', 'Amy', 'Warframe 查询、计算、OCR 与订阅', '0.7.21')
class WarframePlugin(Star):
    def __init__(self,context:Context,config:AstrBotConfig):
        super().__init__(context)
        self.context=context;self.config=config
        self.client=ApiClient(config.get('timeout',20))
        self.service=WarframeService(self.client,config.get('page_size',10))
        self.users=OrderedDict()
        directory=StarTools.get_data_dir('astrbot_plugin_warframe')
        self.themes=ThemeStore(directory)
        self.renderer=CardRenderer(directory/'images')
        self.artwork_cache=ArtworkCache(directory/'item_art')
        self.render_lock=asyncio.Lock();self.runtime_lock=asyncio.Lock();self.runtime=None

    async def initialize(self):
        await self.get_runtime()

    async def get_runtime(self):
        async with self.runtime_lock:
            if self.runtime is None:
                from .runtime import GameRuntime
                runtime=GameRuntime(self,GameConfig(self.config))
                try:await runtime.initialize()
                except BaseException:
                    await runtime.terminate()
                    raise
                self.runtime=runtime
            return self.runtime

    def style_config(self):
        return self.runtime.renderer.style_config() if self.runtime else self.config

    async def image_reply(self,event,card,user):
        theme=theme_from(self.style_config(),self.themes.get(user))
        from .weapon_art import decorate
        decorate(card)
        if isinstance(card,Card) and card.artwork[0] and not card.artwork_path:
            card.artwork_path=await self.artwork_cache.get(card.artwork[0])
            if card.artwork_path and card.artwork[1]:card.artwork_overlay_path=await self.artwork_cache.get(card.artwork[1])
        async with self.render_lock:
            path=await asyncio.to_thread(self.renderer.render,card,theme)
            cutoff=time.time()-86400
            for old in self.renderer.output.glob('*.png'):
                try:
                    if old.stat().st_mtime<cutoff:old.unlink(missing_ok=True)
                except FileNotFoundError:pass
        return event.image_result(str(path))

    async def query(self,request,event):
        """Invoke one native domain handler; all handlers return application data."""
        if request.key=='detail':return [await self.service.run(request.parsed)]
        runtime=await self.get_runtime()
        from .core.api_client import WarframeAPIError,public_error_text
        from .core.commands import Reply
        try:
            if request.key=='admin':reply=await runtime._handle_admin(event,request.admin_text)
            else:
                parsed=request.parsed
                platform=parsed.platform or runtime.groups.platform(event.unified_msg_origin)
                reply=await runtime._routes[request.key](parsed,event,platform)
                if reply is not None:
                    reply.actions=runtime._reply_actions(reply,parsed)
                    reply.actions=[replace(a,send='wf '+a.send.lstrip('.'))
                                   if a.mode!='copy' and not a.send.lower().startswith('wf ')
                                   else a for a in reply.actions]
        except WarframeAPIError as exc:
            reply=Reply(title='数据源暂不可用',raw_text=public_error_text(exc))
        return present(reply,request.key) if reply is not None else []

    @filter.regex(r'(?s)^.+$')
    async def on_message(self,event:AstrMessageEvent):
        user=json.dumps([event.get_platform_id(),event.get_sender_id()],ensure_ascii=False)
        try:
            personal=self.themes.get(user)
            prefixes=personal.get('command_prefixes',self.config.get('command_prefixes',['','/','.']))
            normalized=normalize_prefix(event.message_str,prefixes,self.config.get('bare_commands',True) or 'command_prefixes' in personal)
            if normalized is None:return
            words=normalized.split()
            control=len(words)>=2 and words[0].lower()=='wf' and words[1] in {'主题','配色','字号','背景','前缀'}
            request=None if control else route(normalized,self.config.get('default_platform','pc'))
            if not control and request is None:return
            event.stop_event()
            now=time.monotonic();cooldown=max(0,int(self.config.get('cooldown',2)))
            if now-self.users.get(user,-1e9)<cooldown:raise QueryError('查询太快了，请稍后再试。')
            self.users[user]=now;self.users.move_to_end(user)
            while len(self.users)>2048:self.users.popitem(last=False)
            cards=[self.themes.handle(user,normalized,prefixes)] if control else await self.query(request,event)
            for card in cards:yield await self.image_reply(event,card,user)
        except QueryError as exc:
            event.stop_event()
            yield await self.image_reply(event,Card(str(exc),title='Warframe 助手 · 操作提示',columns=('提示',),rows=[[(str(exc),'riven_negative')]]),user)
        except Exception:
            logger.exception('Warframe query or image rendering failed')
            event.stop_event()
            card=Card('',title='Warframe 助手 · 服务异常',columns=('提示',),rows=[[('查询失败，请稍后重试或联系管理员查看日志。','riven_negative')]])
            async with self.render_lock:path=await asyncio.to_thread(self.renderer.render,card,theme_from({}))
            yield event.image_result(str(path))

    async def send_notification(self,umo,text,at,platform):
        from astrbot.api.event import MessageChain
        from astrbot.api.message_components import Image,At
        from .core.push import at_targets
        from .core.commands import Reply
        for card in present(Reply(title='Warframe · 订阅提醒',lines=text.splitlines()),'notification'):
            async with self.render_lock:path=await asyncio.to_thread(self.renderer.render,card,theme_from(self.style_config()))
            chain=MessageChain();chain.chain=[At(qq=q) for q in at_targets(platform,at)]
            chain.chain.append(Image.fromFileSystem(str(path)))
            if await self.context.send_message(umo,chain) is False:raise RuntimeError('订阅图片发送失败')

    async def terminate(self):
        if self.runtime:await self.runtime.terminate()
        await self.client.close()
