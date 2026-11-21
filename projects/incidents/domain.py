"""Deterministic workflow shared by the local service. Fictional training data only."""
from datetime import datetime, timezone

TRANSITIONS = {'open': {'investigating'}, 'investigating': {'mitigated'}, 'mitigated': {'resolved'}, 'resolved': set()}

def now():
    return datetime.now(timezone.utc).isoformat()

def transition(incident, target, note):
    if target not in TRANSITIONS.get(incident['status'], set()):
        raise ValueError('Follow the workflow: open → investigating → mitigated → resolved.')
    if not isinstance(note, str) or not 10 <= len(note.strip()) <= 2000:
        raise ValueError('Provide an investigation note of 10–2,000 characters.')
    if target == 'resolved' and not all(incident['checks']):
        raise ValueError('Complete every verification step before resolving.')
    return target

def fixtures():
    return [
        {'id':'INC-1042','title':'Sign-in failures after key rotation','service':'Identity gateway','severity':'SEV2','status':'open','owner':'Unassigned','impact':'Simulated sign-in error rate: 18% of 1,000 fixture requests.','hypothesis':'','checks':[False]*3,'steps':['Compare errors before and after the deployment.','Confirm signing-key mismatch in the sample logs.','Verify recovery with the synthetic canary.'],'logs':[
            {'at':'2026-10-28T14:02:00Z','level':'INFO','message':'Deployment identity-gateway v2.4.1 completed; keyset version k18.'},
            {'at':'2026-10-28T14:03:00Z','level':'ERROR','message':'Token signature verification failed; cached keyset k17; expected k18.'},
            {'at':'2026-10-28T14:04:00Z','level':'WARN','message':'Synthetic sign-in probe: 180 / 1,000 requests rejected.'},
            {'at':'2026-10-28T14:07:00Z','level':'INFO','message':'Fixture recovery: refresh cached keys; synthetic canary 1,000 / 1,000 passed.'}],
         'audit':[]},
        {'id':'INC-1043','title':'Order queue latency exceeds threshold','service':'Order processor','severity':'SEV3','status':'open','owner':'Unassigned','impact':'Simulated processing delay: p95 rises from 0.4s to 4.8s.','hypothesis':'','checks':[False]*3,'steps':['Inspect queue depth and worker concurrency.','Compare database pool limits with active workers.','Confirm the fixture queue drains after mitigation.'],'logs':[
            {'at':'2026-10-28T15:10:00Z','level':'WARN','message':'Queue depth 840; oldest message 42s; worker concurrency 64.'},
            {'at':'2026-10-28T15:11:00Z','level':'ERROR','message':'Database pool exhausted: 16 connections; acquisition timeout 2s.'},
            {'at':'2026-10-28T15:13:00Z','level':'INFO','message':'Fixture mitigation: bound workers to 12; queue depth fell to 0 in 90s.'}], 'audit':[]},
        {'id':'INC-1044','title':'Release health check regression','service':'Reporting API','severity':'SEV2','status':'open','owner':'Unassigned','impact':'Simulated new release fails 3 of 5 readiness probes.','hypothesis':'','checks':[False]*3,'steps':['Compare readiness responses across release versions.','Identify missing configuration in the fixture.','Confirm rollback passes all readiness probes.'],'logs':[
            {'at':'2026-10-28T16:20:00Z','level':'INFO','message':'Reporting API release v1.8 started.'},
            {'at':'2026-10-28T16:21:00Z','level':'ERROR','message':'Readiness probe failed: REPORT_CACHE_TTL missing; fixture configuration only.'},
            {'at':'2026-10-28T16:24:00Z','level':'INFO','message':'Fixture rollback v1.7: 5 / 5 readiness probes passed.'}], 'audit':[]}
    ]
