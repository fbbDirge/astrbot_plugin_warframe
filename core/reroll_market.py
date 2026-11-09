"""Observed WM supply statistics, with persistent per-platform market-family snapshots."""
import asyncio
from collections import Counter,defaultdict
from datetime import datetime,timezone,timedelta
import hashlib,json,math,os,re,time,uuid
from statistics import median
from . import paths
from .commands.base import Reply
from .formatters import _riven_stat_cn
from .reroll_categories import classify

TTL=600
MIN_SAMPLE=20
MIN_SELLERS=5
S='　'
_LOCKS={}

def _key(value):return hashlib.sha256(value.encode()).hexdigest()
def _path(kind,key):return paths.run_dir()/'reroll_market'/kind/(key+'.json')
def _read(path):
    try:
        value=json.loads(path.read_text())
        return value if isinstance(value,dict) and value.get('schema')==1 else None
    except (OSError,ValueError):return None

def _write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        tmp.write_text(json.dumps({'schema':1,**data},ensure_ascii=False));os.replace(tmp,path)
    finally:
        tmp.unlink(missing_ok=True)

def snapshot(path,slug,platform):
    data=_read(path)
    if not data or data.get('slug')!=slug or data.get('platform')!=platform:return None
    ts=data.get('sampled_at')
    if not isinstance(ts,(int,float)) or not math.isfinite(ts) or ts>time.time()+60:return None
    stats=data.get('stats')
    if not isinstance(stats,dict) or not all(k in stats for k in ('valid','sellers','positive','negative','combos','returned','excluded')):return None
    if any(type(stats[k])!=int or stats[k]<0 for k in ('valid','sellers','returned','excluded')):return None
    for key in ('positive','negative','combos'):
        if not isinstance(stats[key],list):return None
        for row in stats[key]:
            if not isinstance(row,dict) or not isinstance(row.get('cohort'),str):return None
            if type(row.get('count'))!=int or row['count']<0:return None
            share=row.get('share')
            if type(share) not in (int,float) or not math.isfinite(share) or not 0<=share<=1.000001:return None
            if key!='combos':
                if not isinstance(row.get('stat'),str):return None
            else:
                if type(row.get('rank'))!=int or not 0<=row['rank']<=8:return None
                if type(row.get('price_n'))!=int:return None
                if any(not isinstance(row.get(k),list) or not all(isinstance(v,str) for v in row[k]) for k in ('positive','negative')):return None
                price=row.get('median')
                if price is not None and (type(price) not in (int,float) or not math.isfinite(price) or price<=0):return None
    categories=stats.get('categories')
    if categories is not None:
        if not isinstance(categories,list):return None
        for row in categories:
            if not isinstance(row,dict) or not isinstance(row.get('stat'),str):return None
            if row.get('polarity') not in {'pos','neg'} or row.get('category') not in {'unknown','conflicting','unfavorable','positive','ordinary_positive','negative_candidate','ordinary_negative'}:return None
            if any(type(row.get(k))!=int or row[k]<0 for k in ('count','sellers')):return None
            if row.get('tier') not in (None,'T0','T1','T2'):return None
            for k in ('delta','pct'):
                v=row.get(k)
                if v is not None and (type(v) not in (int,float) or not math.isfinite(v)):return None
            if not isinstance(row.get('comparisons'),list):return None
            for c in row['comparisons']:
                if not isinstance(c,dict) or not isinstance(c.get('cohort'),str):return None
                if any(type(c.get(k))!=int or c[k]<0 for k in ('rank','with_sellers','without_sellers')):return None
    return data

