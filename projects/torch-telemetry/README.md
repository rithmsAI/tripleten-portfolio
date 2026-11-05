# Telemetry Shift Lab | PyTorch CPU experiment

Independent, AI-assisted ML engineering project by Kaya Robinson. Compare a linear classifier and a small neural network on **synthetic** authentication/traffic telemetry, then inspect performance under a distribution shift. This is model-evaluation practice, not evidence of real intrusion detection.

```sh
python -m venv .venv
# Activate the environment, then:
python -m pip install -r requirements.txt
python -m unittest -v
python experiment.py
```

Python 3.12 and pinned CPU PyTorch. Results include a JSON report and a plain JSON model (weights, feature order, train-only mean/std and threshold), without pickle deserialization. To score trusted local rows:

```python
import json
from experiment import predict
artifact = json.load(open('results/model.json'))
print(predict(artifact, [[2, 3, 12, 0.2]]))
```

## Experimental design

Each of three seeds produces independent generated cohorts: 1,200 training, 400 validation, 600 ordinary test and 600 shifted test observations. Four continuous features have overlapping class distributions and an 18% expected positive prevalence. No external or private datasets are used. Cohorts have separate RNG streams; these are independent observations, not overlapping time windows or user sessions.

Fit scaling only on training data. Train fixed linear and 4→8→1 ReLU architectures for 180 full-batch Adam steps using BCEWithLogitsLoss. Pick each decision threshold from validation labels to maximize recall subject to a 5% empirical validation false-positive-rate budget; tie-break on precision, then smaller threshold. Test labels never choose architectures, epochs, scaling or thresholds. All fixed seeds and both architectures are reported, including unfavorable results.

The shifted cohort increases traffic volume and off-hours activity for both classes. Report confusion counts, precision, recall, F1 and false-positive rate rather than only accuracy. The validation budget is **not** a guarantee on test or shifted data. Model outputs are scores, not calibrated risk probabilities.

Twelve tests cover metric arithmetic, degenerate inputs, validation-budget selection, independent RNG cohorts, train-only scaling, deterministic training and exported JSON inference parity. Determinism is scoped to this CPU software environment; no promise across PyTorch/platform versions.

## Limitations and next experiments

The generator defines both patterns and labels, so results measure recovery of invented structure. There are no human adjudications, real users, fairness claims, latency benchmarks, production monitoring or security efficacy claims. The JSON model is a trusted local artifact, not an untrusted upload format. A real study needs licensed real telemetry, group/time separation, confidence intervals, calibration, drift monitoring and a deployment review. See results/report.json for all measured outcomes.

References: [PyTorch reproducibility](https://docs.pytorch.org/docs/stable/notes/randomness.html), [model persistence](https://docs.pytorch.org/tutorials/beginner/basics/saveloadrun_tutorial.html).
