import copy
import unittest
from urllib.parse import urlparse,parse_qs
from test_core import parse,QueryError
from wf_plugin.riven_market import split_query,parse_filters,search_url,filter_listings,format_stat,RivenMarketService

WEAPONS=[{'slug':'torid','rivenType':'rifle','i18n':{'zh-hans':{'name':'托里德'},'en':{'name':'Torid'}}}, {'slug':'boar','i18n':{'zh-hans':{'name':'野猪'}}},{'slug':'dual_ichor','i18n':{'en':{'name':'Dual Ichor'}}}]
ATTRS=[{'slug':s,'unit':'percent','i18n':{'zh-hans':{'name':n}}} for s,n in [('critical_chance','暴击率'),('critical_damage','暴击伤害'),('multishot','多重射击'),('zoom','变焦'),('recoil','武器后坐力')]]
ATTRS.append({'slug':'viral','positiveOnly':True,'i18n':{'zh-hans':{'name':'病毒伤害'}}})

def auction(ident=1,price=100,**kwargs):
    row={'id':f'{ident:024x}','visible':True,'closed':False,'private':False,'platform':'pc','buyout_price':price,'starting_price':1,'owner':{'ingame_name':'Tenno','status':'ingame','platform':'pc'},'item':{'type':'riven','weapon_url_name':'torid','mod_rank':8,'re_rolls':2,'mastery_level':10,'attributes':[{'url_name':'critical_chance','positive':True,'value':150},{'url_name':'multishot','positive':True,'value':100},{'url_name':'zoom','positive':False,'value':-40}]}}
    row.update(kwargs);return row

class SearchTests(unittest.TestCase):
    def test_command_prefixes_and_options(self):
        for prefix in ['','/','.','wf ']:
            c=parse(prefix+'wmr 托里德 暴击率 多重 -变焦 3+1 -rank=8 -all -2 -ps')
            self.assertEqual(c.name,'wmr');self.assertEqual(c.platform,'ps4');self.assertEqual(c.page,2)
            self.assertTrue(c.include_offline);self.assertEqual(c.riven_layout,'3+1')
        for text in ['wmr','wmr 托里德 -rank=9','wmr 托里德 -buy']:
            with self.assertRaises(QueryError):parse(text)

    def test_weapon_and_filter_boundaries(self):
        for text,slug,filters in [('托里德 暴击率','torid','暴击率'),('Dual Ichor 暴伤','dual_ichor','暴伤'),('野猪p 暴击率','boar','暴击率')]:
            w,tail=split_query(text,WEAPONS);self.assertEqual(w[0]['slug'],slug);self.assertEqual(tail,filters)
        w,tail=split_query('托里德 不存在的词条',WEAPONS)
        with self.assertRaises(QueryError):parse_filters(tail,ATTRS,'rifle')

    def test_single_multiple_negative_and_alias(self):
        self.assertEqual(parse_filters('暴击率',ATTRS,'rifle'),(['critical_chance'],[]))
        self.assertEqual(parse_filters('双暴 多重 -变焦',ATTRS,'rifle'),(['critical_chance','critical_damage','multishot'],['zoom']))
        p,n=parse_filters('+暴击率 多重 负变焦',ATTRS,'rifle')
        params=parse_qs(urlparse(search_url('torid',p,n)).query)
        self.assertEqual(params['positive_stats'],['critical_chance,multishot'])
        self.assertEqual(params['negative_stats'],['zoom'])
        self.assertEqual(params['buyout_policy'],['direct'])

    def test_invalid_filters_never_silently_drop(self):
        for text,layout in [('暴击率 -暴击率',None),('暴击率 暴击率',None),('-病毒',None),('未知',None),('-变焦 -多重',None),('双暴 多重','2+0'),('-变焦','3+0')]:
            with self.subTest(text=text),self.assertRaises(QueryError):parse_filters(text,ATTRS,'rifle',layout)

    def test_local_and_validation_and_price_sort(self):
        rows=[auction(1,200),auction(2,100),auction(3,1,closed=True),auction(4,1,visible=False),auction(5,1,private=True),auction(6,None),auction(7,1,platform='ps4')]
        offline=auction(8,50);offline['owner']['status']='offline';rows.append(offline)
        wrong=auction(9,1);wrong['item']['attributes']=wrong['item']['attributes'][:1];rows.append(wrong)
        c=parse('wmr 托里德 暴击率 多重 -变焦')
        result=filter_listings(rows,'torid',['critical_chance','multishot'],['zoom'],c)
        self.assertEqual([x['buyout_price'] for x in result],[100,200])
        c.include_offline=True
        self.assertEqual([x['buyout_price'] for x in filter_listings(rows,'torid',['critical_chance','multishot'],['zoom'],c)],[50,100,200])
        c.riven_layout='3+1';self.assertEqual(filter_listings(rows,'torid',[],[],c),[])

    def test_recoil_uses_polarity_not_sign(self):
        row=auction();row['item']['attributes'].append({'url_name':'recoil','positive':True,'value':-80})
        c=parse('wmr 托里德 后坐力')
        self.assertEqual(len(filter_listings([row],'torid',['recoil'],[],c)),1)
        self.assertIn('正',format_stat(row['item']['attributes'][-1],{a['slug']:a for a in ATTRS}))
        self.assertIn('-80%',format_stat(row['item']['attributes'][-1],{a['slug']:a for a in ATTRS}))

class ServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_paging_and_no_match(self):
        class Client:
            async def get(self,url,**kwargs):
                if url.endswith('/attributes'):return ATTRS
                if url.endswith('/weapons'):return WEAPONS
                return {'auctions':[auction(i,100+i) for i in range(1,8)]}
        service=RivenMarketService(Client())
        card=await service.run(parse('wmr 托里德 暴击率 多重 -变焦 -2'))
        self.assertEqual(len(card.rows),2);self.assertIn('第 2/2 页',card.footer)
        self.assertIn('不代表全部',card.footer);self.assertIn('https://warframe.market/auction/',card.footer)
        text=await service.run(parse('wmr 托里德 暴伤'))
        self.assertIn('无符合条件',text)
        with self.assertRaises(QueryError):await service.run(parse('wmr 托里德 -3'))

class ClientEnvelopeTests(unittest.IsolatedAsyncioTestCase):
    async def test_v1_payload_and_cache_reuse(self):
        from wf_plugin.client import ApiClient
        class Response:
            status=200
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
            async def json(self):return {'payload':{'auctions':[auction()]}}
        class Session:
            closed=False
            count=0
            def get(self,*args,**kwargs):
                self.count+=1
                return Response()
            async def close(self):self.closed=True
        client=ApiClient();client.session=Session()
        url=search_url('torid',['critical_chance'],[])
        first=await client.get(url)
        second=await client.get(url)
        self.assertEqual(first,second);self.assertIn('auctions',first)
        self.assertEqual(client.session.count,1)
        await client.close()