def summarize(auctions,slug):
    """Each seller totals one vote. Prices are raw asking medians within rank + exact combo."""
    if not isinstance(auctions,list):raise ValueError('Invalid auction list')
    unique={a['id']:a for a in auctions if isinstance(a,dict) and isinstance(a.get('id'),str) and a['id']}
    if auctions and not unique:raise ValueError('No valid auction envelope')
    rows=[]
    for a in unique.values():
        if a.get('visible') is not True or a.get('closed') is not False:continue
        item=a.get('item') or {};owner=a.get('owner') or {}
        if not isinstance(item,dict) or not isinstance(owner,dict):continue
        if item.get('type')!='riven' or item.get('weapon_url_name')!=slug:continue
        seller=owner.get('id') or owner.get('ingame_name')
        rank=item.get('mod_rank')
        if not isinstance(seller,str) or not seller or type(rank)!=int or not 0<=rank<=8:continue
        attrs=item.get('attributes');pos=[];neg=[];valid=True
        if not isinstance(attrs,list):continue
        for at in attrs:
            if not isinstance(at,dict) or not isinstance(at.get('url_name'),str) or not at['url_name'] or type(at.get('positive'))!=bool:
                valid=False;break
            (pos if at['positive'] else neg).append(at['url_name'])
        if not valid or len(pos) not in (2,3) or len(neg)>1 or len(set(pos+neg))!=len(pos+neg):continue
        price=a.get('buyout_price')
        price=price if type(price) in (int,float) and math.isfinite(price) and price>0 else None
        rows.append({'seller':seller,'rank':rank,'pos':tuple(sorted(pos)),'neg':tuple(sorted(neg)),'price':price})
    seller_counts=Counter(r['seller'] for r in rows)
    cohorts=defaultdict(float);counts={True:defaultdict(lambda:[0,0.]),False:defaultdict(lambda:[0,0.])};combos={}
    for r in rows:
        weight=1/seller_counts[r['seller']];cohort=f"{len(r['pos'])}正{len(r['neg'])}负"
        cohorts[cohort]+=weight
        for positive in (True,False):
            for stat in r['pos' if positive else 'neg']:
                entry=counts[positive][cohort,stat];entry[0]+=1;entry[1]+=weight
        key=(cohort,r['rank'],r['pos'],r['neg'])
        c=combos.setdefault(key,{'cohort':cohort,'rank':r['rank'],'positive':r['pos'],'negative':r['neg'],'count':0,'weight':0.,'sellers':set(),'prices':[]})
        c['count']+=1;c['weight']+=weight;c['sellers'].add(r['seller'])
        if r['price'] is not None:c['prices'].append((r['seller'],r['price']))
    def ranking(positive):
        out=[]
        for (cohort,stat),(count,weight) in counts[positive].items():
            out.append({'cohort':cohort,'stat':stat,'count':count,'share':weight/cohorts[cohort]})
        return sorted(out,key=lambda x:(x['cohort'],-x['share'],x['stat']))
    output=[]
    for c in combos.values():
        c['share']=c.pop('weight')/cohorts[c['cohort']];c['sellers']=len(c['sellers'])
        quotes=c.pop('prices');prices=[v for _,v in quotes];c['price_n']=len(prices)
        c['price_sellers']=len({seller for seller,_ in quotes})
        c['median']=median(prices) if len(prices)>=3 and c['price_sellers']>=3 else None
        output.append(c)
    return {'returned':len(unique),'valid':len(rows),'excluded':len(unique)-len(rows),'sellers':len(seller_counts),
            'categories':classify(rows),'positive':ranking(True),'negative':ranking(False),'combos':sorted(output,key=lambda c:(-c['share'],-c['count']))}

