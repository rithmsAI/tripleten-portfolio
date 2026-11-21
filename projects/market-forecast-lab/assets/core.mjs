// Pure research calculations shared by the interface and Node's test runner.
export const MODEL_NAMES = {zero:'Zero return',historical_mean:'Historical mean',ridge:'Ridge regression',boosted_trees:'Boosted trees'};
export function selectSessions(asset, {fold='all',regime='all'}={}) {
  return asset.sessions.filter(r=>(fold==='all'||r.fold===Number(fold))&&(regime==='all'||r.regime===regime));
}
export function summarize(rows, model) {
  if(!rows.length) return null;
  let absolute=0,squared=0,direction=0,coverage=0,width=0,baseline=0;
  for(const r of rows){const f=r.forecasts[model],e=r.actual-f.prediction;
    absolute+=Math.abs(e);squared+=e*e;direction+=Number((f.prediction>0)===(r.actual>0));
    coverage+=Number(r.actual>=f.lower&&r.actual<=f.upper);width+=f.upper-f.lower;
    baseline+=Math.abs(r.actual-r.forecasts.zero.prediction);
  }
  const n=rows.length,mae=absolute/n;
  return {n,mae,rmse:Math.sqrt(squared/n),direction:direction/n,coverage:coverage/n,width:width/n,
    baselineMAE:baseline/n,skill:baseline>0?1-absolute/baseline:0};
}
export function simulate(rows,model,{fee=5,slippage=5,threshold=0,policy='interval'}={}) {
  if(![fee,slippage,threshold].every(x=>Number.isFinite(x)&&x>=0&&x<=500)||!['interval','point'].includes(policy)) throw Error('Invalid simulation configuration');
  const c=(fee+slippage)/10000,gate=2*c+threshold/10000;
  let equity=1,benchmark=1,peak=1,drawdown=0,trades=0,wins=0;
  const series=rows.map(r=>{
    const f=r.forecasts[model],entered=(policy==='interval'?f.lower:f.prediction)>gate;
    const costAdjusted=(1+r.actual)*(1-c)/(1+c)-1;
    const net=entered?costAdjusted:0;
    equity*=1+net;benchmark*=1+costAdjusted;peak=Math.max(peak,equity);
    drawdown=Math.min(drawdown,equity/peak-1);
    if(entered){trades++;wins+=Number(net>0);}
    return {date:r.date,entered,net,equity,benchmark};
  });
  return {netReturn:equity-1,benchmarkReturn:benchmark-1,maxDrawdown:drawdown,trades,
    winRate:trades?wins/trades:null,series};
}
export function validateBundle(bundle){
  if(bundle?.dataKind!=='synthetic'||bundle?.schemaVersion!==1||!Array.isArray(bundle.assets)||!bundle.assets.length)throw Error('Unsupported research bundle');
  for(const a of bundle.assets){
    if(!/^[A-Z0-9-]+$/.test(a.symbol)||!Array.isArray(a.sessions)||!a.sessions.length)throw Error('Invalid asset data');
    let prior='';
    for(const r of a.sessions){
      if(!/^\d{4}-\d{2}-\d{2}$/.test(r.date)||r.date<=prior||!Number.isFinite(r.actual)||r.actual<=-1)throw Error('Invalid session order or return');
      prior=r.date;
      for(const model of Object.keys(MODEL_NAMES)){
        const f=r.forecasts?.[model];
        if(!f||![f.prediction,f.lower,f.upper].every(Number.isFinite)||f.lower>f.prediction||f.prediction>f.upper)throw Error('Invalid forecast interval');
      }
    }
  }
  return bundle;
}
