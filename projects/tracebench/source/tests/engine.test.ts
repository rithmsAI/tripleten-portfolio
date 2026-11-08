import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {parseDataset,evaluate,evaluateOutput,percentile,summarize,assess,report} from '../src/engine.js';
const raw=readFileSync(new URL('../public/example-dataset.json',import.meta.url),'utf8');
const fresh=()=>parseDataset(raw);
const gates={minimumPassRate:.8,maximumP95:1500,maximumCost:.05,blockCriticalRegressions:true};
test('paired fixture improves aggregate while retaining a critical regression',()=>{const r=evaluate(fresh());assert.equal(r.length,12);assert.equal(r.filter(x=>x.change==='improved').length,5);assert.equal(r.filter(x=>x.change==='regressed').length,2);assert.equal(summarize(r,'baseline').passRate,7/12);assert.equal(summarize(r,'candidate').passRate,10/12);assert.equal(assess(r,gates).passed,false);assert.equal(assess(r,gates).critical,1);});
test('critical blocker remains when numerical gates are relaxed',()=>{assert.equal(assess(evaluate(fresh()),{...gates,minimumPassRate:0}).passed,false);});
test('disabling critical blocker is an explicit decision',()=>{assert.equal(assess(evaluate(fresh()),{...gates,blockCriticalRegressions:false}).passed,true);});
test('latency and cost boundaries are inclusive',()=>{const rows=evaluate(fresh()),s=summarize(rows,'candidate');assert.equal(assess(rows,{...gates,blockCriticalRegressions:false,maximumP95:s.p95,maximumCost:s.cost}).passed,true);assert.equal(assess(rows,{...gates,blockCriticalRegressions:false,maximumP95:s.p95-1}).passed,false);assert.equal(assess(rows,{...gates,blockCriticalRegressions:false,maximumCost:s.cost-.001}).passed,false);});
test('nearest-rank p95 handles small samples and does not mutate inputs',()=>{const v=[30,10,20];assert.equal(percentile(v,.95),30);assert.equal(percentile(v,.5),20);assert.deepEqual(v,[30,10,20]);assert.equal(percentile([], .95),0);assert.throws(()=>percentile([1],2));});
test('unknown citation fails even when a valid citation is also present',()=>{const c=fresh().cases[0];assert.equal(evaluateOutput(c,{...c.candidate,citations:['S1','unknown']})[1].passed,false);});
test('required but absent citation fails',()=>{const c=fresh().cases[0];assert.equal(evaluateOutput(c,{...c.candidate,citations:[]})[1].passed,false);});
test('matching normalizes case, unicode width, and whitespace',()=>{const c=fresh().cases[0];assert.equal(evaluateOutput(c,{...c.candidate,answer:'Available for ９０   DAYS.'})[0].passed,true);});
test('phrase match is deliberately lexical, including negation blind spot',()=>{const c=fresh().cases[0];assert.equal(evaluateOutput(c,{...c.candidate,answer:'It is NOT 90 days.'})[0].passed,true);});
test('abstention is metadata, not interpreted prose',()=>{const c=fresh().cases[3];assert.equal(evaluateOutput(c,{...c.candidate,abstained:false})[2].passed,false);});
test('rejects malformed JSON and unsupported schema',()=>{assert.throws(()=>parseDataset('{'));assert.throws(()=>parseDataset(JSON.stringify({...fresh(),schemaVersion:2})));});
test('rejects empty and oversized datasets',()=>{assert.throws(()=>parseDataset(JSON.stringify({...fresh(),cases:[]})));assert.throws(()=>parseDataset(' '.repeat(1000001)));assert.throws(()=>parseDataset(JSON.stringify({...fresh(),cases:Array(201).fill(fresh().cases[0])})));});
test('rejects duplicate case IDs',()=>{const d=fresh();d.cases[1].id=d.cases[0].id;assert.throws(()=>parseDataset(JSON.stringify(d)),/Duplicate case/);});
test('rejects duplicate source IDs and impossible citation requirements',()=>{const d=fresh();d.cases[0].sources.push(d.cases[0].sources[0]);assert.throws(()=>parseDataset(JSON.stringify(d)),/Duplicate source/);d.cases[0].sources=[];assert.throws(()=>parseDataset(JSON.stringify(d)),/need at least one source/);});
test('rejects negative, string, null, or infinite numeric measurements',()=>{for(const v of [-1,'2',null,Infinity]){const d:any=fresh();d.cases[0].candidate.costUsd=v;assert.throws(()=>parseDataset(JSON.stringify(d)));}});
test('rejects truthy string labels and duplicate citations',()=>{const d:any=fresh();d.cases[0].expectedAbstention='false';assert.throws(()=>parseDataset(JSON.stringify(d)));d.cases[0].expectedAbstention=false;d.cases[0].candidate.citations=['S1','S1'];assert.throws(()=>parseDataset(JSON.stringify(d)));});
test('all pass requires every independent check',()=>{const d=fresh();d.cases=[d.cases[0]];d.cases[0].candidate.abstained=true;assert.equal(evaluate(d)[0].candidatePass,false);});
test('export re-evaluation is deterministic and human notes cannot override scores',()=>{const d=fresh();const before=report(d,gates),after=report(d,gates,{'TB-003':'Approve manually'});assert.deepEqual(before.results,after.results);assert.deepEqual(before.decision,after.decision);assert.deepEqual(evaluate(parseDataset(JSON.stringify(after.dataset))),evaluate(d));});
test('empty results can never satisfy release criteria',()=>{assert.equal(assess([],{...gates,minimumPassRate:0}).passed,false);});
test('HTML payloads remain strings in evaluation reports',()=>{const d=fresh();d.cases[0].candidate.answer='<img src=x onerror=alert(1)> 90 days';const r=report(parseDataset(JSON.stringify(d)),gates);assert.equal(r.dataset.cases[0].candidate.answer,d.cases[0].candidate.answer);});

