"""Synthetic telemetry experiment. No real intrusion-detection claim."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random

import torch
from torch import nn

FEATURES = ['failed_logins', 'distinct_hosts', 'bytes_out_mb', 'off_hours_fraction']

def cohort(seed, n, shift=False):
    rng = random.Random(seed)
    xs, ys = [], []
    for _ in range(n):
        y = int(rng.random() < .18)
        # Overlapping distributions intentionally avoid a trivial perfect classifier.
        base = [2.0, 2.0, 8.0, .25]
        delta = [3.0, 2.0, 7.0, .30]
        noise = [2.5, 2.0, 7.0, .25]
        row = [max(0., rng.gauss(b + y*d, s)) for b,d,s in zip(base,delta,noise)]
        row[3] = min(1., row[3])
        if shift:
            row[2] *= 2.2  # Benign traffic-volume shift affects both classes.
            row[3] = min(1., row[3]+.15)
        xs.append(row); ys.append(y)
    return torch.tensor(xs, dtype=torch.float32), torch.tensor(ys, dtype=torch.float32)

def fit_scaler(x):
    return x.mean(0), x.std(0, unbiased=False).clamp_min(1e-6)

def metrics(y, scores, threshold):
    pred = scores >= threshold
    truth = y.bool()
    tp=int((pred & truth).sum()); fp=int((pred & ~truth).sum())
    tn=int((~pred & ~truth).sum()); fn=int((~pred & truth).sum())
    return dict(tp=tp, fp=fp, tn=tn, fn=fn, precision=tp/max(1,tp+fp),
                recall=tp/max(1,tp+fn), fpr=fp/max(1,fp+tn), f1=2*tp/max(1,2*tp+fp+fn))

def choose_threshold(y, scores, budget=.05):
    # Only validation labels enter this operation. A value above 1 can abstain entirely.
    candidates = [i/100 for i in range(101)] + [1.01]
    eligible = [(metrics(y,scores,t),t) for t in candidates if metrics(y,scores,t)['fpr']<=budget]
    return max(eligible,key=lambda p:(p[0]['recall'],p[0]['precision'],-p[1]))[1]

def model_for(kind):
    return nn.Sequential(nn.Linear(4,8),nn.ReLU(),nn.Linear(8,1)) if kind=='mlp' else nn.Sequential(nn.Linear(4,1))

def train(kind, seed, train_x, train_y):
    torch.manual_seed(seed)
    model=model_for(kind)
    optimizer=torch.optim.Adam(model.parameters(),lr=.03)
    loss_fn=nn.BCEWithLogitsLoss()
    for _ in range(180):
        optimizer.zero_grad()
        loss=loss_fn(model(train_x).squeeze(1),train_y)
        loss.backward(); optimizer.step()
    model.eval()
    return model

def export_model(model, mean, std, threshold):
    return dict(schema_version=1, features=FEATURES, kind='mlp', threshold=threshold,
                mean=mean.tolist(),std=std.tolist(),
                weights={name:t.detach().tolist() for name,t in model.state_dict().items()})

def predict(artifact, rows):
    if artifact.get('schema_version')!=1 or artifact.get('features')!=FEATURES or artifact.get('kind')!='mlp':
        raise ValueError('unsupported model schema')
    if not rows or len(rows)>10000 or any(len(r)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in r) or r[3]>1 for r in rows):
        raise ValueError('expected 1..10000 rows of four bounded finite telemetry features')
    model=model_for('mlp')
    model.load_state_dict({k:torch.tensor(v,dtype=torch.float32) for k,v in artifact['weights'].items()})
    mean=torch.tensor(artifact['mean']); std=torch.tensor(artifact['std'])
    if mean.shape!=(4,) or std.shape!=(4,) or not torch.isfinite(mean).all() or not torch.isfinite(std).all() or not (std>0).all():
        raise ValueError('invalid scaling')
    model.eval()
    with torch.inference_mode():
        scores=torch.sigmoid(model((torch.tensor(rows,dtype=torch.float32)-mean)/std).squeeze(1))
    if not torch.isfinite(scores).all(): raise ValueError('nonfinite inference')
    return scores.tolist()

def experiment(seeds=(17,29,43)):
    torch.set_num_threads(1); torch.use_deterministic_algorithms(True)
    report=dict(data='synthetic independent cohorts; no real logs',features=FEATURES,
                sizes=dict(train=1200,validation=400,test=600,shifted_test=600),
                validation_fpr_budget=.05,torch_version=torch.__version__,runs=[])
    exported=None
    for seed in seeds:
        x,y=cohort(seed,1200); vx,vy=cohort(seed+1000,400)
        tx,ty=cohort(seed+2000,600); sx,sy=cohort(seed+3000,600,True)
        mean,std=fit_scaler(x)
        for kind in ('linear','mlp'):
            model=train(kind,seed,(x-mean)/std,y)
            with torch.inference_mode():
                score=lambda z:torch.sigmoid(model((z-mean)/std).squeeze(1))
                threshold=choose_threshold(vy,score(vx))
                report['runs'].append(dict(seed=seed,model=kind,threshold=threshold,
                    validation=metrics(vy,score(vx),threshold),test=metrics(ty,score(tx),threshold),
                    shifted_test=metrics(sy,score(sx),threshold)))
            if seed==seeds[0] and kind=='mlp': exported=export_model(model,mean,std,threshold)
    canonical=json.dumps(exported,sort_keys=True).encode()
    report['exported_model_sha256']=hashlib.sha256(canonical).hexdigest()
    report['selection']='No model selected using test performance; both fixed architectures reported.'
    return report,exported

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='results')
    args=parser.parse_args()
    report,model=experiment()
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'model.json').write_text(json.dumps(model,indent=2)+'\n')
    print(json.dumps(report,indent=2))
