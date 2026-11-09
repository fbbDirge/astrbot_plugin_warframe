import copy,json,tempfile,time,unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
import test_core
from wf_plugin.core import paths
from wf_plugin.core.reroll_wfsim import recommend,report,cache_path,call
from wf_plugin.presentation import present
from wf_plugin.renderer import CardRenderer
from wf_plugin.theme import theme_from

RESULT={'ok':True,'weapon':'torid','groups':[{'ruler':'Standard Single Target › Lv 9999 SP › 100% headshots, aiming › Standard conditions','ruler_id':'standard_single_target','mode':'cycle','riven_free':{'score':'10'},'rivens':[{'rank':1,'stat_ids':{'bonuses':['critical_damage','damage','weak_point_damage'],'malus':'status_duration'},'gain':.35,'mods':['Serration'],'measured_at':'2026-11-09T00:00Z'}]}]}
class WFSimTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old=paths._RUN;paths.set_run_dir(self.tmp.name)
  self.client=SimpleNamespace(resolve_riven_weapon=AsyncMock(return_value={'en':'Torid','zh':'托里德','riven_type':'rifle'}),wm_riven_auctions=AsyncMock())
 async def asyncTearDown(self):
  paths.set_run_dir(self.old);self.tmp.cleanup()
 async def test_live_cache_stale_and_render(self):
  mock=AsyncMock(side_effect=[{'rows':[{'id':'torid','name':'Torid'}]},RESULT])
  with patch('wf_plugin.core.reroll_wfsim.call',mock):
   r=await recommend(self.client,'托里德');self.assertIn('+35.0%',''.join(r.lines));self.assertNotIn('白金',''.join(r.lines));self.assertIn('伤害',''.join(r.lines));self.assertNotIn('▲damage',''.join(r.lines));self.assertIn('膛线',''.join(r.lines))
   await recommend(self.client,'托里德');self.assertEqual(mock.await_count,2)
  self.client.wm_riven_auctions.assert_not_awaited()
  p=cache_path('托里德','standard_single_target');data=json.loads(p.read_text());data['sampled_at']-=86400;p.write_text(json.dumps(data))
  with patch('wf_plugin.core.reroll_wfsim.call',AsyncMock(side_effect=RuntimeError('offline'))):
   r=await recommend(self.client,'托里德');self.assertIn('非实时',''.join(r.lines));self.assertIn('北京时间',''.join(r.lines))
  for card in present(r,'reroll'):
   self.assertTrue(CardRenderer(self.tmp.name).render(card,theme_from({})).is_file())
 async def test_no_guessing_variant_and_scenario(self):
  with patch('wf_plugin.core.reroll_wfsim.call',AsyncMock(return_value={'rows':[{'id':'torid_prime','name':'Torid Prime'},{'id':'other','name':'Other'}]})):
   r=await recommend(self.client,'托里德');self.assertIn('请指定武器',r.title)
  with patch('wf_plugin.core.reroll_wfsim.call',AsyncMock(side_effect=[{'rows':[{'id':'torid','name':'Torid'}]},dict(RESULT,groups=[])])) as m:
   r=await recommend(self.client,'托里德 群怪 刷新');self.assertIn('暂无推荐',''.join(r.lines));self.assertEqual(m.call_args.args[2]['ruler'],'standard_multi_target')
 def test_missing_baseline_no_fabricated_gain(self):
  d=copy.deepcopy(RESULT);d['groups'][0]['riven_free']=None
  r=report({'result':d,'query':'托里德','sampled_at':time.time()})
  self.assertNotIn('+35.0%',''.join(r.lines));self.assertIn('无同场景基准',''.join(r.lines))
 async def test_mcp_errors_and_auth(self):
  import httpx
  response=httpx.Response(200,json={'result':{'isError':True,'structuredContent':{'ok':False}}},request=httpx.Request('POST','https://example.com'))
  c=SimpleNamespace(http=SimpleNamespace(post=AsyncMock(return_value=response)))
  with patch('wf_plugin.core.reroll_wfsim._LAST',0):
   with self.assertRaises(ValueError):await call(c,'builder_rivens_read',{'weapon':'torid'},'example-key')
  self.assertEqual(c.http.post.call_args.kwargs['headers']['Authorization'],'Bearer example-key')

class TopFiveTests(unittest.TestCase):
 def test_five_per_mode_without_summary(self):
  result=copy.deepcopy(RESULT)
  base=result['groups'][0]
  base['rivens']=[dict(copy.deepcopy(base['rivens'][0]),rank=i+1) for i in range(8)]
  other=copy.deepcopy(base);other['mode']='base';other['rivens']=other['rivens'][:2]
  result['groups'].append(other)
  text='\n'.join(report({'result':result,'query':'托里德','sampled_at':time.time()}).lines)
  self.assertEqual(text.count('◆ 优选组合 '),7)
  self.assertIn('◆ 优选组合 5',text);self.assertNotIn('◆ 优选组合 6',text)
  self.assertIn('+35.0%',text);self.assertIn('膛线',text)
  self.assertNotIn('正面推荐',text);self.assertNotIn('负面慎选',text);self.assertNotIn('前 20',text)
