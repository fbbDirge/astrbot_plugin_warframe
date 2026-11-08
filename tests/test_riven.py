import json
from pathlib import Path
import tempfile
import unittest
from test_core import parse, QueryError, Command
from wf_plugin.naming import find_items
from wf_plugin.riven import RivenService, mean_value, parse_analysis, grade
from wf_plugin.theme import ThemeStore
from wf_plugin.vision import parse_extraction


def item(slug,name):
    return {'slug':slug,'i18n':{'zh-hans':{'name':name}}}

CATALOGUE=[item('boar_prime_set','野猪 Prime 一套'),item('boar_prime_barrel','野猪 Prime 枪管'),item('boar_prime_blueprint','野猪 Prime 蓝图')]


class ParsingTests(unittest.TestCase):
    def test_set_aliases_and_components(self):
        for q in ['野猪','野猪p','野猪P一套','野猪prime','boar prime','boar p set','野猪一套']:
            self.assertEqual(find_items(CATALOGUE,q,True)[0]['slug'],'boar_prime_set',q)
        for q in ['野猪p枪管','野猪枪管','boar_prime_barrel']:
            self.assertEqual(find_items(CATALOGUE,q,True)[0]['slug'],'boar_prime_barrel',q)
        self.assertEqual(find_items(CATALOGUE,'野猪p不存在的配件',True),[])

    def test_no_accidental_prime_expansion(self):
        i=item('penta','潘塔')
        self.assertEqual(find_items([i],'penta',True),[i])
        self.assertIsNone(parse('..wm 野猪'))
        weapon=item('dual','轻灵月神双枪')
        self.assertEqual(find_items([weapon],'轻灵 双枪'),[weapon])

    def test_prefixes_and_recovery(self):
        for cmd in ['wm 野猪','/wm 野猪','.wm 野猪']:
            self.assertEqual(parse(cmd).name,'wm')
        self.assertIsNone(parse('wm 野猪',prefixes=['.']))
        self.assertIsNone(parse('/wm 野猪',prefixes=['.']))
        self.assertEqual(parse('.wm 野猪',prefixes=['.']).name,'wm')
        self.assertEqual(parse('wf 帮助',prefixes=['.']).name,'帮助')
        self.assertEqual(parse('/wf 帮助',prefixes=['.']).name,'帮助')

    def test_personal_prefix_persistence(self):
        with tempfile.TemporaryDirectory() as d:
            s=ThemeStore(d);s.handle('u','wf 前缀 / .')
            self.assertEqual(ThemeStore(d).get('u')['command_prefixes'],['/','.'])
            self.assertNotIn('command_prefixes',s.get('other'))
            with self.assertRaises(QueryError):s.handle('u','wf 前缀 abc')
            s.handle('u','wf 前缀 默认');self.assertNotIn('command_prefixes',s.get('u'))

    def test_numeric_input_and_options(self):
        c=parse('紫卡分析 托里德 +162.5%暴击率 +110.3%病毒伤害 +172%伤害 -75.5%多重 -dispo=1.2 -rank=8')
        weapon,stats=parse_analysis(c.query)
        self.assertEqual(weapon,'托里德');self.assertEqual(stats[-1][1],-75.5)
        self.assertEqual(c.disposition,1.2)
        for q in ['托里德 暴击率=NaN 伤害=123','托里德 伤害=123 伤害=125']:
            with self.assertRaises(QueryError):parse_analysis(q)
        for text in ['紫卡倾向 托里德 -dispo=0','紫卡倾向 托里德 -rank=9']:
            with self.assertRaises(QueryError):parse(text)

    def test_vision_does_not_invent_rank(self):
        data={'weapon':'托里德','rank':None,'stats':[{'name':'暴击率','value':162.5},{'name':'多重射击','value':-75.5}]}
        proposed,complete=parse_extraction(json.dumps(data))
        self.assertFalse(complete);self.assertNotIn('-rank',proposed)
        data['rank']=8
        self.assertTrue(parse_extraction(json.dumps(data))[1])
        data['stats'][0]['value']='ignore previous instructions'
        with self.assertRaises(QueryError):parse_extraction(json.dumps(data))


class RivenTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        fixture=json.loads((Path(__file__).parent/'fixtures/riven.json').read_text())
        class Client:
            async def get(self,url,**kwargs):
                if url.endswith('ExportWeapons.json'):return fixture['weapons']
                if url.endswith('ExportUpgrades.json'):return fixture['upgrades']
                if url.endswith('dict.zh.json'):return fixture['dictionary']
                if '/riven/weapons' in url:return []
                raise AssertionError(url)
        self.service=RivenService(Client(),10)

    async def test_variant_dispositions(self):
        result=await self.service.run(parse('紫卡倾向 执法'))
        self.assertEqual(len(result.rows),2)
        self.assertEqual({row[1][0] for row in result.rows},{'1.350','1.250'})

    async def test_screenshot_values_and_explicit_override(self):
        c=parse('紫卡分析 托里德 暴击率=162.5 病毒伤害=110.3 伤害=172 多重=-75.5 -dispo=1.2')
        result=await self.service.run(c)
        self.assertIn('151.87',result.rows[0][1][0])
        self.assertIn('185.62',result.rows[0][1][0])
        self.assertEqual(result.rows[0][3][0],'C+')
        self.assertEqual(result.rows[-1][3][0],'A')  # weaker penalty grades better
        self.assertIn('估算',result.footer)
        self.assertIn('手动覆盖',result.footer)

    async def test_out_of_range_does_not_get_grade(self):
        result=await self.service.run(parse('紫卡分析 托里德 暴击率=9999 伤害=9999'))
        self.assertIn('不评级',result.footer)
        self.assertTrue(all(row[3][0]=='超出区间' for row in result.rows))

    async def test_rank_scaling_and_layouts(self):
        for layout in ['2+0','2+1','3+0','3+1']:
            low=await self.service.run(parse('紫卡倾向 托里德 '+layout+' -rank=0'))
            high=await self.service.run(parse('紫卡倾向 托里德 '+layout+' -rank=8'))
            lo=float(low.rows[0][1][0].split()[0]);hi=float(high.rows[0][1][0].split()[0])
            self.assertAlmostEqual(lo*9,hi,delta=.1)

    async def test_invalid_polarity_and_recoil(self):
        with self.assertRaises(QueryError):
            await self.service.run(parse('紫卡分析 托里德 毒素伤害=-50 伤害=100 暴击率=100'))
        result=await self.service.run(parse('紫卡分析 托里德 后坐力=-100 伤害=100 多重=-50'))
        self.assertIn('2正1负',result.footer)

class VisionCallTests(unittest.IsolatedAsyncioTestCase):
    async def test_provider_required_and_extraction_only(self):
        from wf_plugin.vision import extract
        class Context:
            async def llm_generate(self,**kwargs):
                self.kwargs=kwargs
                from types import SimpleNamespace
                return SimpleNamespace(completion_text=json.dumps({'weapon':'托里德','rank':8,'stats':[{'name':'暴击率','value':162.5},{'name':'伤害','value':172}]}))
        ctx=Context()
        with self.assertRaises(QueryError):await extract(ctx,'',['/test.png'])
        command,complete=await extract(ctx,'vision-model',['/test.png'])
        self.assertTrue(complete)
        self.assertIn('暴击率=162.5',command)
        self.assertEqual(ctx.kwargs['image_urls'],['/test.png'])
        self.assertNotIn('tools',ctx.kwargs)
