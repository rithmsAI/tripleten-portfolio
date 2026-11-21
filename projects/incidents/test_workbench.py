import tempfile
import unittest
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from unittest.mock import patch
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

    def test_command_types_are_not_coerced(self):
        payloads = [
            {'kind': 'note', 'text': 'Observation', 'version': version}
            for version in (False, '0', 0.0)
        ] + [
            {'kind': 'check', 'version': 0, 'index': index, 'checked': checked}
            for index, checked in ((False, True), ('0', True), (0, 'false'), (0, 1))
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                response = self.client.post('/incidents/'+self.key+'/commands', json=payload)
                self.assertEqual(response.status_code, 422)
        self.assertEqual(self.item()['version'], 0)
        self.assertEqual(self.item()['audit'], [])

    def test_command_specific_fields_are_enforced(self):
        payloads = [
            {'kind': 'check', 'index': 0},
            {'kind': 'check', 'index': 0, 'checked': True, 'text': 'Ignored text'},
            {'kind': 'owner', 'text': 'Investigator', 'checked': True},
            {'kind': 'note', 'text': 'Observation', 'index': 0},
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post('/incidents/'+self.key+'/commands',
                    json={'version': 0, **payload}).status_code, 422)
        self.assertEqual(self.item()['version'], 0)

    def test_hypothesis_matches_browser_minimum_length(self):
        self.assertEqual(self.cmd('hypothesis', 'Too short').status_code, 422)
        self.assertEqual(self.cmd('hypothesis', 'A supported working hypothesis.').status_code, 200)

    def test_failed_audit_insert_rolls_back_incident_and_version(self):
        before = self.item()
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TRIGGER reject_audit BEFORE INSERT ON audit BEGIN SELECT RAISE(ABORT, 'forced failure'); END")
        response = self.cmd('owner', 'Must not persist')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {'detail': 'Incident storage unavailable'})
        self.assertEqual(self.item(), before)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('DROP TRIGGER reject_audit')
        self.assertEqual(self.cmd('owner', 'Recovery works').status_code, 200)

    def test_storage_failures_have_safe_responses(self):
        with patch('app.sqlite3.connect', side_effect=sqlite3.OperationalError('private database path')):
            for path in ('/incidents', '/incidents/'+self.key, '/incidents/'+self.key+'/report'):
                with self.subTest(path=path):
                    response = self.client.get(path)
                    self.assertEqual(response.status_code, 503)
                    self.assertNotIn('private database path', response.text)

    def test_two_service_instances_cannot_accept_the_same_version(self):
        barrier = threading.Barrier(2)
        with TestClient(create_app(self.path)) as other:
            def write(args):
                client, owner = args
                barrier.wait(timeout=5)
                return client.post('/incidents/'+self.key+'/commands',
                    json={'kind': 'owner', 'text': owner, 'version': 0})
            with ThreadPoolExecutor(max_workers=2) as pool:
                responses = list(pool.map(write, [(self.client, 'First'), (other, 'Second')]))
        self.assertEqual(sorted(r.status_code for r in responses), [200, 409])
        winner = next(r.json() for r in responses if r.status_code == 200)
        self.assertEqual(self.item()['owner'], winner['owner'])
        self.assertEqual(self.item()['version'], 1)
        self.assertEqual(len(self.item()['audit']), 1)

    def test_report_includes_verification_state_and_version(self):
        self.cmd('check', index=1, checked=True)
        report = self.client.get('/incidents/'+self.key+'/report').text
        self.assertIn('Version: 1', report)
        self.assertIn('[ ] Compare errors', report)
        self.assertIn('[x] Confirm signing-key mismatch', report)
        self.assertIn('self-attested', report)

if __name__=='__main__':unittest.main(verbosity=2)
