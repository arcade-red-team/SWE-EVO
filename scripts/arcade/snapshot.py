"""Materialize and verify a Git base in an isolated neutral workspace.

This module never starts an agent. Base snapshots with links, submodules,
unsupported object formats or oversized data are rejected, not repaired.
"""
import hashlib
import io
import os
from pathlib import PurePosixPath
import re
import subprocess

BASE_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
MAX_FILES = 20000
MAX_CONTENT = 200 * 1024 * 1024


def git_env(home):
    return {"PATH": "/usr/bin:/bin", "HOME": str(home), "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
            "GIT_TERMINAL_PROMPT": "0", "GIT_ATTR_NOSYSTEM": "1"}


def git(repo, home, *args):
    result = subprocess.run(["/usr/bin/git", "-C", str(repo), *args], env=git_env(home),
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=120,
                            check=False, close_fds=True)
    if result.returncode:
        raise ValueError("git command failed")
    return result.stdout


def safe_path(name):
    if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
        raise ValueError("invalid archive path")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in ("", ".", "..") or part.casefold() == ".git" for part in path.parts):
        raise ValueError("unsafe archive path")
    if str(path) != name:
        raise ValueError("noncanonical archive path")
    return path


def inventory(repo, home, base):
    if not BASE_PATTERN.fullmatch(base):
        raise ValueError("invalid base SHA")
    fmt = git(repo, home, "rev-parse", "--show-object-format").decode().strip()
    if fmt != "sha1":
        raise ValueError("unsupported Git object format")
    resolved = git(repo, home, "rev-parse", "--verify", base + "^{commit}").decode().strip()
    if resolved != base:
        raise ValueError("base is not an exact commit")
    tree = git(repo, home, "rev-parse", base + "^{tree}").decode().strip()
    data = git(repo, home, "ls-tree", "-rz", "--full-tree", "-l", base)
    files, total = {}, 0
    for entry in data.split(b"\0"):
        if not entry:
            continue
        metadata, name_raw = entry.split(b"\t", 1)
        mode, kind, oid, size = metadata.decode("ascii").split()
        name = name_raw.decode("utf-8")
        path = safe_path(name)
        if kind != "blob" or mode not in ("100644", "100755"):
            raise ValueError("snapshot contains a link, submodule or unsupported mode")
        size = int(size)
        files[str(path)] = (mode, oid, size)
        total += size
    if not files or len(files) > MAX_FILES or total > MAX_CONTENT:
        raise ValueError("snapshot size is unsupported")
    return files, tree


def blob_id(data):
    digest = hashlib.sha1(usedforsecurity=False)
    digest.update(f"blob {len(data)}\0".encode())
    digest.update(data)
    return digest.hexdigest()


def materialize(repo, home, workspace, base):
    """Build and verify a source-only repo in an empty newly created folder."""
    if not workspace.is_dir() or any(workspace.iterdir()):
        raise ValueError("workspace must be an existing empty directory")
    files, expected_tree = inventory(repo, home, base)
    requests = b"".join((oid + "\n").encode("ascii") for _, oid, _ in files.values())
    proc = subprocess.run(["/usr/bin/git", "-C", str(repo), "cat-file", "--batch"],
                          input=requests, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                          env=git_env(home), timeout=120, check=False, close_fds=True)
    if proc.returncode:
        raise ValueError("git object read failed")
    stream = io.BytesIO(proc.stdout)
    for name, (mode, oid, size) in files.items():
        header = stream.readline(1024).decode("ascii").strip().split()
        if header != [oid, "blob", str(size)]:
            raise ValueError("Git object header differs from commit inventory")
        data = stream.read(size)
        if len(data) != size or stream.read(1) != b"\n" or blob_id(data) != oid:
            raise ValueError("Git object content differs from commit")
        path = safe_path(name)
        target = workspace.joinpath(*path.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as output:
            output.write(data)
        os.chmod(target, 0o755 if mode == "100755" else 0o644)
    if stream.read(1):
        raise ValueError("unexpected data after Git objects")
    git(workspace, home, "init", "-q")
    git(workspace, home, "add", "--force", "--all")
    # Fixed identity and isolated git config avoid embedding user information.
    git(workspace, home, "-c", "user.name=Benchmark", "-c", "user.email=benchmark@example.invalid",
        "commit", "-qm", "Snapshot")
    observed = git(workspace, home, "rev-parse", "HEAD^{tree}").decode().strip()
    if observed != expected_tree:
        raise ValueError("materialized tree differs from original commit")
    return {"base_commit": base, "git_tree": observed, "tracked_files": len(files)}
