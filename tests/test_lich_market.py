import copy
import unittest
from test_core import parse, QueryError
from wf_plugin.lich_market import filters, select, match_weapons, LichMarketService

WEAPONS=[{'slug':'kuva_bramma','i18n':{'zh-hans':{'name':'赤毒·布拉玛'},'en':{'name':'Kuva Bramma'}}}]
ORDER={'id':'a'*24,'visible':True,'closed':False,'private':False,'platform':'pc','is_direct_sell':True,'buyout_price':100,'owner':{'status':'ingame','ingame_name':'Tester'},'item':{'type':'lich','weapon_url_name':'kuva_bramma','damage':55,'element':'toxin','having_ephemera':True}}

class LichTests(unittest.TestCase):
    def test_parser_and_filters(self):
        for prefix in ['','/','.']:
            c=parse(prefix+'玄骇 布拉玛 毒 55 有幻纹 -all -2')
            self.assertEqual(c.name,'玄骸');self.assertTrue(c.include_offline);self.assertEqual(c.page,2)
            self.assertEqual(filters(c.query),('布拉玛','toxin',True,55.,60.))
        self.assertEqual(parse('wml').name,'玄骸')
        self.assertEqual(parse('姐妹 帮助').name,'姐妹')
        for q in ['布拉玛 毒 火','布拉玛 24','布拉玛 61','布拉玛 60-50','布拉玛 有幻纹 无幻纹','布拉玛 50 55']:
            with self.assertRaises(QueryError):filters(q)
        for q in ['玄骸 布拉玛 -rank=8','姐妹 典客 -buy','玄骸 布拉玛 -r']:
            with self.assertRaises(QueryError):parse(q)

    def test_names_and_unknown_filter(self):
        for q in ['布拉玛','赤毒布拉玛','Kuva Bramma','kuva_bramma']:
            self.assertEqual(match_weapons(WEAPONS,q),WEAPONS)
        self.assertEqual(match_weapons(WEAPONS,'布拉玛 胡乱词条'),[])

    def test_filters_revalidate_api(self):
        c=parse('玄骸 布拉玛')
        def choose(a):return select([a],'lich','kuva_bramma',c,'toxin',True,50,60)
        self.assertEqual(choose(ORDER),[ORDER])
        for field,value in [('closed',True),('private',True),('visible',False),('platform','ps4'),('buyout_price',None),('buyout_price',float('nan')),('is_direct_sell',False),('id','bad')]:
            bad=copy.deepcopy(ORDER);bad[field]=value;self.assertEqual(choose(bad),[])
        for field,value in [('type','sister'),('element','heat'),('damage',49),('damage',True),('having_ephemera',False),('having_ephemera',None),('weapon_url_name','kuva_nukor')]:
            bad=copy.deepcopy(ORDER);bad['item'][field]=value;self.assertEqual(choose(bad),[])
        bad=copy.deepcopy(ORDER);bad['owner']['status']='offline';self.assertEqual(choose(bad),[])
        c.include_offline=True;self.assertEqual(choose(bad),[bad])

class LichServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_requests_and_card(self):
        class Client:
            async def get(self,url,**kwargs):
                if url.endswith('/weapons'):return WEAPONS
                self.url=url;self.kwargs=kwargs;return {'auctions':[ORDER]}
        client=Client();service=LichMarketService(client)
        card=await service.run(parse('玄骸 布拉玛 毒 50-60 有幻纹'))
        self.assertEqual(card.rows[0][0][0],'Tester')
        self.assertIn('55%',card.rows[0][2][0])
        self.assertIn('having_ephemera=true',client.url)
        self.assertIn('type=lich',client.url)
        self.assertIn('damage_min=50&damage_max=60',client.url)
        self.assertIn('element=toxin',client.url)
        self.assertIn('不代表全部挂单',card.footer)
        help_card=await service.run(parse('玄骸'))
        self.assertIn('绯红之厅',str(help_card))
        with self.assertRaises(QueryError):await service.run(parse('玄骸 布拉玛 -2'))
