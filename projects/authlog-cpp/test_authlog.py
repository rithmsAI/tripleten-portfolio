import json
import os
import subprocess
import unittest

BINARY = os.environ.get('AUTHLOG_BINARY', './authlog')
HEADER = 'timestamp,principal,outcome\n'

def run(rows):
    return subprocess.run([BINARY], input=HEADER+rows, text=True, capture_output=True, timeout=10)

class AuthlogTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(json.loads(run('').stdout)['rows'], 0)

    def test_threshold_and_suppression(self):
        r = run(''.join(f'{i},alice,failure\n' for i in range(8)))
        self.assertEqual(json.loads(r.stdout)['alerts'], [{'timestamp':4,'principal':'alice'}])

    def test_window_boundary(self):
        r = run('0,a,failure\n1,a,failure\n2,a,failure\n3,a,failure\n60,a,failure\n')
        self.assertEqual(json.loads(r.stdout)['alerts'], [])

    def test_rearms(self):
        r=run(''.join(f'{i},a,failure\n' for i in [0,1,2,3,4,100,101,102,103,104]))
        self.assertEqual(len(json.loads(r.stdout)['alerts']), 2)

    def test_principals_isolated(self):
        self.assertEqual(json.loads(run('1,a,failure\n1,b,failure\n').stdout)['accounts'], 2)

    def test_success_not_failure(self):
        self.assertEqual(json.loads(run('1,a,success\n').stdout)['failures'], 0)

    def test_bad_inputs_fail_without_partial_json(self):
        for value in ['1,a,bogus\n', '-1,a,success\n', '1x,a,success\n', '1,a,success,extra\n',
                      '1,a"x,success\n', '2,a,success\n1,a,success\n', '\n',
                      '18446744073709551616,a,success\n', '1,'+'a'*65+',success\n', 'x'*257]:
            with self.subTest(value=value[:40]):
                r=run(value); self.assertEqual(r.returncode,2); self.assertEqual(r.stdout,'')

    def test_account_limit(self):
        self.assertEqual(run(''.join(f'{i},u{i},success\n' for i in range(4097))).returncode,2)

    def test_row_limit(self):
        self.assertEqual(run('0,a,success\n'*100001).returncode,2)

    def test_large_timestamp_no_overflow(self):
        r=run(''.join(f'18446744073709551615,a,failure\n' for _ in range(5)))
        self.assertEqual(len(json.loads(r.stdout)['alerts']),1)

if __name__ == '__main__': unittest.main()
