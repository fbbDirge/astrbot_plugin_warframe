import unittest
import test_core
from wf_plugin.core.reroll_categories import classify
from wf_plugin.core.reroll_market import summarize
from test_reroll_market import auction

class CategoryTests(unittest.TestCase):
    def rows(self):
        return [auction(i,pos=('damage','critical_chance') if i<10 else ('damage','multishot'),
                        neg=('zoom',) if i<10 else ('recoil',),price=150 if i<10 else 100) for i in range(20)]
    def lookup(self, data, stat):return next(r for r in data['categories'] if r['stat']==stat)
    def test_positive_negative_and_unfavorable(self):
        data=summarize(self.rows(),'torid')
        positive=self.lookup(data,'critical_chance')
        self.assertEqual((positive['tier'],positive['pct']),('S',50))
        self.assertEqual(self.lookup(data,'zoom')['category'],'negative_candidate')
        self.assertEqual(self.lookup(data,'recoil')['category'],'unfavorable')
        self.assertEqual(self.lookup(data,'damage')['category'],'unknown')
    def test_no_rank_mixing_or_single_seller_effect(self):
        rows=self.rows()
        for a in rows[:10]:a['item']['mod_rank']=0
        self.assertTrue(all(r['category']=='unknown' for r in summarize(rows,'torid')['categories']))
        rows=self.rows()
        for a in rows[:10]:a['owner']['id']='bulk'
        self.assertTrue(all(r['category']=='unknown' for r in summarize(rows,'torid')['categories']))
    def test_missing_prices_do_not_produce_rankings(self):
        rows=self.rows()
        for a in rows[10:]:a['buyout_price']=None
        self.assertTrue(all(r['category']=='unknown' for r in summarize(rows,'torid')['categories']))
        self.assertTrue(all(r['category']=='unknown' for r in summarize(self.rows()[:10],'torid')['categories']))
    def test_opposite_strata_are_marked_conflicting(self):
        rows=self.rows();other=self.rows()
        for a in other:
            a['id']='other'+a['id'];a['owner']['id']='other'+a['owner']['id'];a['item']['mod_rank']=0
            a['buyout_price']=100 if a['buyout_price']==150 else 150
        self.assertEqual(self.lookup(summarize(rows+other,'torid'),'critical_chance')['category'],'conflicting')
