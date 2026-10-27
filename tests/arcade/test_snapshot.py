import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/arcade/snapshot.py"
spec = importlib.util.spec_from_file_location("arcade_snapshot", SCRIPT)
snapshot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snapshot)


def run(repo, *args):
    return subprocess.run(['/usr/bin/git', '-C', str(repo), *args], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=True).stdout.decode().strip()


class SnapshotTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        self.home = self.root / 'home'
        self.work = self.root / 'work'
        for path in (self.repo, self.home, self.work):
            path.mkdir()
        run(self.repo, 'init', '-q')
        (self.repo / 'src').mkdir()
        (self.repo / 'src' / 'module.py').write_text('BASE_CONTENT\n')
        (self.repo / 'run').write_text('#!/bin/sh\nexit 0\n')
        os.chmod(self.repo / 'run', 0o755)
        self.commit()

    def tearDown(self):
        self.tmp.cleanup()

    def commit(self):
        run(self.repo, 'add', '-A')
        run(self.repo, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'test')
        self.base = run(self.repo, 'rev-parse', 'HEAD')

    def test_clean_base_not_dirty_or_untracked_and_exact_tree(self):
        (self.repo / 'src' / 'module.py').write_text('PRIVATE_DIRTY\n')
        (self.repo / 'private').write_text('PRIVATE_UNTRACKED\n')
        result = snapshot.materialize(self.repo, self.home, self.work, self.base)
        self.assertEqual(result['base_commit'], self.base)
        self.assertEqual((self.work / 'src' / 'module.py').read_text(), 'BASE_CONTENT\n')
        self.assertFalse((self.work / 'private').exists())
        self.assertTrue(os.access(self.work / 'run', os.X_OK))
        self.assertEqual(result['git_tree'], run(self.repo, 'rev-parse', self.base + '^{tree}'))
        self.assertEqual(run(self.work, 'remote'), '')
        self.assertEqual(json.loads(json.dumps(result))['tracked_files'], 2)

    def test_symlink_fails_closed_and_export_ignore_does_not_hide_file(self):
        (self.repo / 'link').symlink_to('../outside')
        self.commit()
        with self.assertRaisesRegex(ValueError, 'link'):
            snapshot.materialize(self.repo, self.home, self.work, self.base)
        self.assertFalse(any(self.work.iterdir()))
        (self.repo / 'link').unlink()
        (self.repo / '.gitattributes').write_text('src/module.py export-ignore\n')
        self.commit()
        snapshot.materialize(self.repo, self.home, self.work, self.base)
        self.assertEqual((self.work / 'src' / 'module.py').read_text(), 'BASE_CONTENT\n')

    def test_nonempty_and_wrong_sha_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'exact commit|git command'):
            snapshot.materialize(self.repo, self.home, self.work, '0' * 40)
        (self.work / 'occupied').write_text('x')
        with self.assertRaisesRegex(ValueError, 'empty directory'):
            snapshot.materialize(self.repo, self.home, self.work, self.base)

    def test_names_do_not_escape(self):
        for bad in ('../x', '/tmp/x', 'a/../x', 'a//x', '.git/config', 'a\\b'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                snapshot.safe_path(bad)


if __name__ == '__main__':
    unittest.main()
