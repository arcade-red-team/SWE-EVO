import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts' / 'arcade' / 'analyze.py'
spec = importlib.util.spec_from_file_location('arcade_analyze', SCRIPT)
analyze = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analyze)


def fixture():
    tasks = {'a': 'repo1', 'b': 'repo2'}
    rows = []
    for task_id in tasks:
        for seed in (1, 2, 3):
            for mode in ('baseline', 'arcade'):
                rows.append({'task_id': task_id, 'seed': seed, 'mode': mode,
                             'status': 'measured', 'resolved': mode == 'arcade',
                             'metrics': {'fix_rate': 0.7 if mode == 'arcade' else 0.2}})
    return tasks, rows


class AnalyzeTest(unittest.TestCase):
    def run_fixture(self, rows, tasks=None):
        if tasks is None:
            tasks = {'a': 'repo1', 'b': 'repo2'}
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / 'manifest.json'
            outcomes = Path(directory) / 'outcomes.jsonl'
            manifest.write_text(json.dumps({'tasks': [{'id': key, 'repo': repo} for key, repo in tasks.items()]}))
            outcomes.write_text(''.join(json.dumps(row) + '\n' for row in rows))
            return subprocess.run([sys.executable, str(SCRIPT), '--manifest', str(manifest),
                                   '--outcomes', str(outcomes), '--metric', 'fix_rate',
                                   '--expected-tasks', '2', '--analysis-seed', '123', '--draws', '200'],
                                  text=True, capture_output=True, check=False)

    def test_clean_paired_data_and_determinism(self):
        _, rows = fixture()
        one = self.run_fixture(rows)
        two = self.run_fixture(rows)
        self.assertEqual(one.returncode, 0, one.stderr)
        self.assertEqual(one.stdout, two.stdout)
        result = json.loads(one.stdout)['groups']['all']
        self.assertEqual(result['n_tasks'], 2)
        self.assertEqual(result['resolve_by_seed']['1']['arcade_only'], 2)
        self.assertEqual(result['resolve_by_seed']['1']['p_two_sided_exact'], 0.5)
        self.assertEqual(result['resolve_by_seed']['1']['paired_difference'], 1)
        self.assertEqual(result['resolve_by_seed']['1']['difference_95_percentile_bootstrap_ci'], [1, 1])
        self.assertAlmostEqual(result['continuous_metric']['mean_paired_difference'], 0.5)
        self.assertEqual(result['continuous_metric']['paired_sign_flip']['p_two_sided'], 0.5)

    def test_mcnemar_zero_and_unbalanced_discordance(self):
        self.assertEqual(analyze.exact_mcnemar([False, True], [False, True])['p_two_sided_exact'], 1)
        result = analyze.exact_mcnemar([False] * 5, [True] * 5)
        self.assertEqual(result['p_two_sided_exact'], 0.0625)
        self.assertEqual(result['arcade_only'], 5)

    def test_missing_seed_mode_or_whole_task_fails_closed(self):
        _, rows = fixture()
        for altered in (rows[:-1], [row for row in rows if row['task_id'] != 'b']):
            proc = self.run_fixture(altered)
            self.assertEqual(proc.returncode, 2)
            self.assertEqual(proc.stdout, '')
            self.assertIn('missing', proc.stderr)

    def test_duplicate_invalid_and_nonfinite_fail_closed(self):
        _, rows = fixture()
        cases = [rows + [rows[0]],
                 [dict(row, status='timeout') if i == 0 else row for i, row in enumerate(rows)],
                 [dict(row, resolved=1) if i == 0 else row for i, row in enumerate(rows)],
                 [dict(row, metrics={'fix_rate': None}) if i == 0 else row for i, row in enumerate(rows)],
                 [dict(row, metrics={'fix_rate': float('nan')}) if i == 0 else row for i, row in enumerate(rows)]]
        for altered in cases:
            proc = self.run_fixture(altered)
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertEqual(proc.stdout, '')

    def test_manifest_count_prevents_silently_analyzing_subset(self):
        _, rows = fixture()
        proc = self.run_fixture([row for row in rows if row['task_id'] == 'a'], {'a': 'repo1'})
        self.assertEqual(proc.returncode, 2)
        self.assertIn('expected 2 tasks', proc.stderr)

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ValueError):
            analyze.read_json('{"seed":1,"seed":2}')


if __name__ == '__main__':
    unittest.main()
