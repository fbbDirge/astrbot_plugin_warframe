import unittest
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
import test_core
from wf_plugin.core.riven_reply import image_event
from wf_plugin.core.commands.vision import VisionCommands
from wf_plugin.core.commands.riven import RivenCommands
Image=type('Image',(),{})
Reply=type('Reply',(),{})
def event(chain,**kw):return NS(message_obj=NS(message=chain),**kw)
class QuotedImageTests(unittest.IsolatedAsyncioTestCase):
 async def test_embedded_quote_and_current_priority(self):
  pic=Image();q=Reply();q.chain=[pic];q.id='10'
  e=await image_event(event([q]));self.assertTrue(VisionCommands._event_has_image(e));self.assertIs(e.message_obj.message[0],pic)
  own=Image();e=await image_event(event([q,own]));self.assertIs(e.message_obj.message[0],own)
 async def test_onebot_fetch_and_scope(self):
  q=Reply();q.chain=[];q.id='10'
  response={'group_id':42,'message':[{'type':'image','data':{'url':'https://example.com/card.png'}}]}
  bot=NS(call_action=AsyncMock(return_value=response))
  e=event([q],bot=bot,get_group_id=lambda:'42')
  out=await image_event(e);self.assertTrue(VisionCommands._event_has_image(out))
  bot.call_action.assert_awaited_once_with(action='get_msg',message_id='10')
  response['group_id']=43;self.assertIs(await image_event(e),e)
 async def test_failure_and_no_recursive_lookup(self):
  q=Reply();q.chain=[];q.id='10';e=event([q],bot=NS(call_action=AsyncMock(side_effect=RuntimeError('missing'))))
  self.assertIs(await image_event(e),e)
  q.chain=[q];e=event([q]);self.assertIs(await image_event(e),e)
 async def test_analysis_accepts_quoted_image_before_gate(self):
  q=Reply();q.chain=[Image()];q.id='10'
  marker=object()
  handler=NS(_riven_text_input=lambda _:NS(weapon='',positive=[],negative=[]),
   _event_has_image=VisionCommands._event_has_image,_vision_last=lambda _: {},
   _vision_gate=lambda *a,**k:(marker,'sender'))
  self.assertIs(await RivenCommands._h_riven_analysis(handler,NS(),event([q]),'pc'),marker)