def report(asked,weapon,data,state,mode='',write_failed=False):
    stats=data['stats'];name=asked.get('zh') or asked.get('en') or data['slug']
    family=weapon.get('zh') or weapon.get('en') or data['slug']
    stamp=datetime.fromtimestamp(data['sampled_at'],timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
    age=max(0,int((time.time()-data['sampled_at'])//60))
    lines=[f'◆ WM 紫卡家族：{family}',f'◆ 数据状态：{state}',f'◆ 采样时间：{stamp}（北京时间，约 {age} 分钟前）',
           f"◆ 样本：有效 {stats['valid']} 张 / {stats['sellers']} 位卖家；去重返回 {stats['returned']} 张，排除 {stats['excluded']} 张",
           '※ 抽样范围：价格升序＋降序合并；接口可能截断，不代表全市场。',
           '※ 占比按卖家降权：每位卖家在整个样本中的总权重为 1；同组内计算占比。']
    enough=stats['valid']>=MIN_SAMPLE and stats['sellers']>=MIN_SELLERS
    if not enough:lines+=['◆ 样本不足：至少 20 张、5 位卖家才形成统计参考；以下仅展示观察值。']
    label=lambda stat:_riven_stat_cn(stat,weapon.get('riven_type',''),weapon.get('group',''))
    categories = stats.get('categories')
    if categories is None:
        lines += ['◆ 词条分类待更新', '· 此历史缓存尚未包含价差统计，发送“'+name+' 洗卡推荐 刷新”重新采样。']
    else:
        lines += ['※ 分类依据：同等级、同正负结构内，比较带/不带词条的卖家报价中位数；每位卖家先取中位价，两边重叠卖家排除。',
                  '※ 每边至少 5 个有效报价、3 位卖家；跨组按较小卖家数加权。价差仅是关联，其他词条与数值品质仍可能影响结果。']
        definitions = [('positive','正面推荐 · 市场溢价分档'),
                       ('ordinary_positive','普通正面 · 价差不明显'),
                       ('negative_candidate','负面候选 · 市场溢价'),
                       ('ordinary_negative','普通负面 · 价差不明显'),
                       ('unfavorable','不利词条 · 市场折价'),
                       ('conflicting','争议词条 · 分组结论相反'),
                       ('unknown','待判断 · 样本不足')]
        for category, title in definitions:
            selected = [r for r in categories if r['category'] == category]
            if not selected: continue
            lines += ['◆ '+title,S+S.join(['档位','词条','挂牌价差','对照样本'])]
            for r in selected:
                sign = '▲' if r['polarity'] == 'pos' else '▼'
                tier = r.get('tier') or '—'
                delta = '—' if r['pct'] is None else f"{r['delta']:+.1f} 白金 / {r['pct']:+.1f}%"
                samples = '；'.join(f"{c['cohort']} {c['rank']}级：{c['with_sellers']}/{c['without_sellers']}卖家" for c in r['comparisons'])
                if not samples:samples=f"观察 {r['count']} 张 / {r['sellers']} 卖家，无足够对照"
                lines += ['· '+S.join([tier,sign+label(r['stat']),delta,samples])]
        if not categories:lines += ['◆ 词条分类', '· 暂无有效词条样本']
        lines += ['※ T0≥40% / T1≥20% / T2≥10% 溢价；≤−10% 为不利，介于其间为普通。分档是本插件的市场参考规则，不是游戏强度等级。',
                  '※ 对照样本为“带词条 / 不带词条”的独立卖家数。负面候选不等于无害负面；不利项不等于所有配装的致命项。',
                  '※ 本页未计算击杀效率，没有据此生成伤害收益或战斗推荐。']
    lines+=['◆ 常见组合与挂牌参考',S+S.join(['结构 / 等级','正词条 / 负词条','样本 / 占比','挂牌中位数'])]
    shown=Counter()
    for r in stats['combos']:
        if shown[r['cohort']]>=1:continue
        shown[r['cohort']]+=1
        attrs=' / '.join(label(x) for x in r['positive'])+'\n负面：'+(' / '.join(label(x) for x in r['negative']) or '无')
        price=f"{r['median']:g} 白金" if r['median'] is not None else '价格样本不足'
        lines+=['· '+S.join([f"{r['cohort']}·{r['rank']}级",attrs.replace('\n','；'),f"{r['count']}张 / {r['share']:.0%}",price+f"（{r['price_n']}单）"])]
    if not stats['combos']:lines+=['· 暂无有效组合']
    lines+=['◆ 如何用来选洗卡方向',
            '· 常见组合可作为挑选目标的候选，再按你的暴击路线与触发机制、元素组合及增益判断；不能只按出现次数决定。',
            '· 常见负面不等于无害负面；应检查它是否影响当前武器与打法。',
            '· 挂牌中位数仅对相同正负词条、结构、等级分组；数值品质仍不同，既不是成交价，也不是收益预测。',
            '· 标价必须为有效正数；无买断价的挂单只计词条。少于 3 个价格或 3 位卖家的组合不展示中位价。']
    if mode:lines+=['※ '+mode+'用途：WM 挂单没有打法标签，本统计未按该用途筛选。']
    if write_failed:lines+=['※ 本次数据已获取，但持久缓存写入失败。']
    return Reply(name+' · 洗卡推荐',lines,footer='来源：warframe.market 紫卡公开挂单 · 平台 '+data['platform']+'\n常见＝在售供给，不代表最好用或畅销；最新返回也可能命中 WM 客户端的短时缓存。')

async def market_recommend(client,query,platform):
    from .commands.market import riven_market_weapon
    query=query.strip()
    if not query:return Reply('洗卡推荐',['◆ 用法：武器名 洗卡推荐','· 绝路 洗卡推荐','· 洗卡推荐 托里德','· 支持所有 wmr 可查询的紫卡武器；可加 刷新 或平台参数。'])
    refresh=bool(re.search(r'(?:^|\s)刷新$',query));query=re.sub(r'\s*刷新$','',query).strip()
    mode=''
    match=re.search(r'\s+(夜灵|三傻|日常|通用)$',query)
    if match:mode=match[1];query=query[:match.start()].strip()
    querykey=_key(platform+'|'+query.casefold())
    mapping_path=_path('queries',querykey);mapping=_read(mapping_path)
    mapping_ok=mapping and mapping.get('platform')==platform and isinstance(mapping.get('weapon'),dict) and isinstance(mapping.get('asked'),dict)
    if mapping_ok:
        asked,weapon=mapping['asked'],mapping['weapon']
        old=snapshot(_path('snapshots',_key(platform+'|'+weapon.get('url_name',''))),weapon.get('url_name',''),platform)
        if old and 'categories' in old['stats'] and not refresh and time.time()-old['sampled_at']<TTL:return report(asked,weapon,old,'缓存命中（10 分钟有效期）',mode)
    try:
        async with asyncio.timeout(25):
            asked=await client.resolve_riven_weapon(query)
            if not asked:return Reply('洗卡推荐 · 未找到武器',['◆ 请使用完整中文名、英文名或现有 wmr 别名。'])
            weapon=await riven_market_weapon(client,query,asked)
    except Exception:
        if not mapping_ok:return Reply('洗卡推荐 · 数据暂不可用',['◆ WM 武器查询失败，且没有此查询的本地缓存。','· 稍后重试；不会使用其他武器的数据替代。'])
        asked,weapon=mapping['asked'],mapping['weapon']
    slug=weapon.get('url_name')
    if not isinstance(slug,str) or not slug:return Reply('洗卡推荐',['◆ 无法确认 WM 紫卡家族，请使用完整武器名。'])
    key=_key(platform+'|'+slug);path=_path('snapshots',key)
    try:_write(mapping_path,{'platform':platform,'asked':asked,'weapon':weapon})
    except OSError:pass
    lock=_LOCKS.setdefault(str(path),asyncio.Lock())
    async with lock:
        old=snapshot(path,slug,platform)
        if old and 'categories' in old['stats'] and not refresh and time.time()-old['sampled_at']<TTL:return report(asked,weapon,old,'缓存命中（10 分钟有效期）',mode)
        try:
            async with asyncio.timeout(45):
                auctions=await client.wm_riven_auctions(slug,platform,sorts=('price_asc','price_desc'),require_all_sorts=True,retries=0,timeout=15)
            stats=summarize(auctions,slug)
            data={'slug':slug,'platform':platform,'sampled_at':time.time(),'stats':stats}
        except Exception:
            if old:return report(asked,weapon,old,'接口失败，使用历史缓存（非实时）',mode)
            return Reply('洗卡推荐 · 数据暂不可用',['◆ WM 挂单查询失败，且没有该武器在此平台的缓存。','· 稍后重试；没有生成统计推荐。'])
        failed=False
        try:_write(path,data)
        except OSError:failed=True
        return report(asked,weapon,data,'本次查询成功（WM 返回样本）',mode,failed)
