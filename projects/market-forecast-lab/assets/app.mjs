import {MODEL_NAMES,selectSessions,summarize,simulate,validateBundle} from './core.mjs';
const $=id=>document.getElementById(id),escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=(v,d=1,sign=false)=>v==null?'—':`${sign&&v>0?'+':''}${(v*100).toFixed(d)}%`;
const date=(s,short=false)=>new Intl.DateTimeFormat('en-US',{month:'short',day:'numeric',...(short?{}:{year:'numeric'}),timeZone:'UTC'}).format(new Date(s+'T00:00:00Z'));
let data,asset,rows=[],state={model:'ridge',fold:'all',regime:'all',view:'interval',index:188},simConfig={fee:5,slippage:5,threshold:0,policy:'interval'};
const color={mint:'#b5e9df',ivory:'#e9efed',copper:'#dca37f',muted:'#78919c'};

function spark(values){const lo=Math.min(...values),span=Math.max(...values)-lo||1;return `<svg viewBox="0 0 90 27" aria-hidden="true"><polyline fill="none" stroke="${color.mint}" stroke-width="1.4" points="${values.map((v,i)=>`${i*90/(values.length-1)},${25-(v-lo)/span*22}`).join(' ')}"/></svg>`;}
function renderAssets(){
  $('asset-picker').innerHTML=data.assets.map(a=>`<button class="asset-card" data-symbol="${escape(a.symbol)}" aria-pressed="${a.symbol===asset.symbol}"><span class="asset-type">${escape(a.assetClass)}</span><strong>${escape(a.symbol)}</strong><small>${escape(a.name)}</small><span class="asset-bottom">${a.sessions.length} held-out sessions ${spark(a.sessions.slice(-30).map(r=>r.actual))}</span></button>`).join('');
  $('asset-picker').querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{asset=data.assets.find(a=>a.symbol===b.dataset.symbol);state.index=Infinity;render();}));
}
function render(){
  renderAssets();rows=selectSessions(asset,state);state.index=Math.max(0,Math.min(state.index,rows.length-1));
  $('asset-title').textContent=`${asset.symbol} · ${asset.name}`;
  $('asset-meta').textContent=`${asset.assetClass.toUpperCase()} / ${asset.report.input_rows_used.toLocaleString()} input bars / Invented bars through ${date(asset.report.last_date)}`;
  $('window-label').textContent=rows.length?`${date(rows[0].date,true)} — ${date(rows.at(-1).date,true)} · ${rows.length} sessions`:'No sessions match this selection';
  const m=summarize(rows,state.model);
  const kpis=m?[
    ['Mean absolute error',pct(m.mae,3),`${Math.abs(m.skill*100).toFixed(1)}% ${m.skill>0?'less':'more'} error vs zero`,m.skill>0?'positive':'negative'],
    ['Direction accuracy',pct(m.direction),`${rows.length} observed sessions · not confidence`,''],
    ['Interval coverage',pct(m.coverage),`90% nominal target · empirical coverage`,Math.abs(m.coverage-.9)>.05?'neutral':''],
    ['Mean interval width',pct(m.width,2),'Inspect coverage alongside interval width','']
  ]:[['Mean absolute error','—','No sessions selected',''],['Direction accuracy','—','No sessions selected',''],['Interval coverage','—','No sessions selected',''],['Mean interval width','—','No sessions selected','']];
  $('kpis').innerHTML=kpis.map(([label,value,note,tone])=>`<div class="kpi"><div class="kpi-label">${label}</div><div class="kpi-value">${value}</div><div class="kpi-note ${tone}">${note}</div></div>`).join('');
  $('session').max=Math.max(0,rows.length-1);$('session').value=state.index;$('session').disabled=!rows.length;
  $('download-csv').disabled=!rows.length;
  $('chart-start').textContent=rows.length?date(rows[0].date,true):'';$('chart-end').textContent=rows.length?date(rows.at(-1).date,true):'';
  renderForecast();renderInspector();renderComparison();renderRegimes();renderSimulation();renderEvidence();
}
function chartBase(values,{baseline=0}={}){
  let low=Math.min(...values,baseline),high=Math.max(...values,baseline);const pad=Math.max((high-low)*.1,.0005);low-=pad;high+=pad;
  const W=960,H=310,left=48,right=18,top=18,bottom=28,x=(i,n)=>left+i*(W-left-right)/Math.max(n-1,1),y=v=>H-bottom-(v-low)/(high-low)*(H-top-bottom);
  const grid=Array.from({length:5},(_,i)=>{const v=low+(high-low)*i/4;return `<line x1="${left}" x2="${W-right}" y1="${y(v)}" y2="${y(v)}" class="chart-grid"/><text class="chart-tick" x="${left-9}" y="${y(v)+4}" text-anchor="end">${pct(v,1)}</text>`;}).join('');
  return {W,H,left,right,top,bottom,x,y,grid,low,high};
}
function line(values,c,n=values.length){return values.map((v,i)=>`${c.x(i,n).toFixed(2)},${c.y(v).toFixed(2)}`).join(' ');}
function renderForecast(){
  const box=$('forecast-chart');
  if(!rows.length){box.innerHTML='<div class="empty-chart">No sessions in this volatility group.<br>Choose another group or evaluation fold.</div>';return;}
  const fs=rows.map(r=>r.forecasts[state.model]),actual=rows.map(r=>r.actual),pred=fs.map(f=>f.prediction),lower=fs.map(f=>f.lower),upper=fs.map(f=>f.upper),error=rows.map((r,i)=>pred[i]-r.actual);
  const uncertainty=state.view==='interval',c=chartBase(uncertainty?[...actual,...lower,...upper]:error),zero=c.y(0);
  const band=uncertainty?`<polygon points="${line(upper,c)} ${line(lower,c).split(' ').reverse().join(' ')}" fill="${color.copper}" opacity=".09"/><polyline points="${line(lower,c)}" fill="none" stroke="${color.copper}" opacity=".45" stroke-width="1"/><polyline points="${line(upper,c)}" fill="none" stroke="${color.copper}" opacity=".45" stroke-width="1"/>`:'';
  box.innerHTML=`<svg viewBox="0 0 ${c.W} ${c.H}" role="img" aria-label="${uncertainty?'Forecast, realized returns and nominal 90 percent intervals':'Prediction error: forecast minus realized return'} for ${escape(asset.symbol)}. Use the session slider for exact values."><title>${escape(asset.symbol)} historical forecast explorer</title>${c.grid}<line x1="${c.left}" x2="${c.W-c.right}" y1="${zero}" y2="${zero}" stroke="#66818e" stroke-dasharray="4 5" opacity=".6"/>${band}${uncertainty?`<polyline points="${line(pred,c)}" fill="none" stroke="${color.ivory}" stroke-width="1.5" opacity=".8"/>`:''}<polyline points="${line(uncertainty?actual:error,c)}" fill="none" stroke="${color.mint}" stroke-width="1.8" stroke-linejoin="round"/><g id="chart-crosshair" class="chart-selection"></g></svg>`;
  const svg=box.querySelector('svg');
  svg.addEventListener('pointermove',e=>{const r=svg.getBoundingClientRect();const vx=(e.clientX-r.left)/r.width*c.W;state.index=Math.max(0,Math.min(rows.length-1,Math.round((vx-c.left)/(c.W-c.left-c.right)*(rows.length-1))));$('session').value=state.index;renderInspector();updateCrosshair(c);});
  updateCrosshair(c);
}
function updateCrosshair(c){
  const node=$('chart-crosshair');if(!node||!rows.length)return;
  if(!c){const fs=rows.map(r=>r.forecasts[state.model]);c=chartBase(state.view==='interval'?[...rows.map(r=>r.actual),...fs.map(f=>f.lower),...fs.map(f=>f.upper)]:rows.map(r=>r.forecasts[state.model].prediction-r.actual));}
  const row=rows[state.index],v=state.view==='interval'?row.actual:row.forecasts[state.model].prediction-row.actual,x=c.x(state.index,rows.length);
  node.innerHTML=`<line x1="${x}" x2="${x}" y1="${c.top}" y2="${c.H-c.bottom}" stroke="${color.mint}" opacity=".45" stroke-dasharray="3 4"/><circle cx="${x}" cy="${c.y(v)}" r="4" fill="${color.mint}" stroke="#10232b" stroke-width="2"/>`;
}
function renderInspector(){
  if(!rows.length){$('inspect-date').textContent='No selected session';$('inspect-feature').textContent='';$('inspect-prediction').textContent='—';$('inspect-details').innerHTML='';$('inspect-status').textContent='NO OBSERVATIONS';return;}
  const r=rows[state.index],f=r.forecasts[state.model];
  $('inspect-date').textContent=date(r.date);$('inspect-feature').textContent=`Features completed ${date(r.featureDate,true)} · Fold ${r.fold}`;
  $('inspect-prediction').textContent=pct(f.prediction,2,true);
  const entries=[['Realized return',pct(r.actual,2,true)],['90% interval',`${pct(f.lower,2)} to ${pct(f.upper,2)}`],['Volatility group',r.regime[0].toUpperCase()+r.regime.slice(1)],['Rolling RSI (14)',(r.indicators.rsi_14*100).toFixed(1)],['20-session return',pct(r.indicators.return_20,2,true)],['EMA gap (20)',pct(r.indicators.ema_gap,2,true)]];
  $('inspect-details').innerHTML=entries.map(([k,v])=>`<div class="inspect-row"><span>${k}</span><strong>${escape(v)}</strong></div>`).join('');
  $('inspect-status').textContent=f.lower>.002?'DEFAULT RULE: LONG CANDIDATE':'DEFAULT RULE: ABSTAIN';
}
function renderComparison(){
  $('comparison').innerHTML=Object.entries(MODEL_NAMES).map(([key,name])=>{const m=summarize(rows,key);return `<tr class="${key===state.model?'highlight':''}"><th scope="row">${name}${key===state.model?'<span class="selected-dot">●</span>':''}</th><td>${m?pct(m.mae,3):'—'}</td><td>${m?pct(m.direction):'—'}</td><td>${m?pct(m.coverage):'—'}</td><td class="${m&&m.skill>0?'positive':m&&m.skill<0?'negative':'muted'}">${m?pct(m.skill,1,true):'—'}</td></tr>`;}).join('');
}
function renderRegimes(){
  const windowRows=selectSessions(asset,{fold:state.fold}),groups=['lower','middle','higher'].map(key=>({key,rows:windowRows.filter(r=>r.regime===key)})),max=Math.max(1,...groups.map(g=>g.rows.length));
  $('regime-breakdown').innerHTML=groups.map(g=>{const m=summarize(g.rows,state.model);return `<div class="regime-row"><div><span>${g.key[0].toUpperCase()+g.key.slice(1)} volatility</span><small>${g.rows.length} sessions${g.rows.length<20?' · small sample':''}</small></div><div class="regime-track"><i style="width:${g.rows.length/max*100}%"></i></div><div class="regime-foot"><span>MAE ${m?pct(m.mae,3):'—'}</span><span class="${m&&m.skill<0?'negative':'positive'}">${m?`${pct(m.skill,1,true)} vs zero`:'No observations'}</span></div></div>`;}).join('');
}
function renderSimulation(){
  for(const key of ['fee','slippage','threshold'])$(key+'-value').textContent=`${simConfig[key]} bps`;
  const result=simulate(rows,state.model,simConfig);
  const cards=[['Net return',rows.length?pct(result.netReturn,2,true):'—',result.netReturn<0?'negative':'positive'],['Max drawdown',rows.length?pct(result.maxDrawdown,2):'—',''],['Round trips',String(result.trades),''],['Profitable trades',pct(result.winRate),'']];
  $('sim-kpis').innerHTML=cards.map(([label,value,tone])=>`<div><span>${label}</span><strong class="${tone}">${value}</strong><small>${label==='Profitable trades'?(result.trades?(result.trades<20?`Small sample · ${result.trades} trades`:'After modeled costs'):'No trades entered'):label==='Round trips'?`${rows.length} selected sessions`:label==='Net return'?'Compounded research notional':'From the prior equity peak'}</small></div>`).join('');
  if(rows.length){
    // Include starting cash so losses on the first session appear as drawdowns.
    const strategy=[0,...result.series.map(r=>r.equity-1)],benchmark=[0,...result.series.map(r=>r.benchmark-1)],c=chartBase([...strategy,...benchmark]);
    $('equity-chart').innerHTML=`<svg viewBox="0 0 ${c.W} ${c.H}" role="img" aria-label="Compounded strategy and always-long intraday net return, including initial cash"><title>Exploratory cost-sensitive return simulation</title>${c.grid}<line x1="${c.left}" x2="${c.W-c.right}" y1="${c.y(0)}" y2="${c.y(0)}" stroke="#66818e" stroke-dasharray="4 5"/><polyline points="${line(benchmark,c)}" fill="none" stroke="${color.copper}" stroke-width="2" opacity=".8"/><polyline points="${line(strategy,c)}" fill="none" stroke="${color.mint}" stroke-width="2.4"/></svg>`;
  }else $('equity-chart').innerHTML='<div class="empty-chart">Select a window with observed sessions.</div>';
  const gapNote=state.regime!=='all'?'Only selected volatility-group sessions are included; omitted dates are excluded from this exploratory comparison. ':'';
  $('sim-note').textContent=gapNote+(result.trades===0?'The rule abstains throughout this selection. Zero return reflects holding cash; it is not evidence of a profitable strategy. ':`${result.trades} modeled round trips. Always-long intraday return over these sessions: ${pct(result.benchmarkReturn,2,true)}. `)+(simConfig.policy==='point'?'Point-forecast entry ignores interval uncertainty. This exploratory rule differs from the original conservative evaluation.':'The interval rule requires its lower bound to clear estimated round-trip costs plus the entry buffer.');
}
function renderEvidence(){
  const b=asset.report.boundaries,total=asset.report.input_rows_used;
  $('split-timeline').innerHTML=b.map(f=>{const training=100*f.train_rows/total,cal=100*asset.report.config.calibration_size/total,test=100*asset.report.config.test_size/total;return `<div class="fold-item"><div class="fold-title"><span>FOLD ${f.fold} · ${f.train_rows} training rows</span><span>Test: ${date(f.test_first_target,true)} — ${date(f.test_last_target,true)}</span></div><div class="fold-graphic" role="img" aria-label="Fold ${f.fold}: ${f.train_rows} training rows, 63 calibration rows, two one-row gaps and 63 test rows"><i class="train-block" style="width:${training}%"></i><i class="cal-block" style="width:${cal}%"></i><i class="test-block" style="width:${test}%"></i></div></div>`;}).join('');
  const entries=[['Provider',asset.provenance.provider],['Input range',`${asset.report.first_date} → ${asset.report.last_date}`],['Target window',`${asset.sessions[0].date} → ${asset.sessions.at(-1).date}`],['Price basis',asset.provenance.price_basis],['Generator',`Independent synthetic fixture · seed ${asset.provenance.seed}`],['Model stack',`scikit-learn ${asset.report.versions.scikit_learn} · NumPy ${asset.report.versions.numpy}`]];
  $('provenance').innerHTML=entries.map(([k,v])=>`<dt>${k}</dt><dd>${escape(v)}</dd>`).join('');$('input-hash').textContent=asset.report.input_sha256;
}
function download(filename,body,type){const blob=new Blob([body],{type}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function exportCSV(){
  const result=simulate(rows,state.model,simConfig),header='symbol,model,target_date,feature_date,fold,volatility_regime,actual_return,predicted_return,lower,upper,fee_bps_per_side,slippage_bps_per_side,entry_buffer_bps,exploratory_policy,exploratory_entered,exploratory_net_return,exploratory_equity';
  const lines=rows.map((r,i)=>{const f=r.forecasts[state.model],s=result.series[i];return [asset.symbol,state.model,r.date,r.featureDate,r.fold,r.regime,r.actual,f.prediction,f.lower,f.upper,simConfig.fee,simConfig.slippage,simConfig.threshold,simConfig.policy,s.entered,s.net,s.equity].join(',');});
  download(`RithmScope_${asset.symbol}_${state.model}_selection.csv`,[header,...lines].join('\n')+'\n','text/csv;charset=utf-8');
}
function wire(){
  for(const key of ['model','fold','regime'])$(key).addEventListener('change',()=>{state[key]=$(key).value;state.index=Infinity;render();});
  $('session').addEventListener('input',()=>{state.index=Number($('session').value);renderInspector();updateCrosshair();});
  for(const view of ['interval','error'])$('view-'+view).addEventListener('click',()=>{state.view=view;for(const v of ['interval','error']){$('view-'+v).classList.toggle('selected',v===view);$('view-'+v).setAttribute('aria-pressed',String(v===view));}document.querySelector('.chart-panel .chart-legend').style.visibility=view==='interval'?'visible':'hidden';renderForecast();});
  for(const key of ['fee','slippage','threshold'])$(key).addEventListener('input',()=>{simConfig[key]=Number($(key).value);renderSimulation();});
  $('policy').addEventListener('change',()=>{simConfig.policy=$('policy').value;renderSimulation();});
  $('reset-sim').addEventListener('click',()=>{simConfig={fee:5,slippage:5,threshold:0,policy:'interval'};for(const k of ['fee','slippage','threshold','policy'])$(k).value=simConfig[k];renderSimulation();});
  $('download-csv').addEventListener('click',exportCSV);
  $('download-json').addEventListener('click',()=>download(`RithmScope_${asset.symbol}_research.json`,JSON.stringify({schemaVersion:1,scope:data.scope,dataKind:data.dataKind,asset,selection:{...state},exploratorySimulation:{...simConfig,result:simulate(rows,state.model,simConfig)},warning:'Sandbox results reuse observed outcomes; they are not an untouched evaluation.'},null,2),'application/json'));
  $('reproduce-top').addEventListener('click',()=>$('reproduce-dialog').showModal());$('close-dialog').addEventListener('click',()=>$('reproduce-dialog').close());
  document.querySelectorAll('nav a').forEach(a=>a.addEventListener('click',()=>{document.querySelectorAll('nav a').forEach(n=>n.classList.toggle('active',n===a));}));
}
async function start(){try{
  const response=await fetch(new URL('./research.json',import.meta.url));if(!response.ok)throw Error(`Research bundle could not load (${response.status})`);
  data=validateBundle(await response.json());asset=data.assets.find(a=>a.symbol==='DEMO-CRYPTO-A')||data.assets[0];
  wire();$('research-content').hidden=false;render();
}catch(error){$('load-error').hidden=false;$('load-error').textContent=`Could not load the dashboard: ${error.message}. Open the GitHub README for the research results.`;$('asset-picker').innerHTML='';}}
start();
