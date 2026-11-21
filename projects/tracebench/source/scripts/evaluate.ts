import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {parseDataset,report} from '../src/engine.js';
const raw=readFileSync(process.argv[2]||'public/example-dataset.json','utf8');
const dataset=parseDataset(raw);
const result={...report(dataset,{minimumPassRate:.8,maximumP95:1500,maximumCost:.05,blockCriticalRegressions:true}),datasetSha256:createHash('sha256').update(JSON.stringify(dataset)).digest('hex')};
const text=JSON.stringify(result,null,2)+'\n';
if(process.argv[3])writeFileSync(process.argv[3],text);else process.stdout.write(text);
