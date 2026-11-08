'use strict';
const NEXT={open:'investigating',investigating:'mitigated',mitigated:'resolved'};
const KEY='rithmsai-incident-workbench-v1';
let incidents=[],selected='INC-1042',storage=true,seq=0;
const $=s=>document.querySelector(s);
const el=(tag,text,cls)=>{const x=document.createElement(tag);if(text!==undefined)x.textContent=text;if(cls)x.className=cls;return x;};
function announce(text,error=false){$('#notice').textContent=text;$('#notice').className=error?'notice error':'notice';}
function persist(){try{localStorage.setItem(KEY,JSON.stringify({incidents,seq}));}catch{storage=false;announce('Browser storage is unavailable. Changes last only until this tab reloads.',true);}}
function current(){return incidents.find(x=>x.id===selected);}
function record(action,detail){const x=current();x.audit.push({seq:++seq,at:new Date().toISOString(),action,detail});persist();render();announce('Saved locally: '+action+'.');}
function filteredLogs(item,level,query){return item.logs.filter(x=>(level==='ALL'||x.level===level)&&`${x.at} ${x.level} ${x.message}`.toLowerCase().includes(query.toLowerCase()));}
function canTransition(item,target,note){if(NEXT[item.status]!==target)return 'Follow the investigation stages in order.';if(note.trim().length<10||note.trim().length>2000)return 'Write a transition note of 10–2,000 characters.';if(target==='resolved'&&!item.checks.every(Boolean))return 'Complete all runbook verification steps before resolving.';return '';}
function reportText(item){return `# ${item.id}: ${item.title}\n\nFictional training incident — no production systems connected.\nStatus: ${item.status}\nService: ${item.service}\nSeverity: ${item.severity}\nOwner: ${item.owner}\nImpact: ${item.impact}\nHypothesis: ${item.hypothesis||'Not recorded'}\n\n## Verification\n${item.steps.map((s,i)=>`- [${item.checks[i]?'x':' '}] ${s}`).join('\n')}\n\n## Audit trail\n${item.audit.map(a=>`${a.seq}. ${a.at} [${a.action}] ${a.detail}`).join('\n')}\n\nBrowser audit records can be edited or reset locally; this is not a tamper-proof or multi-user system.\n`;}
function download(){const x=current(),url=URL.createObjectURL(new Blob([reportText(x)],{type:'text/plain;charset=utf-8'}));const a=el('a');a.href=url;a.download=x.id+'-incident-report.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);announce('Report exported.');}
function renderLogs(){const x=current(),rows=filteredLogs(x,$('#level').value,$('#log-search').value);$('#logs').replaceChildren();rows.forEach(a=>{const row=el('li',undefined,'log-row');row.append(el('time',a.at.slice(11,19)+' UTC'),el('span',a.level,'level '+a.level.toLowerCase()),el('span',a.message));$('#logs').append(row);});$('#log-count').textContent=`${rows.length} of ${x.logs.length} fixture events`;if(!rows.length)$('#logs').append(el('li','No matching log events.','empty'));}
function render(){const x=current();$('#queue').replaceChildren();const query=$('#incident-search').value.toLowerCase(),status=$('#status-filter').value;const found=incidents.filter(i=>(status==='all'||i.status===status)&&`${i.id} ${i.title} ${i.service}`.toLowerCase().includes(query));found.forEach(i=>{const b=el('button',undefined,'queue-item'+(i.id===selected?' active':''));b.type='button';b.setAttribute('aria-pressed',String(i.id===selected));b.append(el('span',i.id+' / '+i.severity,'mono'),el('strong',i.title),el('small',i.service+' · '+i.status));b.onclick=()=>{selected=i.id;$('#level').value='ALL';$('#log-search').value='';render();};$('#queue').append(b);});if(!found.length)$('#queue').append(el('p','No incidents match these filters.','empty'));$('#active-count').textContent=incidents.filter(i=>i.status!=='resolved').length;$('#title').textContent=x.title;$('#incident-id').textContent=x.id+' / '+x.severity;$('#service').textContent=x.service;$('#status').textContent=x.status;$('#impact').textContent=x.impact;$('#owner').value=x.owner==='Unassigned'?'':x.owner;$('#hypothesis').value=x.hypothesis;$('#runbook').replaceChildren();x.steps.forEach((step,i)=>{const label=el('label',undefined,'check-row'),input=el('input');input.type='checkbox';input.checked=x.checks[i];input.disabled=x.status==='resolved';input.onchange=()=>{x.checks[i]=input.checked;record('verification',`Step ${i+1}: ${input.checked?'complete':'reopened'} — ${step}`);};label.append(input,el('span',step));$('#runbook').append(label);});const next=NEXT[x.status];$('#advance').textContent=next?'Move to '+next:'Resolved';$('#advance').disabled=!next;document.querySelectorAll('[data-mutable]').forEach(e=>e.disabled=x.status==='resolved');$('#audit').replaceChildren();x.audit.slice().reverse().forEach(a=>{const li=el('li');li.append(el('span',`#${a.seq} · ${a.at.slice(11,19)} UTC · ${a.action}`,'mono'),el('p',a.detail));$('#audit').append(li);});if(!x.audit.length)$('#audit').append(el('li','No actions yet. Begin investigating, then record your reasoning.','empty'));$('#audit-count').textContent=x.audit.length+' recorded actions';renderLogs();}
function restoreState(fresh,saved){
 const restored=structuredClone(fresh);
 if(saved===null)return {incidents:restored,seq:0};
 if(!saved||!Array.isArray(saved.incidents)||saved.incidents.length!==fresh.length)throw Error('Invalid saved incidents.');
 let lastSequence=0;const seen=new Set();
 restored.forEach((item,n)=>{
  const savedItem=saved.incidents[n];
  if(!savedItem||savedItem.id!==item.id||!Object.hasOwn({...NEXT,resolved:''},savedItem.status)||!Array.isArray(savedItem.checks)||savedItem.checks.length!==item.steps.length||!savedItem.checks.every(v=>typeof v==='boolean')||typeof savedItem.owner!=='string'||savedItem.owner.length>80||typeof savedItem.hypothesis!=='string'||savedItem.hypothesis.length>2000||!Array.isArray(savedItem.audit))throw Error('Invalid saved incident state.');
  if(savedItem.status==='resolved'&&!savedItem.checks.every(Boolean))throw Error('Invalid resolved verification state.');
  let previous=0;
  const audit=savedItem.audit.map(a=>{
   if(!a||!Number.isSafeInteger(a.seq)||a.seq<=previous||a.seq>=Number.MAX_SAFE_INTEGER||seen.has(a.seq)||typeof a.detail!=='string'||typeof a.at!=='string'||typeof a.action!=='string')throw Error('Invalid saved audit record.');
   previous=a.seq;seen.add(a.seq);lastSequence=Math.max(lastSequence,a.seq);
   return {seq:a.seq,at:a.at,action:a.action,detail:a.detail};
  });
  Object.assign(item,{status:savedItem.status,owner:savedItem.owner,hypothesis:savedItem.hypothesis,checks:[...savedItem.checks],audit});
 });
 return {incidents:restored,seq:lastSequence};
}
async function init(){try{const response=await fetch('fixtures.json');if(!response.ok)throw Error('Fixture request failed');const fresh=await response.json();incidents=structuredClone(fresh);try{const restored=restoreState(fresh,JSON.parse(localStorage.getItem(KEY)||'null'));incidents=restored.incidents;seq=restored.seq;}catch{storage=false;announce('Saved state could not be read. Fresh fictional scenarios loaded.',true);}render();$('#loading').hidden=true;$('#workspace').hidden=false;
$('#incident-search').oninput=render;$('#status-filter').onchange=render;$('#level').onchange=renderLogs;$('#log-search').oninput=renderLogs;
$('#owner-form').onsubmit=e=>{e.preventDefault();const text=$('#owner').value.trim();if(!text||text.length>80)return announce('Enter a display name of 1–80 characters.',true);current().owner=text;record('owner',text);};
$('#hypothesis-form').onsubmit=e=>{e.preventDefault();const text=$('#hypothesis').value.trim();if(text.length<10||text.length>2000)return announce('Write a hypothesis of 10–2,000 characters.',true);current().hypothesis=text;record('hypothesis',text);};
$('#note-form').onsubmit=e=>{e.preventDefault();const text=$('#note').value.trim();if(text.length<1||text.length>2000)return announce('Enter a note of 1–2,000 characters.',true);$('#note').value='';record('note',text);};
$('#advance').onclick=()=>{const x=current(),target=NEXT[x.status],note=$('#transition-note').value.trim(),error=canTransition(x,target,note);if(error)return announce(error,true);x.status=target;$('#transition-note').value='';record('transition',`${target}: ${note}`);};
$('#export').onclick=download;$('#reset').onclick=()=>{$('#reset-dialog').showModal();};$('#confirm-reset').onclick=()=>{incidents=structuredClone(fresh);seq=0;persist();$('#reset-dialog').close();render();announce('All fictional scenarios reset.');};
}catch{ $('#loading').textContent='Unable to load the fictional scenarios. Reload the page or serve this folder over HTTP.';}}
if(typeof document!=='undefined')init();
if(typeof module!=='undefined')module.exports={filteredLogs,canTransition,reportText,restoreState};
