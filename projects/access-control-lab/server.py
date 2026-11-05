"""Local defensive access-control exercise; not an internet-facing production server."""
import argparse
from contextlib import contextmanager
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
import sqlite3
import time

def load_tokens(path):
    config=json.loads(Path(path).read_text())
    if set(config)!={'analyst','admin'} or any(not isinstance(v,str) or len(v)<32 or len(v)>256 for v in config.values()) or len(set(config.values()))!=2:
        raise ValueError('two distinct tokens of 32..256 characters required')
    return {role:hashlib.sha256(token.encode()).digest() for role,token in config.items()}

@contextmanager
def connect(db):
    con=sqlite3.connect(db,timeout=3)
    try:
        con.execute('PRAGMA foreign_keys=ON')
        with con:
            yield con
    finally:
        con.close()

def initialize(db):
    with connect(db) as con:
        con.execute('CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, category TEXT NOT NULL, severity INTEGER NOT NULL)')
        con.execute('CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, ts INTEGER NOT NULL, role TEXT NOT NULL, action TEXT NOT NULL, status INTEGER NOT NULL)')

def handler_for(db,tokens):
    class Handler(BaseHTTPRequestHandler):
        server_version='AccessLab'
        sys_version=''
        def setup(self):
            super().setup(); self.connection.settimeout(3)
        def log_message(self,*args):
            pass  # Do not log headers, tokens, request bodies, or raw paths.
        def reply(self,status,data):
            raw=json.dumps(data,separators=(',',':')).encode()
            self.send_response(status)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Connection','close')
            self.end_headers();self.wfile.write(raw)
        def audit(self,role,action,status):
            with connect(db) as con:
                con.execute('INSERT INTO audit(ts,role,action,status) VALUES(?,?,?,?)',(int(time.time()),role,action,status))
        def role(self):
            auths=self.headers.get_all('Authorization',[])
            if len(auths)!=1 or not auths[0].startswith('Bearer ') or len(auths[0])>263: return None
            digest=hashlib.sha256(auths[0][7:].encode()).digest()
            found=None
            for role,expected in tokens.items():
                if hmac.compare_digest(digest,expected):found=role
            return found
        def handle_request(self,write=False):
            if not write and self.path=='/health':
                self.reply(200,{'status':'ok'});return
            if self.path!='/events':self.reply(404,{'error':'not found'});return
            role=self.role()
            action='create_event' if write else 'read_events'
            if not role:
                self.audit('anonymous',action,401);self.reply(401,{'error':'unauthorized'});return
            if write and role!='admin':
                self.audit(role,action,403);self.reply(403,{'error':'forbidden'});return
            if write:
                sizes=self.headers.get_all('Content-Length',[])
                if self.headers.get('Transfer-Encoding') is not None or len(sizes)!=1 or len(sizes[0])>8 or not sizes[0].isascii() or not sizes[0].isdigit():
                    self.audit(role,action,400);self.reply(400,{'error':'one Content-Length required'});return
                size=int(sizes[0])
                if size>1024:
                    self.audit(role,action,413);self.reply(413,{'error':'body too large'});return
                if self.headers.get('Content-Type')!='application/json':
                    self.audit(role,action,415);self.reply(415,{'error':'application/json required'});return
                raw=self.rfile.read(size)
                try:
                    if len(raw)!=size: raise ValueError('truncated body')
                    event=json.loads(raw)
                    if not isinstance(event,dict) or set(event)!={'category','severity'} or not isinstance(event['category'],str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,31}',event['category']) or type(event['severity']) is not int or not 1<=event['severity']<=5:
                        raise ValueError('invalid event')
                except (ValueError,UnicodeError):
                    self.audit(role,action,400);self.reply(400,{'error':'invalid event'});return
                # Event and successful audit are committed together or rolled back together.
                with connect(db) as con:
                    cursor=con.execute('INSERT INTO events(category,severity) VALUES(?,?)',(event['category'],event['severity']))
                    ident=cursor.lastrowid
                    con.execute('INSERT INTO audit(ts,role,action,status) VALUES(?,?,?,201)',(int(time.time()),role,action))
                self.reply(201,{'id':ident});return
            with connect(db) as con:
                rows=con.execute('SELECT id,category,severity FROM events ORDER BY id DESC LIMIT 100').fetchall()
                con.execute('INSERT INTO audit(ts,role,action,status) VALUES(?,?,?,200)',(int(time.time()),role,action))
            self.reply(200,{'events':[dict(zip(('id','category','severity'),row)) for row in rows]})
        def dispatch(self,write):
            try:self.handle_request(write)
            except (sqlite3.Error,OSError):
                self.reply(503,{'error':'service unavailable'})
        def do_GET(self):self.dispatch(False)
        def do_POST(self):self.dispatch(True)
    return Handler

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--generate-tokens',action='store_true')
    parser.add_argument('--tokens',default='tokens.local.json')
    parser.add_argument('--db',default='state.local.db')
    parser.add_argument('--host',default='127.0.0.1')
    parser.add_argument('--port',type=int,default=8080)
    args=parser.parse_args()
    if args.generate_tokens:
        with open(args.tokens,'x') as out:json.dump({role:secrets.token_urlsafe(32) for role in ('analyst','admin')},out)
        Path(args.tokens).chmod(0o600)
        print('Created local credentials. Keep them private.');raise SystemExit
    tokens=load_tokens(args.tokens);initialize(args.db)
    ThreadingHTTPServer((args.host,args.port),handler_for(args.db,tokens)).serve_forever()
