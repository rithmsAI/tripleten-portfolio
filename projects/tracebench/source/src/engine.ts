export const ENGINE_VERSION = '1.1.0';
export type Output = {answer:string; citations:string[]; abstained:boolean; latencyMs:number; costUsd:number};
export type Case = {id:string; category:string; risk:'standard'|'critical'; prompt:string; sources:{id:string;text:string}[]; requiredPhrases:string[]; expectedAbstention:boolean; requireCitation:boolean; baseline:Output; candidate:Output};
export type Dataset = {schemaVersion:1; name:string; provenance:string; cases:Case[]};
export type Check = {name:string; passed:boolean; detail:string};
export type Result = {case:Case; baseline:Check[]; candidate:Check[]; baselinePass:boolean; candidatePass:boolean; change:'improved'|'regressed'|'unchanged'};
export type Gates = {minimumPassRate:number; maximumP95:number; maximumCost:number; blockCriticalRegressions:boolean};
function record(x:unknown): x is Record<string,unknown> {return typeof x==='object' && x!==null && !Array.isArray(x);}
function str(x:unknown,label:string,max=10000): asserts x is string {if(typeof x!=='string'||!x.trim()||x.length>max) throw Error(`${label}: expected nonempty text (max ${max} characters).`);}
function bool(x:unknown,label:string): asserts x is boolean {if(typeof x!=='boolean') throw Error(`${label}: expected true or false.`);}
function strings(x:unknown,label:string): asserts x is string[]{if(!Array.isArray(x)||x.length>50)throw Error(`${label}: expected an array of up to 50 strings.`); x.forEach(v=>str(v,label,1000)); if(new Set(x).size!==x.length)throw Error(`${label}: duplicate values.`);}
function output(x:unknown,label:string):asserts x is Output {if(!record(x))throw Error(`${label}: missing output.`);str(x.answer,`${label}.answer`);strings(x.citations,`${label}.citations`);bool(x.abstained,`${label}.abstained`); for(const k of ['latencyMs','costUsd'])if(typeof x[k]!=='number'||!Number.isFinite(x[k])||x[k]<0)throw Error(`${label}.${k}: expected a finite nonnegative number.`);}
export function parseDataset(raw:string):Dataset {
 if(new TextEncoder().encode(raw).length>1_000_000)throw Error('Dataset exceeds the 1 MB limit.');
 let d:unknown;try{d=JSON.parse(raw);}catch{throw Error('Invalid JSON. Download the example dataset to see the format.');}
 if(!record(d)||d.schemaVersion!==1)throw Error('Expected schemaVersion: 1.');str(d.name,'name',200);str(d.provenance,'provenance',2000);
 if(!Array.isArray(d.cases)||d.cases.length<1||d.cases.length>200)throw Error('Expected between 1 and 200 cases.');
 const ids=new Set<string>();for(const c of d.cases){if(!record(c))throw Error('Invalid case.');str(c.id,'case.id',100);if(ids.has(c.id))throw Error(`Duplicate case ID: ${c.id}`);ids.add(c.id);str(c.category,'category',100);str(c.prompt,'prompt');if(!['standard','critical'].includes(c.risk as string))throw Error(`${c.id}: invalid risk.`);strings(c.requiredPhrases,'requiredPhrases');bool(c.expectedAbstention,'expectedAbstention');bool(c.requireCitation,'requireCitation');if(!Array.isArray(c.sources)||c.sources.length>30)throw Error(`${c.id}: expected up to 30 sources.`);const sourceIds=new Set();for(const s of c.sources){if(!record(s))throw Error('Invalid source.');str(s.id,'source.id',100);str(s.text,'source.text');if(sourceIds.has(s.id))throw Error('Duplicate source ID.');sourceIds.add(s.id);}if(c.requireCitation&&c.sources.length===0)throw Error(`${c.id}: required citations need at least one source.`);output(c.baseline,`${c.id}.baseline`);output(c.candidate,`${c.id}.candidate`);}
 const dataset=d as Dataset;
 for(const side of ['baseline','candidate'] as const){
  if(!Number.isFinite(dataset.cases.reduce((sum,c)=>sum+c[side].costUsd,0)))throw Error(`${side}: total cost exceeds the supported numeric range.`);
 }
 return dataset;
}
const normalized=(s:string)=>s.normalize('NFKC').toLowerCase().replace(/\s+/g,' ').trim();
export function evaluateOutput(c:Case,o:Output):Check[]{
 const missing=c.requiredPhrases.filter(p=>!normalized(o.answer).includes(normalized(p)));
 const unknown=o.citations.filter(id=>!c.sources.some(s=>s.id===id));
 return [
 {name:'Required phrases',passed:missing.length===0,detail:missing.length?`Missing: ${missing.join(', ')}`:'All required phrases found; this is lexical matching, not factual verification.'},
 {name:'Citation IDs',passed:unknown.length===0&&(!c.requireCitation||o.citations.length>0),detail:unknown.length?`Unknown source IDs: ${unknown.join(', ')}`:c.requireCitation&&o.citations.length===0?'At least one citation is required.':'IDs resolve to supplied sources; claim support still needs human review.'},
 {name:'Abstention flag',passed:o.abstained===c.expectedAbstention,detail:`Expected ${c.expectedAbstention}; supplied ${o.abstained}. The flag is supplied metadata, not a semantic refusal detector.`}
 ];
}
export function evaluate(d:Dataset):Result[]{return d.cases.map(c=>{const baseline=evaluateOutput(c,c.baseline),candidate=evaluateOutput(c,c.candidate),baselinePass=baseline.every(x=>x.passed),candidatePass=candidate.every(x=>x.passed);return {case:c,baseline,candidate,baselinePass,candidatePass,change:baselinePass===candidatePass?'unchanged':candidatePass?'improved':'regressed'};});}
export function percentile(values:number[],p:number):number {if(!values.length)return 0;if(p<0||p>1||!Number.isFinite(p))throw Error('Percentile must be between 0 and 1.');const sorted=[...values].sort((a,b)=>a-b);return sorted[Math.max(0,Math.ceil(p*sorted.length)-1)];}
export function summarize(rows:Result[],side:'baseline'|'candidate') {return {count:rows.length,passRate:rows.length?rows.filter(r=>side==='baseline'?r.baselinePass:r.candidatePass).length/rows.length:0,p95:percentile(rows.map(r=>r.case[side].latencyMs),.95),cost:rows.reduce((s,r)=>s+r.case[side].costUsd,0)};}
export function validateGates(g:unknown):asserts g is Gates {
 if(!record(g))throw Error('Release gates must be an object.');
 if(typeof g.minimumPassRate!=='number'||!Number.isFinite(g.minimumPassRate)||g.minimumPassRate<0||g.minimumPassRate>1)throw Error('Pass-rate gate must be a finite number between 0 and 1.');
 for(const field of ['maximumP95','maximumCost'])if(typeof g[field]!=='number'||!Number.isFinite(g[field])||g[field]<0)throw Error(`${field} gate must be a finite nonnegative number.`);
 if(typeof g.blockCriticalRegressions!=='boolean')throw Error('Critical-regression gate must be explicitly true or false.');
}
export function assess(rows:Result[],g:Gates){validateGates(g);const s=summarize(rows,'candidate');const critical=rows.filter(r=>r.change==='regressed'&&r.case.risk==='critical').length;const checks=[{label:'Pass-rate floor',passed:s.passRate>=g.minimumPassRate},{label:'p95 latency ceiling',passed:s.p95<=g.maximumP95},{label:'Total run-cost budget',passed:s.cost<=g.maximumCost},{label:g.blockCriticalRegressions?'No critical regressions':'Critical-regression block disabled',passed:!g.blockCriticalRegressions||critical===0}];return {passed:rows.length>0&&checks.every(x=>x.passed),checks,critical};}
export function report(d:Dataset,g:Gates,reviews:Record<string,string>={}){validateGates(g);if(!record(reviews))throw Error('Reviews must be an object.');const ids=new Set(d.cases.map(c=>c.id));for(const [id,note] of Object.entries(reviews)){if(!ids.has(id)||typeof note!=='string'||note.length>4000)throw Error('Review notes must reference an existing case and contain at most 4,000 characters.');}const rows=evaluate(d);return {engineVersion:ENGINE_VERSION,dataset:d,gates:g,decision:assess(rows,g),baseline:summarize(rows,'baseline'),candidate:summarize(rows,'candidate'),results:rows.map(r=>({id:r.case.id,change:r.change,baseline:r.baseline,candidate:r.candidate})),reviews,limitations:['Deterministic lexical and metadata checks only; no semantic correctness guarantee.','Latency and costs are supplied values, not measured by this application.','Synthetic fixture results do not estimate real-world model performance.','Human review notes do not change automated scores.']};}
