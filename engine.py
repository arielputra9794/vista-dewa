"""VISTA valuation engine. All monetary amounts IDR bn; shares in millions."""
import copy
import json
import math
import random
import statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def load_data():
    return json.loads((ROOT/'data/model_inputs.json').read_text())

def normalized(h):
    # Start at gross profit, removing non-operating gains without double subtraction.
    ebit=h['revenue']-h['cogs']-h['sga']-h['final_tax']
    return {'ebit':ebit,'ebitda':ebit+h['da_ppe']+h['da_rou'] if 'da_ppe' in h and 'da_rou' in h else None}

def bridge(data,case):
    h=data['historical']['Q3YTD2026']
    debt=sum(h[x] for x in ['bank_current','bank_long','finance_lease_current','finance_lease_long','other_borrowings_current','other_borrowings_long','related_debt'])
    investments=(h['investments']+h['associate_asset']+h['liquid_investments'])*case['investment_recovery']
    exploration=max(0,h['exploration']-data['historical']['FY2025']['exploration_dtl'])*case['asset_recovery']
    return dict(debt=debt,cash=h['cash'],net_debt=debt-h['cash'],investments=investments,exploration=exploration,nci=h['nci'],adjustment=h['cash']+investments+exploration-debt-h['nci'])

def base_nwc(h):
    return sum(h[k] for k in ['receivables_related','receivables_third','inventory','prepaid','other_current'])-sum(h[k] for k in ['trade_payables','accruals','unearned','customer_advances'])

def validate_case(c):
    for k in ['growth','margin','da','capex','nwc']:
        if len(c[k])!=5 or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in c[k]):raise ValueError(k+' must contain five finite numeric inputs')
    for k in ['wacc','g','roic','asset_recovery','investment_recovery']:
        if not isinstance(c[k],(int,float)) or not math.isfinite(c[k]): raise ValueError(k+' must be finite')
    if not 0<c['wacc']<1 or not 0<=c['g']<c['wacc']:raise ValueError('WACC must exceed terminal growth, and both must be economically valid.')
    if c['roic']<=c['g']:raise ValueError('Terminal ROIC must exceed terminal growth.')
    if any(x<=-1 for x in c['growth']):raise ValueError('Revenue growth must exceed -100%.')
    if any(not 0<=x<=1 for k in ['da','capex','nwc','margin'] for x in c[k]):raise ValueError('Operating ratios must lie between 0 and 100%.')
    if not 0<=c['asset_recovery']<=1 or not 0<=c['investment_recovery']<=1:raise ValueError('Recovery assumptions must lie between 0 and 100%.')

def dcf(data,case):
    validate_case(case)
    if data['market']['shares_m']<=0 or data['market']['price']<=0:raise ValueError('Price and shares must be positive.')
    tax=data['assumptions']['tax']
    if not 0<=tax<=1:raise ValueError('Tax must lie between 0 and 100%.')
    rev=data['historical']['Q3YTD2026']['revenue']*4/3
    nwc=base_nwc(data['historical']['Q3YTD2026'])
    rows=[]
    for i in range(5):
        rev*=1+case['growth'][i]
        ebit=rev*case['margin'][i]
        nopat=ebit*(1-tax)
        da=rev*case['da'][i]
        cash_capex=rev*case['capex'][i]
        lease_capex=rev*data['assumptions']['noncash_lease_capex_ratio']
        closing_nwc=rev*case['nwc'][i]
        change=closing_nwc-nwc
        fcff=nopat+da-cash_capex-lease_capex-change
        factor=(1+case['wacc'])**(i+1)
        rows.append(dict(period=f'F{i+1}',year_end=f'{2027+i}-09-30',revenue=rev,ebit=ebit,nopat=nopat,da=da,cash_capex=cash_capex,lease_capex=lease_capex,nwc=closing_nwc,delta_nwc=change,fcff=fcff,discount_factor=1/factor,pv=fcff/factor))
        nwc=closing_nwc
    terminal_nopat=rows[-1]['nopat']*(1+case['g'])
    reinvestment=terminal_nopat*case['g']/case['roic']
    terminal_fcff=terminal_nopat-reinvestment
    terminal_value=terminal_fcff/(case['wacc']-case['g'])
    terminal_pv=terminal_value/(1+case['wacc'])**5
    ev=sum(r['pv'] for r in rows)+terminal_pv
    b=bridge(data,case)
    equity=ev+b['adjustment']
    return dict(rows=rows,ev=ev,terminal_nopat=terminal_nopat,terminal_reinvestment=reinvestment,terminal_fcff=terminal_fcff,terminal_value=terminal_value,terminal_pv=terminal_pv,tv_share=terminal_pv/ev if ev>0 else None,equity_unfloored=equity,equity=max(0,equity),price=max(0,equity)*1000/data['market']['shares_m'],bridge=b)

def relative(data,case):
    vals=[p['ev_ebitda'] for p in data['peers'] if p['include']]
    if any(not isinstance(x,(int,float)) or not math.isfinite(x) or x<=0 for x in vals):raise ValueError('Included peer EV/EBITDA multiples must be positive and finite.')
    if not vals:return dict(price=None,ev=None,multiple=None,n=0,dispersion=None)
    multiple=statistics.median(vals)
    # Normalized annualized 9M operating EBITDA, not acquisition-inflated earnings.
    ebitda=normalized(data['historical']['Q3YTD2026'])['ebitda']*4/3
    if ebitda<=0: return dict(price=None,ev=None,multiple=multiple,n=len(vals),dispersion=None)
    ev=multiple*ebitda
    eq=ev+bridge(data,case)['adjustment']
    return dict(price=max(0,eq)*1000/data['market']['shares_m'],ev=ev,equity_unfloored=eq,multiple=multiple,n=len(vals),dispersion=statistics.pstdev(vals)/statistics.mean(vals),ebitda=ebitda)