test('rejects invalid numeric gate configuration instead of issuing a decision',()=>{
 const rows=evaluate(fresh());
 for(const change of [{minimumPassRate:-.1},{minimumPassRate:1.1},{minimumPassRate:NaN},{maximumP95:Infinity},{maximumP95:-1},{maximumCost:-1},{maximumCost:NaN},{maximumCost:'1'}]){
  assert.throws(()=>assess(rows,{...gates,...change} as any),/gate/i);
 }
});
test('requires an explicit boolean critical-regression gate',()=>{
 for(const blockCriticalRegressions of [undefined,null,0,'false']){
  assert.throws(()=>assess(evaluate(fresh()),{...gates,blockCriticalRegressions} as any),/gate/i);
 }
});
test('rejects imported costs whose aggregate overflows JSON numbers',()=>{
 for(const side of ['baseline','candidate'] as const){
  const d=fresh();d.cases[0][side].costUsd=1e308;d.cases[1][side].costUsd=1e308;
  assert.throws(()=>parseDataset(JSON.stringify(d)),/total.*cost/i);
 }
});
test('reports reject unknown, non-text, and overlong review notes',()=>{
 for(const reviews of [{unknown:'Observation'},{'TB-003':42},{'TB-003':'x'.repeat(4001)}]){
  assert.throws(()=>report(fresh(),gates,reviews as any),/review/i);
 }
});
test('reports reject invalid gates before export',()=>{
 assert.throws(()=>report(fresh(),{...gates,maximumCost:Infinity}),/gate/i);
});
test('valid reports remain finite and deterministic after JSON round trip',()=>{
 const first=report(fresh(),gates,{'TB-003':'Human review required.'});
 assert.deepEqual(JSON.parse(JSON.stringify(first)),first);
 assert.equal(first.candidate.cost,report(fresh(),gates).candidate.cost);
});
