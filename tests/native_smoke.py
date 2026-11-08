"""Isolated AstrBot host stub for the transplanted engine and root adapter."""
import asyncio
import importlib.util
import json
import logging
import os
import shutil
from pathlib import Path
import sys
import tempfile
import types
from unittest.mock import AsyncMock

ROOT=Path(__file__).resolve().parents[1]
for name in ['astrbot','astrbot.api','astrbot.api.event','astrbot.api.star','astrbot.api.message_components']:
    sys.modules[name]=types.ModuleType(name)
api=sys.modules['astrbot.api'];api.AstrBotConfig=dict;api.logger=logging.getLogger('smoke')
event_mod=sys.modules['astrbot.api.event'];star=sys.modules['astrbot.api.star'];components=sys.modules['astrbot.api.message_components']
class Star:
    def __init__(self,context):self.context=context
class Chain:
    def __init__(self):self.chain=[]
    def message(self,text):self.chain.append(text);return self
class Image:
    @classmethod
    def fromFileSystem(cls,path):return ('image',path)
class Plain:pass
class At:
    def __init__(self,qq):self.qq=qq
components.Image=Image;components.Plain=Plain;components.At=At
star.Star=Star;star.Context=object;star.register=lambda *a,**k:lambda c:c
star.StarTools=types.SimpleNamespace(get_data_dir=lambda name:Path(TEMP)/name)
event_mod.AstrMessageEvent=object;event_mod.MessageChain=Chain
event_mod.filter=types.SimpleNamespace(regex=lambda *a,**k:lambda f:f)
spec=importlib.util.spec_from_file_location('wf_smoke',ROOT/'__init__.py',submodule_search_locations=[str(ROOT)])
package=importlib.util.module_from_spec(spec);sys.modules['wf_smoke']=package;spec.loader.exec_module(package)

class Event:
    unified_msg_origin='test:GroupMessage:123'
    message_str='遗物 古纪A1'
    def get_platform_id(self):return 'test'
    def get_sender_id(self):return '1234'
    def get_platform_name(self):return 'aiocqhttp'
    def get_messages(self):return []
    def get_sender_name(self):return 'Tester'
    def stop_event(self):self.stopped=True
    def image_result(self,path):return ('image',path)
    def is_admin(self):return False

