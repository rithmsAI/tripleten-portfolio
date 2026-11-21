

const $=id=>document.getElementById(id); const fmt=n=>Number(n).toLocaleString('en-US',{maximumFractionDigits:2});

const metricLabels={electricity_mwh:'MWh',water_withdrawal_ml:'ML',water_consumption_ml:'ML',intensity:'L/kWh'};

function bars(rows,unit){const max=Math.max(...rows.map(r=>r.value),1);return rows.map(r=>`<div class="bar-row"><span>${r.label}</span><div class="bar-track" aria-hidden="true"><div class="bar-fill" style="width:${r.value/max*100}%"></div></div><span class="bar-value">${fmt(r.value)} ${unit}</span></div>`).join('');}

function annual(){const metric=$('annualMetric').value,rows=sustainabilityData.annual.map(r=>({label:'FY'+r.fiscal_year.slice(2),value:+r[metric]}));$('annualBars').innerHTML=bars(rows,metricLabels[metric]);$('growthValue').textContent='+'+((rows.at(-1).value/rows[0].value-1)*100).toFixed(1)+'%';$('growthLabel').textContent='FY20 to FY25 · corporate '+$('annualMetric').selectedOptions[0].textContent.toLowerCase();}

function locations(){const scope=$('locationScope').value,metric=$('locationMetric').value;let rows=sustainabilityData.locations.filter(r=>scope==='all'||r.country==='United States');$('locationsTable').innerHTML=rows.map(r=>`<tr><td>${r.location}</td><td>${r.country}</td><td>${fmt(r.electricity_mwh)}</td><td>${r.water_withdrawal_ml?fmt(r.water_withdrawal_ml):'<1 (censored)'}</td></tr>`).join('');let points=rows.filter(r=>metric==='electricity_mwh'||r.water_withdrawal_ml!=='').map(r=>({label:r.location,value:metric==='intensity'?+r.water_withdrawal_ml*1000/+r.electricity_mwh:+r[metric]})).sort((a,b)=>b.value-a.value).slice(0,10);$('locationBars').innerHTML=bars(points,metricLabels[metric]);$('locationTitle').textContent=$('locationMetric').selectedOptions[0].textContent+' / FY25 / '+(scope==='us'?'United States':'global disclosure');}

function scenario(){const pue=+$('pue').value,it=+$('itLoad').value;$('pueValue').textContent=pue.toFixed(2);$('itValue').textContent=fmt(it)+' MWh';$('facilityValue').textContent=fmt(pue*it)+' MWh';$('overheadValue').textContent=fmt((pue-1)*it)+' MWh of non-IT overhead · '+(((pue-1)/pue)*100).toFixed(1)+'% of facility energy.';}

$('annualMetric').addEventListener('change',annual);['locationScope','locationMetric'].forEach(id=>$(id).addEventListener('change',locations));['pue','itLoad'].forEach(id=>$(id).addEventListener('input',scenario));annual();locations();scenario();

