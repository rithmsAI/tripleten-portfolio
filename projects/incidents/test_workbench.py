import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from app import create_app

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.path=Path(self.temp.name)/'test.sqlite3'
        self.client=TestClient(create_app(self.path))
        self.key='INC-1042'
    def tearDown(self):
        self.client.close(); self.temp.cleanup()
    def item(self): return self.client.get('/incidents/'+self.key).json()
    def cmd(self,kind,text='',**extra):
        return self.client.post('/incidents/'+self.key+'/commands',json={'kind':kind,'text':text,'version':self.item()['version'],**extra})
    def test_seed_is_idempotent_and_persistent(self):
        self.cmd('owner','Demo investigator')
        with TestClient(create_app(self.path)) as other:
            self.assertEqual(len(other.get('/incidents').json()),3)
            self.assertEqual(other.get('/incidents/'+self.key).json()['owner'],'Demo investigator')
    def test_workflow_cannot_skip_stages(self):
        self.assertEqual(self.cmd('transition','resolved\nCanary is green now.').status_code,422)
        self.assertEqual(self.item()['version'],0)
        self.assertEqual(self.item()['audit'],[])
    def test_resolution_requires_all_verification(self):
        self.assertEqual(self.cmd('transition','investigating\nInspecting key mismatch.').status_code,200)
        self.cmd('transition','mitigated\nRefreshed fixture cache.')
        self.assertEqual(self.cmd('transition','resolved\nAll fixture probes recovered.').status_code,422)
        for i in range(3):self.cmd('check',index=i,checked=True)
        self.assertEqual(self.cmd('transition','resolved\nAll fixture probes recovered.').status_code,200)
        self.assertEqual(self.cmd('note','Late note').status_code,422)
    def test_stale_write_is_rejected_without_partial_audit(self):
        self.cmd('note','First observation')
        r=self.client.post('/incidents/'+self.key+'/commands',json={'version':0,'kind':'owner','text':'Stale owner'})
        self.assertEqual(r.status_code,409)
        self.assertEqual(self.item()['owner'],'Unassigned')
        self.assertEqual(len(self.item()['audit']),1)
    def test_sql_and_html_are_data(self):
        text="<script>alert(1)</script>'; DROP TABLE incidents; --"
        self.assertEqual(self.cmd('note',text).status_code,200)
        self.assertEqual(len(self.client.get('/incidents').json()),3)
        self.assertEqual(self.item()['audit'][0]['detail'],text)
    def test_invalid_payloads_do_not_mutate(self):
        for payload in ({'version':0,'kind':'check','index':9,'checked':True},{'version':0,'kind':'owner','text':' '},{'version':0,'kind':'note','text':'x'*2001},{'version':0,'kind':'note','text':'ok','admin':True}):
            self.assertEqual(self.client.post('/incidents/'+self.key+'/commands',json=payload).status_code,422)
        self.assertEqual(self.item()['version'],0)
    def test_audit_order_and_incident_isolation(self):
        self.cmd('note','One');self.cmd('note','Two')
        audit=self.item()['audit']
        self.assertEqual([a['detail'] for a in audit],['One','Two'])
        self.assertLess(audit[0]['seq'],audit[1]['seq'])
        self.assertEqual(self.client.get('/incidents/INC-1043').json()['audit'],[])
    def test_export_has_reasoning_and_safe_headers(self):
        self.cmd('hypothesis','The cached signing key is stale.')
        r=self.client.get('/incidents/'+self.key+'/report')
        self.assertEqual(r.status_code,200)
        self.assertIn('The cached signing key is stale.',r.text)
        self.assertIn('Fictional training incident',r.text)
        self.assertTrue(r.headers['content-type'].startswith('text/plain'))
        self.assertEqual(r.headers['x-content-type-options'],'nosniff')
    def test_unknown_incident(self):
        self.assertEqual(self.client.get('/incidents/unknown').status_code,404)
        self.assertEqual(self.client.post('/incidents/unknown/commands',json={'version':0,'kind':'note','text':'test'}).status_code,404)
    def test_transition_note_required(self):
        self.assertEqual(self.cmd('transition','investigating').status_code,422)
        self.assertEqual(self.item()['version'],0)

if __name__=='__main__':unittest.main(verbosity=2)
