"""Controls for recovery probe base binding and file ownership."""

import importlib.util
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/arcade/recovery_probe.py"
spec = importlib.util.spec_from_file_location("recovery_probe", SCRIPT)
assert spec and spec.loader
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class RecoveryProbeTest(unittest.TestCase):
    def test_clean_checkout_and_wrong_base(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "source.py").write_text("def f(): pass\n", encoding="utf-8")
            subprocess.run(["git", "add", "source.py"], cwd=root, check=True)
            subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "base"], cwd=root, check=True)
            actual = probe.git(root, "rev-parse", "HEAD")
            probe.verify_checkout(root, actual)
            with self.assertRaisesRegex(ValueError, "does not equal"):
                probe.verify_checkout(root, "0" * 40)
            self.assertEqual(probe.git(root, "status", "--porcelain"), "")
            (root / "source.py").write_text("changed\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "changes"):
                probe.verify_checkout(root, actual)

    def test_detects_split_files_and_missing_entity_assignment(self):
        graph = SimpleNamespace(entities={"one": SimpleNamespace(file_path="x.py"),
                                          "two": SimpleNamespace(file_path="x.py")})
        architecture = SimpleNamespace(components=[SimpleNamespace(name="a", entities=["one"]),
                                                    SimpleNamespace(name="b", entities=["two"])])
        self.assertEqual(probe.file_membership(graph, architecture), {"x.py": ["a", "b"]})
        architecture.components.pop()
        with self.assertRaisesRegex(ValueError, "did not assign"):
            probe.file_membership(graph, architecture)

    def test_output_inside_checkout_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(probe.main(["--checkout", str(root), "--base-sha", "0" * 40,
                                         "--output", str(root / "evidence.json")]), 1)
            self.assertFalse((root / "evidence.json").exists())

    def test_source_digest_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "actual.py").write_text("public\n", encoding="utf-8")
            (root / "alias.py").symlink_to(root / "actual.py")
            with self.assertRaisesRegex(ValueError, "symlink"):
                probe.source_digest(root, ["alias.py"])


if __name__ == "__main__":
    unittest.main()