def assess(data,d,r):
    a=data['assumptions']
    terminal=min(max(d['tv_share'] if d['tv_share'] is not None else 1,0),1)
    ds=100*(.4*a['core_source_quality']+.3*a['forecast_visibility']+.3*(1-terminal))
    rs=100*(.4*a['peer_quality']+.3*min(r['n']/4,1)+.3/(1+(r['dispersion'] or 0))) if r['price'] is not None else 0
    asset=100*(.5*a['core_source_quality']+.5*a['asset_observability'])
    total=ds+rs
    dw=ds/total if total else 1
    rw=1-dw if total else 0
    fair=dw*d['price']+rw*(r['price'] or 0)
    disagreement=abs(d['price']-(r['price'] or d['price']))/max(fair,1)
    confidence=max(0,min(100,(ds*dw+rs*rw)-20*min(disagreement,1)-10)) # explicit unresolved share/peer perimeter penalty
    upside=fair/data['market']['price']-1
    signal='AVOID / REDUCE' if upside<-.20 else 'BUY CANDIDATE' if upside>.20 else 'WATCH / HOLD'
    if confidence<60:signal='PROVISIONAL '+signal
    return dict(dcf_score=ds,relative_score=rs,asset_score=asset,dcf_weight=dw,relative_weight=rw,fair_price=fair,upside=upside,confidence=confidence,recommendation=signal,disagreement=disagreement)

def evaluate(data,case_name='Base',case=None):
    c=copy.deepcopy(case or data['scenarios'][case_name]);d=dcf(data,c);r=relative(data,c)
    return dict(case=case_name,assumptions=c,dcf=d,relative=r,assessment=assess(data,d,r))

def sensitivity(data,case):
    out=[]
    for w in [.10,.12,.14,.16,.18]:
        row={'WACC':w}
        for g in [.02,.025,.03,.035,.04]:
            c=copy.deepcopy(case);c.update(wacc=w,g=g)
            row[f'{g:.1%}']=dcf(data,c)['price']
        out.append(row)
    return out

def monte_carlo(data,n=2000,seed=42):
    rng=random.Random(seed);values=[]
    for _ in range(n):
        c=copy.deepcopy(data['scenarios']['Base'])
        c['wacc']=rng.triangular(.11,.18,.14)
        c['g']=rng.triangular(.02,.045,.035)
        delta=rng.triangular(-.04,.04,0)
        c['margin']=[max(0,x+delta) for x in c['margin']]
        gd=rng.triangular(-.06,.06,0)
        c['growth']=[x+gd for x in c['growth']]
        cd=rng.triangular(-.025,.04,0)
        c['capex']=[x+cd for x in c['capex']]
        c['asset_recovery']=rng.triangular(0,.60,.30)
        values.append(dcf(data,c)['price'])
    s=sorted(values)
    def q(p):
        idx=(len(s)-1)*p;lo=int(idx);hi=min(lo+1,len(s)-1);return s[lo]+(s[hi]-s[lo])*(idx-lo)
    return dict(n=n,seed=seed,p10=q(.1),p50=q(.5),p90=q(.9),fraction_above_price=sum(v>data['market']['price'] for v in values)/n,values=values)

def audit(data):
    checks=[]
    def add(name,delta,tolerance=.000001):checks.append(dict(check=name,difference=delta,status='PASS' if abs(delta)<=tolerance else 'FAIL'))
    for period,h in data['historical'].items():
        if all(k in h for k in ['assets','liabilities','equity']):add(period+' balance sheet',h['assets']-h['liabilities']-h['equity'])
        if 'pbt' in h:
            add(period+' gross profit',h['revenue']-h['cogs']-h['gross_profit'])
            pbt=normalized(h)['ebit']+h['finance_income']-h['finance_cost']+h['fx']+h['associates']+h['other']
            add(period+' PBT reconstruction',pbt-h['pbt'])
            add(period+' tax bridge',h['pbt']-h['tax_expense']-h['net_income'])
        if all(k in h for k in ['cfo','cfi','cff','cash']):add(period+' cash rollforward',h.get('opening_cash',data['historical']['FY2025']['cash'])+h['cfo']+h['cfi']+h['cff']-h['cash'])
    h=data['historical']['FY2025']
    add('FY2025 other income bridge',h['acquisition_gain']-sum(h[k] for k in ['receivable_writeoff','loss_of_control','inventory_writeoff','asset_disposal_loss'])+h['other_residual']-h['other'])
    add('Scenario probabilities',sum(c['probability'] for c in data['scenarios'].values())-1)
    for name in data['scenarios']:
        e=evaluate(data,name);d=e['dcf'];add(name+' EV bridge',sum(x['pv'] for x in d['rows'])+d['terminal_pv']-d['ev'])
        add(name+' approach weights',e['assessment']['dcf_weight']+e['assessment']['relative_weight']-1)
    return checks

def all_results(data):
    results=[evaluate(data,n) for n in data['scenarios']]
    expected=sum(x['assessment']['fair_price']*data['scenarios'][x['case']]['probability'] for x in results)
    return dict(results=results,expected_price=expected,audit=audit(data),monte_carlo=monte_carlo(data),sensitivity=sensitivity(data,data['scenarios']['Base']))

if __name__=='__main__':
    results=all_results(load_data())
    (ROOT/'data/results.json').write_text(json.dumps(results,indent=2))
    print(json.dumps({x['case']:x['assessment'] for x in results['results']},indent=2))
