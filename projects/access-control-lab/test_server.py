import hashlib
import http.client
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from server import initialize,handler_for,load_tokens

class AccessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'state.db'
        self.raw={'analyst':'a'*40,'admin':'b'*40}
        self.tokens={r:hashlib.sha256(t.encode()).digest() for r,t in self.raw.items()}
        initialize(self.db)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(self.db,self.tokens))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
    def request(self,method='GET',path='/events',role=None,body=None,headers=None):
        h={'Authorization':'Bearer '+self.raw[role]} if role else {}
        if body is not None:h['Content-Type']='application/json'
        h.update(headers or {})
        con=http.client.HTTPConnection(*self.server.server_address,timeout=5)
        try:
            con.request(method,path,body=body,headers=h);r=con.getresponse()
            return r.status,json.loads(r.read()),dict(r.getheaders())
        finally:con.close()
    def test_health(self):self.assertEqual(self.request(path='/health')[0],200)
    def test_missing_auth(self):self.assertEqual(self.request()[0],401)
    def test_invalid_token(self):self.assertEqual(self.request(headers={'Authorization':'Bearer invalid'})[0],401)
    def test_analyst_read(self):self.assertEqual(self.request(role='analyst')[0],200)
    def test_analyst_cannot_write(self):self.assertEqual(self.request('POST',role='analyst',body='{}')[0],403)
    def test_admin_create_and_read(self):
        self.assertEqual(self.request('POST',role='admin',body='{"category":"auth","severity":4}')[0],201)
        self.assertEqual(self.request(role='analyst')[1]['events'][0]['severity'],4)
    def test_schema_rejections(self):
        for body in ['[]','null','{bad','{"category":"auth","severity":true}',
                     '{"category":"auth","severity":6}','{"category":"auth","severity":1,"role":"admin"}',
                     '{"category":"x\u0027); DROP TABLE events;--","severity":1}']:
            with self.subTest(body=body):self.assertEqual(self.request('POST',role='admin',body=body)[0],400)
    def test_body_limit(self):self.assertEqual(self.request('POST',role='admin',body='x'*1025)[0],413)
    def test_content_type(self):self.assertEqual(self.request('POST',role='admin',body='{}',headers={'Content-Type':'text/plain'})[0],415)
    def test_unknown_route(self):self.assertEqual(self.request(path='/events?role=admin')[0],404)
    def test_safe_headers(self):
        h=self.request(role='admin')[2]
        self.assertEqual(h['Cache-Control'],'no-store');self.assertEqual(h['X-Content-Type-Options'],'nosniff')
    def test_audit_no_secrets(self):
        self.request();self.request('POST',role='analyst',body='{}')
        with sqlite3.connect(self.db) as con:rows=con.execute('SELECT role,status FROM audit').fetchall()
        self.assertEqual(rows,[('anonymous',401),('analyst',403)])
        self.assertNotIn(self.raw['admin'],str(rows))
    def test_atomic_rollback(self):
        with sqlite3.connect(self.db) as con:
            con.execute("CREATE TRIGGER fail_audit BEFORE INSERT ON audit BEGIN SELECT RAISE(ABORT,'audit unavailable'); END")
        self.assertEqual(self.request('POST',role='admin',body='{"category":"auth","severity":1}')[0],503)
        with sqlite3.connect(self.db) as con:self.assertEqual(con.execute('SELECT COUNT(*) FROM events').fetchone()[0],0)
    def test_state_survives_reinitialize(self):
        self.request('POST',role='admin',body='{"category":"auth","severity":2}');initialize(self.db)
        self.assertEqual(len(self.request(role='analyst')[1]['events']),1)
    def test_bad_token_config(self):
        p=Path(self.tmp.name)/'tokens.json';p.write_text('{"admin":"short"}')
        with self.assertRaises(ValueError):load_tokens(p)
    def test_valid_token_config(self):
        p=Path(self.tmp.name)/'tokens.json';p.write_text(json.dumps(self.raw))
        self.assertEqual(load_tokens(p),self.tokens)

if __name__=='__main__':unittest.main()
