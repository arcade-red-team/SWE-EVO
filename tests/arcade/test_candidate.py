"""Adversarial tests for candidate capture and independent patch construction."""

import importlib
import os
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

DIRECTORY = Path(__file__).resolve().parents[2] / "scripts/arcade"
sys.path.insert(0, str(DIRECTORY))
candidate = importlib.import_module("candidate")
snapshot = importlib.import_module("snapshot")
sys.path.remove(str(DIRECTORY))


class CandidateTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.src, self.home, self.base, self.work = (self.root / n for n in ("src", "home", "base", "work"))
        for directory in (self.src, self.home, self.base, self.work):
            directory.mkdir()
        (self.src / "keep.py").write_text("old\n")
        (self.src / "delete.py").write_text("delete\n")
        snapshot.git(self.src, self.home, "init", "-q")
        snapshot.git(self.src, self.home, "add", "--all")
        snapshot.git(self.src, self.home, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                     "commit", "-qm", "base")
        self.commit = snapshot.git(self.src, self.home, "rev-parse", "HEAD").decode().strip()
        self.tree = snapshot.materialize(self.src, self.home, self.base, self.commit)["git_tree"]
        snapshot.materialize(self.src, self.home, self.work, self.commit)

    def tearDown(self):
        self.temp.cleanup()

    def build(self):
        return candidate.build_patch(self.base, self.work, self.tree, self.root)

    def test_clean_and_changed_untracked_deleted_binary_executable(self):
        clean = self.build()
        self.assertEqual(clean["patch"], b"")
        self.assertEqual(clean["base_tree"], clean["candidate_tree"])
        (self.work / "keep.py").write_text("new\n")
        (self.work / "delete.py").unlink()
        (self.work / "new.dat").write_bytes(b"\0\x01binary\xff")
        (self.work / "executable").write_text("#!/bin/sh\n")
        os.chmod(self.work / "executable", 0o755)
        (self.work / ".hidden").write_text("included\n")
        # Tamper with agent-side metadata: candidate capture never invokes Git there.
        (self.work / ".git" / "HEAD").write_text("untrusted\n")
        result = self.build()
        self.assertNotEqual(result["candidate_tree"], self.tree)
        self.assertEqual(set(result["files"]), {"keep.py", "new.dat", "executable", ".hidden"})
        for path in (b"keep.py", b"delete.py", b"new.dat", b"executable", b".hidden"):
            self.assertIn(path, result["patch"])
        self.assertEqual(result["files"]["executable"][0], "100755")

    def test_symlink_special_files_and_hardlinks_fail_closed(self):
        outside = self.root / "outside"
        outside.write_text("private")
        for kind in ("symlink", "directory_symlink", "fifo", "hardlink"):
            target = self.work / "malicious"
            if kind in ("symlink", "directory_symlink"):
                target.symlink_to(outside if kind == "symlink" else self.root, target_is_directory=kind != "symlink")
            elif kind == "fifo":
                os.mkfifo(target)
            else:
                os.link(outside, target)
            try:
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    self.build()
            finally:
                target.unlink()

    def test_base_tree_and_candidate_changed_after_capture_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "base tree"):
            candidate.build_patch(self.base, self.work, "0" * 40, self.root)
        real_capture = candidate.capture
        count = 0

        def mutate_before_second_check(path, **kwargs):
            nonlocal count
            count += 1
            if count == 3:
                (self.work / "keep.py").write_text("raced\n")
            return real_capture(path, **kwargs)

        with patch.object(candidate, "capture", side_effect=mutate_before_second_check):
            with self.assertRaisesRegex(ValueError, "changed after capture"):
                self.build()

    def test_guard_snapshot_matches_capture_then_detects_mutation(self):
        (self.work / "extra").write_text("candidate\n")
        result = self.build()
        guard = self.root / "guard"
        guard.mkdir()
        candidate.materialize_capture(result["files"], result["candidate_sha256"], guard)
        candidate.verify_capture(guard, result["candidate_sha256"])
        self.assertFalse((guard / ".git").exists())
        (guard / ".git").mkdir()
        with self.assertRaisesRegex(ValueError, "Git metadata is not allowed"):
            candidate.verify_capture(guard, result["candidate_sha256"])
        (guard / ".git").rmdir()
        (guard / "empty").mkdir()
        with self.assertRaisesRegex(ValueError, "empty directory"):
            candidate.verify_capture(guard, result["candidate_sha256"])
        (guard / "empty").rmdir()
        target = guard / "extra"
        os.chmod(target, 0o600)
        target.write_text("tampered\n")
        with self.assertRaisesRegex(ValueError, "changed"):
            candidate.verify_capture(guard, result["candidate_sha256"])
        with self.assertRaisesRegex(ValueError, "does not match expected"):
            candidate.materialize_capture(result["files"], "0" * 64, guard)

    def test_git_metadata_symlink_and_nested_repository_fail_closed(self):
        (self.work / ".git").rename(self.work / ".old-git")
        (self.work / ".git").symlink_to(self.root)
        with self.assertRaisesRegex(ValueError, "Git metadata"):
            self.build()
        (self.work / ".git").unlink()
        (self.work / ".old-git").rename(self.work / ".git")
        (self.work / "nested" / ".git").mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "unsafe archive path"):
            self.build()


if __name__ == "__main__":
    unittest.main()
