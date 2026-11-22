#!/usr/bin/env bash
# Run from the project root after building titanic-api:test.
set -euo pipefail

docker run -d --name titanic-ci --health-interval=2s --health-timeout=3s \
  --health-start-period=5s --health-retries=2 titanic-api:test

wait_for_health() {
  local expected="$1"
  for attempt in $(seq 1 30); do
    actual=$(docker inspect --format '{{.State.Health.Status}}' titanic-ci)
    if [ "$actual" = "$expected" ]; then
      echo "Container health: $actual"
      return 0
    fi
    sleep 2
  done
  echo "Expected $expected; last health status: $actual" >&2
  return 1
}

wait_for_health healthy
test "$(docker exec titanic-ci id -u)" != "0"
docker exec titanic-ci python healthcheck.py
docker exec -i titanic-ci python - <<'PY'
import json
from urllib.request import Request, urlopen

with open('models/sample_input.json', encoding='utf-8') as source:
    passenger = json.load(source)
request = Request('http://127.0.0.1:8000/predict',
                  data=json.dumps(passenger).encode(),
                  headers={'Content-Type': 'application/json'})
with urlopen(request, timeout=10) as response:
    result = json.load(response)
    assert response.status == 200
    assert result['survived'] in [0, 1]
    assert 0 <= result['survival_probability'] <= 1
print('Container prediction contract passed.')
PY

# Suspend only this disposable test container's Uvicorn process. The probe
# keeps running, times out, and must mark the container unhealthy.
docker kill --signal=SIGSTOP titanic-ci
wait_for_health unhealthy
docker kill --signal=SIGCONT titanic-ci
wait_for_health healthy
