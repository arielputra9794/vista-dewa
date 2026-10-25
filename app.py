"""Launch with python -m streamlit run app.py."""
import copy,json
import pandas as pd
import streamlit as st
from engine import ROOT,load_data,evaluate,all_results,normalized,sensitivity,monte_carlo,audit

st.set_page_config(page_title='VISTA · DEWA',page_icon='◈',layout='wide')
st.markdown('<style>.block-container{padding-top:2rem} h1{letter-spacing:-.04em} [data-testid="stMetricValue"]{color:#06796e}</style>',unsafe_allow_html=True)
data=load_data()
st.title('VISTA')
st.caption('Valuation Intelligence, Scenario Testing & Approach Selection')
st.caption('Developed by Ariel Arviano Putra · 29125401')
st.subheader('PT Darma Henwa Tbk · IDX:DEWA')
st.caption('19 October 2026 market reference · 30 September 2026 financial position · IDR billion unless labeled otherwise')
with st.sidebar:
    st.header('Valuation controls')
    case_name=st.selectbox('Scenario',list(data['scenarios']),index=1)
    case=copy.deepcopy(data['scenarios'][case_name])
    data['market']['price']=st.number_input('Reference price (IDR/share)',min_value=1.,value=float(data['market']['price']))
    data['market']['shares_m']=st.number_input('Shares (million)',min_value=1.,value=float(data['market']['shares_m']),format='%.6f')
    st.caption(data['market']['shares_basis'])
    case['wacc']=st.slider('Nominal IDR WACC (%)',8.,25.,case['wacc']*100,.5)/100
    case['g']=st.slider('Terminal growth (%)',0.,6.,case['g']*100,.5)/100
    case['roic']=st.slider('Terminal ROIC (%)',6.,30.,case['roic']*100,.5)/100
    case['asset_recovery']=st.slider('Exploration net carrying value recovery (%)',0,100,round(case['asset_recovery']*100))/100
    case['investment_recovery']=st.slider('Investment recovery (%)',0,100,round(case['investment_recovery']*100))/100
    data['assumptions']['tax']=st.slider('Normalized tax (%)',0.,40.,22.,.5)/100
    data['assumptions']['forecast_visibility']=st.slider('Forecast visibility judgment',0.,1.,.4,.05)
    data['assumptions']['peer_quality']=st.slider('Peer data quality judgment',0.,1.,.5,.05)
    st.caption('Quality scores are disclosed analyst judgments, not trained predictions.')

with st.expander('Edit five-year operating assumptions'):
    rows=[{'Period':f'F{i+1}',**{k:case[k][i]*100 for k in ['growth','margin','da','capex','nwc']}} for i in range(5)]
    edited=st.data_editor(pd.DataFrame(rows),disabled=['Period'],hide_index=True,key=case_name)
    st.caption('All entries are percentages. Margin is normalized EBIT after final tax. Cash capex excludes the additional 0.5% lease/noncash replacement allowance.')
    for k in ['growth','margin','da','capex','nwc']:case[k]=(edited[k]/100).tolist()
with st.expander('Peer selection and multiple overrides'):
    peers=st.data_editor(pd.DataFrame(data['peers']),disabled=['ticker','name','reason','source','profile_source','date','basis','ev_idr_bn','reference_price'],hide_index=True)
    data['peers']=peers.to_dict('records')
