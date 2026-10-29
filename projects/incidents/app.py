"""Local FastAPI/SQLite reference service; not a public production API."""
import json
import os
import sqlite3
import threading
from contextlib import closing
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field, ConfigDict
from domain import fixtures, transition, now

class Command(BaseModel):
    model_config = ConfigDict(extra='forbid')
    version: int = Field(ge=0)
    kind: str = Field(pattern='^(note|owner|hypothesis|check|transition)$')
    text: str = Field(default='', max_length=2000)
    index: int | None = Field(default=None, ge=0, le=2)
    checked: bool | None = None

def create_app(db_path=None):
    path = Path(db_path or os.environ.get('WORKBENCH_DB','workbench.sqlite3'))
    app = FastAPI(title='Incident Response Workbench', description='Local fictional incident training service. No authentication; bind to 127.0.0.1 only.')
    lock = threading.Lock()
    with closing(sqlite3.connect(path)) as db:
        db.executescript('CREATE TABLE IF NOT EXISTS incidents(id TEXT PRIMARY KEY, version INTEGER NOT NULL, payload TEXT NOT NULL); CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY AUTOINCREMENT, incident_id TEXT NOT NULL, at TEXT NOT NULL, action TEXT NOT NULL, detail TEXT NOT NULL);')
        for item in fixtures():
            db.execute('INSERT OR IGNORE INTO incidents VALUES(?,0,?)',(item['id'],json.dumps(item)))
        db.commit()

    def read(db, key):
        row = db.execute('SELECT version,payload FROM incidents WHERE id=?',(key,)).fetchone()
        if row is None: raise HTTPException(404,'Incident not found')
        item=json.loads(row[1]); item['version']=row[0]
        item['audit']=[dict(zip(('seq','at','action','detail'),r)) for r in db.execute('SELECT seq,at,action,detail FROM audit WHERE incident_id=? ORDER BY seq',(key,))]
        return item

    @app.get('/health')
    def health(): return {'status':'ok','mode':'fictional-local-demo'}

    @app.get('/incidents')
    def list_incidents():
        with closing(sqlite3.connect(path)) as db:
            return [read(db,r[0]) for r in db.execute('SELECT id FROM incidents ORDER BY id').fetchall()]

    @app.get('/incidents/{key}')
    def get_incident(key:str):
        with closing(sqlite3.connect(path)) as db: return read(db,key)

    @app.post('/incidents/{key}/commands')
    def command(key:str, cmd:Command):
        with lock, closing(sqlite3.connect(path)) as db:
            db.execute('BEGIN IMMEDIATE')
            item=read(db,key)
            if item['version']!=cmd.version: raise HTTPException(409,'Version conflict. Reload before retrying.')
            text=cmd.text.strip()
            try:
                if cmd.kind=='transition': item['status']=transition(item,text.split('\n',1)[0],text.split('\n',1)[1] if '\n' in text else '')
                elif cmd.kind=='check':
                    if cmd.index is None or cmd.checked is None: raise ValueError('Check index and checked value are required.')
                    if item['status']=='resolved': raise ValueError('Resolved incidents are read-only.')
                    item['checks'][cmd.index]=cmd.checked
                    text=f'Step {cmd.index+1}: {cmd.checked}'
                else:
                    if item['status']=='resolved': raise ValueError('Resolved incidents are read-only.')
                    if not text: raise ValueError('Text must not be blank.')
                    if cmd.kind=='owner' and len(text)>80: raise ValueError('Owner must be 80 characters or fewer.')
                    if cmd.kind in ('owner','hypothesis'): item[cmd.kind]=text
            except ValueError as exc: raise HTTPException(422,str(exc)) from exc
            db.execute('UPDATE incidents SET version=version+1,payload=? WHERE id=?',(json.dumps({k:v for k,v in item.items() if k not in ('version','audit')}),key))
            db.execute('INSERT INTO audit(incident_id,at,action,detail) VALUES(?,?,?,?)',(key,now(),cmd.kind,text))
            db.commit()
            return read(db,key)

    @app.get('/incidents/{key}/report')
    def report(key:str):
        with closing(sqlite3.connect(path)) as db: item=read(db,key)
        text=f"# {key}: {item['title']}\n\nFictional training incident.\nStatus: {item['status']}\nOwner: {item['owner']}\nImpact: {item['impact']}\nHypothesis: {item['hypothesis']}\n\n## Audit\n"+'\n'.join(f"- {a['at']} [{a['action']}] {a['detail']}" for a in item['audit'])
        return Response(text,media_type='text/plain',headers={'Content-Disposition':f'attachment; filename="{key}-report.txt"','X-Content-Type-Options':'nosniff'})
    return app

# Factory avoids creating a database on import. Run uvicorn app:create_app --factory.
