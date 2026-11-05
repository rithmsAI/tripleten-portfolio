import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {MODEL_NAMES,selectSessions,summarize,simulate,validateBundle} from '../assets/core.mjs';
const bundle=JSON.parse(readFileSync(new URL('../assets/research.json',import.meta.url),'utf8'));
const near=(a,b)=>assert.ok(Math.abs(a-b)<1e-9,`${a} differs from ${b}`);
const row=(actual,prediction,lower,date='2025-01-02')=>({date,actual,forecasts:{ridge:{prediction,lower,upper:Math.max(prediction,lower)+.1},zero:{prediction:0,lower:-.1,upper:.1}}});

for(const asset of bundle.assets)test(`${asset.symbol}: browser calculations reconcile with every Python model`,()=>{
  assert.equal(asset.sessions.length,189);
  for(const model of Object.keys(MODEL_NAMES)){
    const m=summarize(asset.sessions,model),s=simulate(asset.sessions,model),p=asset.report.metrics[model];
    near(m.mae,p.mae);near(m.rmse,p.rmse);near(m.direction,p.direction_accuracy);
    near(m.coverage,p.interval_coverage);near(m.width,p.mean_interval_width);
    near(s.netReturn,p.simulated_net_return);near(s.maxDrawdown,p.simulated_max_drawdown);
    near(s.benchmarkReturn,p.always_long_intraday_net_return);assert.equal(s.trades,p.simulated_trades);
  }
});
test('window and regime filters preserve order and intersection',()=>{
  const asset=bundle.assets[0],fold=selectSessions(asset,{fold:'2'});assert.equal(fold.length,63);
  const selected=selectSessions(asset,{fold:'2',regime:'higher'});
  assert.ok(selected.every(r=>r.fold===2&&r.regime==='higher'));
  assert.deepEqual(selected.map(r=>r.date),selected.map(r=>r.date).sort());
});
test('fees and slippage charge both entry and exit',()=>{
  const r=simulate([row(0,.1,.09)],'ridge',{fee:50,slippage:50});
  near(r.netReturn,.99/1.01-1);assert.equal(r.trades,1);assert.equal(r.winRate,0);
});
test('drawdown includes the loss on the first trade',()=>{
  const r=simulate([row(-.1,.1,.09)],'ridge',{fee:0,slippage:0});near(r.maxDrawdown,-.1);
});
test('abstention has zero costs, zero drawdown and no win-rate claim',()=>{
  const r=simulate([row(-.2,0,-.1)],'ridge');
  near(r.netReturn,0);near(r.maxDrawdown,0);assert.equal(r.trades,0);assert.equal(r.winRate,null);
});
test('point-forecast rule is distinguished from interval entry',()=>{
  const rows=[row(.01,.02,-.01)];assert.equal(simulate(rows,'ridge').trades,0);
  assert.equal(simulate(rows,'ridge',{policy:'point'}).trades,1);
});
test('entry buffer and higher costs cannot introduce additional entries',()=>{
  for(const asset of bundle.assets){
    const rows=asset.sessions;
    assert.ok(simulate(rows,'ridge',{policy:'point',fee:30,slippage:30}).trades<=simulate(rows,'ridge',{policy:'point',fee:0,slippage:0}).trades);
    assert.ok(simulate(rows,'ridge',{policy:'point',threshold:100}).trades<=simulate(rows,'ridge',{policy:'point'}).trades);
  }
});
test('invalid numeric simulation settings are rejected',()=>{
  for(const value of [-1,NaN,Infinity,501])assert.throws(()=>simulate([],'ridge',{fee:value}));
  assert.throws(()=>simulate([],'ridge',{policy:'unknown'}));
});
test('empty selections never invent observations or trade success',()=>{
  assert.equal(summarize([],'ridge'),null);const s=simulate([],'ridge');assert.equal(s.trades,0);assert.equal(s.winRate,null);assert.deepEqual(s.series,[]);
});
test('interval coverage includes exact boundary observations',()=>{
  const r=row(-.01,0,-.01);r.forecasts.ridge.upper=.01;near(summarize([r],'ridge').coverage,1);
});
test('research bundle validation rejects reversed dates and malformed bounds',()=>{
  validateBundle(bundle);
  const a=structuredClone(bundle);a.assets[0].sessions.reverse();assert.throws(()=>validateBundle(a));
  const b=structuredClone(bundle);b.assets[0].sessions[0].forecasts.ridge.lower=9;assert.throws(()=>validateBundle(b));
});


test('public bundle contains invented sequences with no market-provider provenance',()=>{
  assert.equal(bundle.dataKind,'synthetic');
  for(const a of bundle.assets){
    assert.ok(a.symbol.startsWith('DEMO-'));
    assert.equal(a.provenance.kind,'synthetic');
    assert.equal(a.report.data_kind,'synthetic');
    assert.equal(a.provenance.provider,'Independent synthetic generator');
  }
});
