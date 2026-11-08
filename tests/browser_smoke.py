import hashlib
import json
import threading
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(ROOT)))
thread=threading.Thread(target=server.serve_forever,daemon=True)
thread.start()
base=f'http://127.0.0.1:{server.server_port}'
try:
 with sync_playwright() as p:
     browser=p.chromium.launch(headless=True)
     page=browser.new_page(viewport={'width':1440,'height':1000})
     errors=[]
     page.on('pageerror',lambda error: errors.append(str(error)))
     page.goto(base+'/projects/incidents/')
     expect(page.locator('#workspace')).to_be_visible()
     page.locator('#owner').fill('Demo Investigator')
     page.get_by_role('button',name='Assign',exact=True).click()
     page.locator('#hypothesis').fill('The fictional cached signing key is stale.')
     page.get_by_role('button',name='Save hypothesis',exact=True).click()
     for stage in ['investigating','mitigated']:
         page.locator('#transition-note').fill('Reviewed the fictional logs and recorded findings.')
         page.locator('#advance').click()
         expect(page.locator('#status')).to_have_text(stage)
     page.locator('#transition-note').fill('The fictional canary has recovered.')
     page.locator('#advance').click()
     expect(page.locator('#status')).to_have_text('mitigated')
     for checkbox in page.locator('#runbook input').all(): checkbox.check()
     page.locator('#advance').click()
     expect(page.locator('#status')).to_have_text('resolved')
     with page.expect_download() as download_info: page.locator('#export').click()
     report=Path(download_info.value.path()).read_text()
     assert 'Demo Investigator' in report and '[x]' in report
     page.reload()
     expect(page.locator('#status')).to_have_text('resolved')
     page.locator('#reset').click()
     page.locator('#confirm-reset').click()
     expect(page.locator('#status')).to_have_text('open')
     expect(page.locator('#owner')).to_have_value('')
     expect(page.locator('#audit-count')).to_have_text('0 recorded actions')
     assert not any(c.is_checked() for c in page.locator('#runbook input').all())
     page.reload()
     expect(page.locator('#owner')).to_have_value('')
     page.evaluate("localStorage.setItem('rithmsai-incident-workbench-v1', JSON.stringify({incidents:[null,null,null]}))")
     page.reload()
     expect(page.locator('#workspace')).to_be_visible()
     expect(page.locator('#notice')).to_contain_text('Fresh fictional scenarios loaded')
     print('PASS incident browser: workflow gates, report download, reload, pristine reset, malformed-state recovery')

     page.goto(base+'/projects/tracebench/')
     expect(page.get_by_role('heading',name='Hold release',exact=True)).to_be_visible()
     page.get_by_label('Block critical regressions').uncheck()
     expect(page.get_by_role('heading',name='Criteria met',exact=True)).to_be_visible()
     page.get_by_role('button',name='Reset thresholds').click()
     expect(page.get_by_role('heading',name='Hold release',exact=True)).to_be_visible()
     page.locator('#review').fill('Check the source support manually.')
     with page.expect_download() as download_info: page.get_by_role('button',name='Export report').click()
     exported=json.loads(Path(download_info.value.path()).read_text())
     assert exported['engineVersion']=='1.1.0'
     assert exported['reviews']['TB-003']=='Check the source support manually.'
     assert exported['decision']['passed'] is False
     fingerprint=page.evaluate('(dataset)=>JSON.stringify(dataset)',exported['dataset'])
     assert hashlib.sha256(fingerprint.encode()).hexdigest()==exported['datasetSha256']
     dataset=exported['dataset']
     dataset['name']='Imported prototype-like ID test'
     dataset['cases']=dataset['cases'][:1]
     dataset['cases'][0]['id']='constructor'
     page.locator('input[type=file]').set_input_files({'name':'valid.json','mimeType':'application/json','buffer':json.dumps(dataset).encode()})
     expect(page.get_by_role('heading',name=dataset['name'],exact=True)).to_be_visible()
     expect(page.locator('#review')).to_have_value('')
     page.locator('#review').fill('This is an ordinary case ID.')
     with page.expect_download() as download_info: page.get_by_role('button',name='Export report').click()
     assert json.loads(Path(download_info.value.path()).read_text())['reviews']['constructor']=='This is an ordinary case ID.'
     bad=json.loads(json.dumps(dataset))
     bad['cases']=[bad['cases'][0],json.loads(json.dumps(bad['cases'][0]))]
     bad['cases'][1]['id']='other'
     for item in bad['cases']: item['candidate']['costUsd']=1e308
     page.locator('input[type=file]').set_input_files({'name':'overflow.json','mimeType':'application/json','buffer':json.dumps(bad).encode()})
     expect(page.get_by_role('status')).to_contain_text('Import failed')
     expect(page.get_by_role('heading',name=dataset['name'],exact=True)).to_be_visible()
     expect(page.locator('#review')).to_have_value('This is an ordinary case ID.')
     page.set_viewport_size({'width':390,'height':844})
     assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
     assert not errors,errors
     print('PASS TraceBench browser: gate toggle/reset, downloaded report/hash, file import, prototype-like ID, failed import preserves state, mobile overflow check, no page errors')
     browser.close()
finally:
 server.shutdown()
 server.server_close()
 thread.join(timeout=5)
