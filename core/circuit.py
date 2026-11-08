"""Independent normal/Steel Path Circuit schedules and a semantic detail view."""
import json
from datetime import datetime,timedelta,timezone
from pathlib import Path
from .viewmodel import DataLines

def position(data,now):
    period=timedelta(hours=int(data.get('period_hours',168)))
    epoch=datetime.fromisoformat(data['epoch'])
    passed=(now-epoch)//period
    index=(int(data.get('anchor_week',1))-1+passed)%len(data['weeks'])
    return index,epoch+(passed+1)*period

def detail(data,now=None):
    now=now or datetime.now(timezone.utc)
    frames=json.loads((Path(__file__).parent/'data/circuit_frames.json').read_text())
    wi,reset=position(data,now);fi,_=position(frames,now)
    weeks=[[{'name':w.get('cn') or w.get('en'),'identity':w.get('en') or w.get('cn')} for w in row] for row in data['weeks']]
    payload={'frames':frames['weeks'][fi],'next_frames':frames['weeks'][(fi+1)%len(frames['weeks'])],
             'weapons':weeks[wi],'next_weapons':weeks[(wi+1)%len(weeks)],'weeks':weeks,
             'current_week':wi,'next_week':(wi+1)%len(weeks),'reset':reset.isoformat(),
             'remaining_seconds':max(0,int((reset-now).total_seconds()))}
    # Diagnostic text deliberately excludes reviews, recommendations and weapon variants.
    lines=['◆ 本周战甲：'+'、'.join(payload['frames']),'◆ 下周战甲：'+'、'.join(payload['next_frames']),
           '◆ 本周灵化武器：'+'、'.join(w['name'] for w in weeks[wi]),
           '◆ 下周灵化武器：'+'、'.join(w['name'] for w in payload['next_weapons'])]
    return DataLines(lines,domain='incarnon_detail',meta=payload)