async def run():
    from wf_smoke.main import WarframePlugin
    from wf_smoke.runtime import GameRuntime
    from wf_smoke.settings import GameConfig
    from wf_smoke.routing import route
    from wf_smoke.core.commands import Reply
    from wf_smoke.core.parser import ALIAS_TO_COMMAND
    from wf_smoke.core import paths
    context=types.SimpleNamespace(send_message=AsyncMock())
    plugin=WarframePlugin(context,{'cooldown':0})
    runtime=GameRuntime(plugin,GameConfig(plugin.config));plugin.runtime=runtime
    assert paths.run_dir()==plugin.themes.directory/'game'
    event=Event();original=dict(runtime._routes)
    assert len(original)==58,len(original)
    for command,handler in original.items():
        assert callable(handler),command
        alias=next((a for a,c in ALIAS_TO_COMMAND.items() if c==command),None)
        if alias is None:continue # status is an administrative route
        stub=AsyncMock(return_value=Reply(title='迁移验证',lines=['◆ 状态：测试结果']))
        runtime._routes[command]=stub
        cards=await plugin.query(route(alias),event)
        result=[await plugin.image_reply(event,c,'u') for c in cards]
        assert stub.await_count==1,(command,alias)
        assert result and all(r[0]=='image' and Path(r[1]).exists() for r in result),command
        runtime._routes[command]=handler
    # The root handler must actually delegate (not send None to its old service).
    runtime._routes['relic']=AsyncMock(return_value=Reply(title='遗物测试',lines=['测试']))
    result=[r async for r in plugin.on_message(event)]
    assert runtime._routes['relic'].await_count==1
    assert result[0][0]=='image'
    # No external requests: exercise the real local damage calculator and help/OCR guidance.
    for cmd in ['帮助','武器融合 25 40','伤害 绝路','识卡','蹲']:
        cards=await plugin.query(route(cmd),event)
        result=[await plugin.image_reply(event,c,'u') for c in cards]
        assert result and all(r[0]=='image' for r in result),cmd
        if cmd=='帮助':
            assert len(result)==1,'Command overview must be a single image'
            assert len(cards[0].blocks)>5,'All command categories must be retained'
            if os.getenv('WF_SMOKE_PREVIEWS'):
                shutil.copyfile(result[0][1],ROOT/'previews/native-help.png')
        if os.getenv('WF_SMOKE_PREVIEWS') and cmd=='伤害 绝路':
            shutil.copyfile(result[0][1],ROOT/'previews/native-damage.png')
    from wf_smoke.core.parser import parse as parse_ext
    reply=await original['damage'](parse_ext('伤害 绝路'),event,'pc')
    assert reply.title=='伤害计算'
    assert any('DPS' in line for line in reply.lines),reply.lines[:5]
    assert not any('计算出错' in line for line in reply.lines)
    # Real market resolution, filtering and typed view generation, with only HTTP data stubbed.
    from unittest.mock import patch
    from wf_smoke.core.parser import parse_wm
    catalog=[{'url_name':'mesa_prime_set','zh':'Mesa Prime 一套','en':'Mesa Prime Set','tags':['set'],
              'i18n':{'en':{'thumb':'items/images/example.png'}}},
             {'url_name':'mesa_prime_systems_blueprint','zh':'Mesa Prime 系统蓝图','en':'Mesa Prime Systems Blueprint','tags':[]}]
    orders=[{'order_type':'sell','platinum':25,'quantity':2,'visible':True,'user':{'ingame_name':'Fixture_Tenno','status':'ingame','reputation':8}}]
    with patch.object(runtime.client,'wm_items',AsyncMock(return_value=catalog)),patch.object(runtime.client,'wm_orders',AsyncMock(return_value=(orders,{}))),patch.object(runtime.client,'wm_set_parts',AsyncMock(return_value=[catalog[1]])):
        for query,slug in [('wm measprime','mesa_prime_set'),('wm 女枪系统','mesa_prime_systems_blueprint')]:
            parsed=route(query).parsed
            before=runtime.client.wm_orders.await_count
            response=await original['wm'](parsed,event,'pc')
            assert getattr(response.lines,'domain',None)=='market',(query,response)
            assert response.lines.records[0]['user']['ingame_name']=='Fixture_Tenno'
            assert runtime.client.wm_orders.await_args_list[before].args[0]==slug
    # Group administration still checks authorization; no direct service bypass.
    denied=await runtime._handle_admin(event,'.开启 推送')
    assert '管理员' in denied.raw_text
    assert not runtime.groups.get(event.unified_msg_origin).get('push',False)
    if os.getenv('WF_SMOKE_LIVE'):
        for command in json.loads(os.getenv('WF_SMOKE_QUERIES','["遗物 古纪A1","赏金","xh 布拉玛"]')):
            parsed=parse_ext(command)
            try:
                reply=await original[parsed.command](parsed,event,'pc')
                assert reply.title and reply.lines,(command,reply.raw_text)
                from wf_smoke.presentation import present
                for card in present(reply,parsed.command):
                    output=await plugin.image_reply(event,card,'u')
                    assert Path(output[1]).exists()
                print('LIVE',command,reply.title,len(reply.lines))
            except Exception as exc:
                raise AssertionError((command,type(exc).__name__)) from exc
    # Paging and startup warm-up use the native runtime class, not the removed plugin.
    actions=runtime._reply_actions(Reply('订单（第2/3页）'),route('wm 膛线 -2 -ps').parsed)
    assert any(a.label=='上一页' for a in actions) and any(a.label=='下一页' for a in actions)
    for action in actions:
        if action.mode!='copy':assert route('wf '+action.send).key=='wm'
    with patch.object(runtime,'_refresh_from_community',AsyncMock(return_value={'ok':True})),patch.object(runtime,'_refresh_static_community',AsyncMock(return_value={'ok':True})),patch.object(runtime.client,'wm_items',AsyncMock(return_value=catalog)),patch.object(runtime.client,'wm_riven_weapons',AsyncMock(return_value=[{'url_name':'torid'}])):
        await runtime._boot_warm()
        assert len(runtime._background_status['boot']['checks'])==4
    # Start and close the real lifecycle with network loops parked locally.
    async def parked(*args,**kwargs):
        await asyncio.Event().wait()
    for name in ('_rank_autoloop','_valence_autoloop','_revision_autoloop','_community_autoloop','_boot_warm'):
        setattr(runtime,name,parked)
    runtime._warmup=lambda:None
    runtime.push.start=lambda:None
    await runtime.initialize()
    await asyncio.sleep(0)
    await plugin.terminate()
    for name in ('_auto_task','_valence_task','_revision_task','_community_task','_boot_task','_warm_task'):
        task=getattr(runtime,name,None)
        assert task is None or task.done(),name
    assert context.send_message.await_count==0
    print('58 routes attached; dispatch, real local handlers, image rendering and cleanup passed')

with tempfile.TemporaryDirectory(prefix='wf-sdjk-smoke-') as TEMP:
    asyncio.run(run())