try:result=evaluate(data,case_name,case)
except (ValueError,TypeError) as e:st.error(str(e));st.stop()
a=result['assessment'];d=result['dcf'];r=result['relative']
st.warning(a['recommendation']+' · Assumption-dependent academic conclusion. Read confidence and limitations before interpreting the price.')
cols=st.columns(4)
for col,label,value in zip(cols,['Blended value / share','DCF value / share','Relative value / share','Model confidence'],[f"Rp{a['fair_price']:,.1f}",f"Rp{d['price']:,.1f}",'Unavailable' if r['price'] is None else f"Rp{r['price']:,.1f}",f"{a['confidence']:.0f}/100"]):col.metric(label,value)
st.caption(f"Implied return {a['upside']:+.1%}. This is a valuation gap, not a forecast realized return. DCF weight {a['dcf_weight']:.1%}, relative weight {a['relative_weight']:.1%}.")
tabs=st.tabs(['Valuation','Financial history','Scenarios & sensitivity','Suitability & confidence','Sources & checks'])
with tabs[0]:
    st.subheader('Recurring cash flows')
    frame=pd.DataFrame(d['rows']).set_index('period');st.line_chart(frame[['revenue','ebit','fcff']]);st.dataframe(frame.round(2))
    st.subheader('Enterprise value to equity')
    st.dataframe(pd.DataFrame([{'Item':label,'IDR bn':value} for label,value in [('Operating enterprise value',d['ev']),('Less debt',-d['bridge']['debt']),('Add cash',d['bridge']['cash']),('Add recoverable investments',d['bridge']['investments']),('Add exploration recovery',d['bridge']['exploration']),('Less NCI',-d['bridge']['nci']),('Equity before zero floor',d['equity_unfloored'])]]).round(2),hide_index=True)
    st.write(f"Operating EV: Rp{d['ev']:,.1f}bn. Terminal PV: Rp{d['terminal_pv']:,.1f}bn. Terminal share: {d['tv_share']:.1%}.")
    if d['tv_share']>0.75:st.warning('High terminal-value dependence. The explicit forecast alone provides limited support for valuation.')
    st.write(f"Market capitalization on the selected share basis: Rp{data['market']['price']*data['market']['shares_m']/1000:,.1f}bn. Observed enterprise value before separating investments: Rp{data['market']['price']*data['market']['shares_m']/1000+d['bridge']['net_debt']+d['bridge']['nci']:,.1f}bn.")
    st.caption('Cash is added once. All equipment/lease/other borrowings are subtracted once. Exploration is included only through the risk-adjusted net-asset addition. Negative equity is floored at zero for per-share presentation.')
    st.write('Terminal FCFF = next-year NOPAT × (1 − g / terminal ROIC). This funds perpetual growth rather than assuming growth without reinvestment.')
with tabs[1]:
    hist=[]
    for name in ['FY2024R','FY2025','Q1YTD2026','Q2YTD2026','Q3YTD2026']:
        h=data['historical'][name];hist.append({'Period':name,'Revenue':h['revenue'],'Reported profit':h['net_income'],**normalized(h)})
    st.dataframe(pd.DataFrame(hist),hide_index=True)
    st.caption('Interims are cumulative. FY2024R is the restated comparative. Standalone Q2 = six months minus Q1; standalone Q3 = nine months minus six months.')
    q=[];prev={'revenue':0,'net_income':0}
    for n in ['Q1YTD2026','Q2YTD2026','Q3YTD2026']:
        h=data['historical'][n];q.append({'Quarter':n[:2],'Revenue':h['revenue']-prev['revenue'],'Reported profit':h['net_income']-prev['net_income']});prev=h
    st.dataframe(pd.DataFrame(q),hide_index=True)
    st.info('FY2025 acquisition gain: Rp4,535.4bn. Normalization starts from gross profit less SG&A and final tax, so the gain is not subtracted twice. All other gains/losses are disclosed separately in the input register.')
    st.write('2024 restatement: assets/equity reduced by Rp272.1bn; net income increased by Rp38.9bn. 2026 interims reclassify Rp2,110.0bn within opening 2025 equity, with no total equity effect. The corrected Q2 file supersedes the earlier version.')
with tabs[2]:
    st.caption('Named scenarios below use their saved operating drivers; current price, shares, peer selection and quality controls apply to all. The active edited scenario is shown separately above.')
    rr=[evaluate(data,n) for n in data['scenarios']]
    st.dataframe(pd.DataFrame([{'Case':x['case'],'DCF':x['dcf']['price'],'Relative':x['relative']['price'],'Blended':x['assessment']['fair_price'],'Probability assumption':data['scenarios'][x['case']]['probability']} for x in rr]),hide_index=True)
    expected=sum(x['assessment']['fair_price']*data['scenarios'][x['case']]['probability'] for x in rr)
    st.write(f'Probability-weighted scenario value: Rp{expected:,.1f}/share. Probabilities are analyst assumptions.')
    st.subheader('DCF sensitivity to WACC and terminal growth')
    st.dataframe(pd.DataFrame(sensitivity(data,case)).set_index('WACC').style.format('{:,.1f}'))
    st.download_button('Download active forecast CSV',frame.to_csv(),'VISTA_active_forecast.csv','text/csv')
    st.download_button('Download active valuation JSON',json.dumps(result,indent=2),'VISTA_active_result.json','application/json')
with tabs[3]:
    st.dataframe(pd.DataFrame([{'Approach':'DCF','Score':a['dcf_score'],'Weight':a['dcf_weight']},{'Approach':'EV/EBITDA','Score':a['relative_score'],'Weight':a['relative_weight']},{'Approach':'Asset approach','Score':a['asset_score'],'Weight':0}]),hide_index=True)
    st.write('DCF score = 40% source quality + 30% forecast visibility + 30% explicit-period value share (floored at zero). Relative score = 40% peer quality + 30% peer coverage + 30% inverse dispersion. Asset score = 50% source quality + 50% asset observability. Asset method has zero blend weight because no independent reserve NAV is available. Market price is a benchmark, never a valuation weight.')
    st.write('Confidence = weighted method score − up to 20 points for disagreement − 10 points for unresolved share count and peer perimeter. Below 60, every signal is provisional. Buy-candidate / avoid thresholds are +20% / −20%.')
    mc=monte_carlo(data)
    st.write(f"Assumption simulation, 2,000 draws: DCF P10 Rp{mc['p10']:.1f}, P50 Rp{mc['p50']:.1f}, P90 Rp{mc['p90']:.1f}. {mc['fraction_above_price']:.1%} of draws exceed the reference price.")
    st.caption('Fixed seed 42. Independent triangular draws: WACC 11/14/18%, g 2/3.5/4.5%, margin shift −4/0/+4pp, growth shift −6/0/+6pp, capex shift −2.5/0/+4pp, exploration recovery 0/30/60%. Same shift across all forecast years. This simulation always starts from the saved Base case, not active slider overrides. These are assumption ranges, not empirical confidence intervals.')
with tabs[4]:
    st.dataframe(pd.DataFrame(audit(data)),hide_index=True)
    st.dataframe(pd.DataFrame(data['records']),hide_index=True)
    st.write('All PDF references use physical PDF page numbers, including cover/auditor pages. Raw source values are IDR thousand. Model values divide them by 1,000,000 to obtain IDR billion.')
    for p in data['peers']:st.markdown(f"[{p['ticker']} market inputs]({p['source']}) · [Business profile]({p['profile_source']})")
    st.markdown(f"[DEWA market price]({data['market']['price_source']}) · [KSEI issued shares]({data['market']['shares_source']})")
    for item in data['limitations']:st.write('• '+item)
    st.download_button('Download input register',(st.session_state.get('_unused','') or (json.dumps(data,indent=2))),'VISTA_inputs.json','application/json')

with st.expander("Download project deliverables"):
    for label,name in [("Excel valuation workbook","VISTA_Valuation.xlsx"),("Methodological report","VISTA_Methodology.pdf"),("Valuation slides (PDF)","VISTA_Pitch.pdf")]:
        document = ROOT / name
        if document.is_file():
            st.download_button(label,document.read_bytes(),file_name=name)
        else:
            st.info(f"{label} is not available yet.")

st.caption('VISTA · Developed by Ariel Arviano Putra · 29125401')
