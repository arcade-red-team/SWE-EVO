"""Prototype: capture a candidate without trusting its Git metadata.

The caller must stop agent and tool processes before capture and keep the
trusted temporary directory private. Double scanning detects ordinary changes,
not an adversary that races and restores between scans.
"""

import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile

import snapshot


def _identity(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
            value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def capture(workspace, *, allow_root_git=False):
    """Capture source bytes and Git modes; reject unsafe filesystem entries."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    root = os.open(workspace, flags)
    files = {}
    total = 0

    def walk(directory, prefix):
        nonlocal total
        before = os.fstat(directory)
        before_count = len(files)
        for name in sorted(os.listdir(directory)):
            if not isinstance(name, str):
                raise ValueError("unsupported filename")
            relative = f"{prefix}/{name}" if prefix else name
            if not prefix and name == ".git":
                if not allow_root_git:
                    raise ValueError("Git metadata is not allowed in guard snapshot")
                entry = os.stat(name, dir_fd=directory, follow_symlinks=False)
                if not stat.S_ISDIR(entry.st_mode):
                    raise ValueError("unsafe Git metadata path")
                continue
            snapshot.safe_path(relative)
            entry = os.stat(name, dir_fd=directory, follow_symlinks=False)
            if stat.S_ISDIR(entry.st_mode):
                child = os.open(name, flags, dir_fd=directory)
                try:
                    if _identity(entry) != _identity(os.fstat(child)):
                        raise ValueError("directory changed during capture")
                    walk(child, relative)
                finally:
                    os.close(child)
            elif stat.S_ISREG(entry.st_mode):
                if entry.st_nlink != 1 or entry.st_size > snapshot.MAX_CONTENT:
                    raise ValueError("hardlink or oversized file")
                fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
                try:
                    if _identity(entry) != _identity(os.fstat(fd)):
                        raise ValueError("file changed before reading")
                    chunks = []
                    remaining = entry.st_size
                    while remaining:
                        chunk = os.read(fd, min(remaining, 1024 * 1024))
                        if not chunk:
                            raise ValueError("file truncated during capture")
                        chunks.append(chunk)
                        remaining -= len(chunk)
                    if _identity(entry) != _identity(os.fstat(fd)):
                        raise ValueError("file changed during capture")
                    after = os.stat(name, dir_fd=directory, follow_symlinks=False)
                    if _identity(entry) != _identity(after):
                        raise ValueError("file replaced during capture")
                finally:
                    os.close(fd)
                contents = b"".join(chunks)
                total += len(contents)
                if total > snapshot.MAX_CONTENT or len(files) >= snapshot.MAX_FILES:
                    raise ValueError("candidate exceeds supported bounds")
                files[relative] = ("100755" if entry.st_mode & stat.S_IXUSR else "100644", contents)
            else:
                raise ValueError("symlink or special file is unsupported")
        if _identity(before) != _identity(os.fstat(directory)):
            raise ValueError("directory changed during capture")
        if prefix and len(files) == before_count:
            raise ValueError("empty directory is unsupported")

    try:
        walk(root, "")
    except OSError as error:
        raise ValueError("filesystem changed or could not be read") from error
    finally:
        os.close(root)
    return files


def digest(files):
    manifest = [{"path": name, "mode": mode, "sha256": hashlib.sha256(data).hexdigest()}
                for name, (mode, data) in sorted(files.items())]
    return hashlib.sha256(json.dumps(manifest, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def materialize_capture(files, expected_sha256, destination):
    """Write captured bytes for a guard; caller must recheck after guard runs."""
    if not isinstance(files, dict) or digest(files) != expected_sha256:
        raise ValueError("capture does not match expected digest")
    root = os.open(destination, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        if os.listdir(root):
            raise ValueError("guard destination must be empty")
        for name, (mode, data) in sorted(files.items()):
            path = snapshot.safe_path(name)
            if mode not in ("100644", "100755") or not isinstance(data, bytes):
                raise ValueError("invalid captured file")
            directory = os.dup(root)
            try:
                for part in path.parts[:-1]:
                    try:
                        os.mkdir(part, 0o700, dir_fd=directory)
                    except FileExistsError:
                        pass
                    child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                    os.close(directory)
                    directory = child
                fd = os.open(path.parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=directory)
                with os.fdopen(fd, "wb") as file:
                    file.write(data)
                    os.fchmod(file.fileno(), 0o500 if mode == "100755" else 0o400)
            finally:
                os.close(directory)
    finally:
        os.close(root)
    verify_capture(destination, expected_sha256)


def verify_capture(destination, expected_sha256):
    if digest(capture(destination)) != expected_sha256:
        raise ValueError("guard snapshot changed or does not match candidate")


def _git(repo, home, index, args, payload=None):
    env = snapshot.git_env(home)
    env["GIT_INDEX_FILE"] = str(index)
    result = subprocess.run(["/usr/bin/git", "-C", str(repo), *args], input=payload,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            env=env, timeout=120, close_fds=True, check=False)
    if result.returncode:
        raise ValueError("trusted Git operation failed")
    return result.stdout


def _tree(repo, home, index, files):
    _git(repo, home, index, ["read-tree", "--empty"])
    entries = []
    blobs = {}
    for name, (mode, data) in sorted(files.items()):
        oid = snapshot.blob_id(data)
        if oid in blobs and blobs[oid] != data:
            raise ValueError("distinct contents have identical Git object IDs")
        blobs[oid] = data
        entries.append(f"{mode} {oid}\t".encode() + name.encode("utf-8") + b"\0")
    # Numeric filenames avoid passing untrusted source names to the line-based
    # --stdin-paths interface. --no-filters preserves exact bytes.
    with tempfile.TemporaryDirectory(prefix="blobs-", dir=repo) as directory:
        paths = []
        for number, data in enumerate(blobs.values()):
            path = Path(directory) / str(number)
            path.write_bytes(data)
            paths.append(path.relative_to(repo).as_posix())
        if paths:
            actual = _git(repo, home, index, ["hash-object", "-w", "--stdin-paths", "--no-filters"],
                          ("\n".join(paths) + "\n").encode()).decode("ascii").splitlines()
            if actual != list(blobs):
                raise ValueError("written blobs did not match")
    if entries:
        _git(repo, home, index, ["update-index", "-z", "--index-info"], b"".join(entries))
    return _git(repo, home, index, ["write-tree"]).decode().strip()


def build_patch(base_workspace, candidate_workspace, expected_base_tree, temporary_parent):
    """Return patch bytes and capture identities after independent tree checks."""
    base = capture(base_workspace, allow_root_git=True)
    candidate = capture(candidate_workspace, allow_root_git=True)
    identity = digest(candidate)
    with tempfile.TemporaryDirectory(prefix="trusted-patch-", dir=temporary_parent) as directory:
        root = Path(directory)
        repo, home, index = root / "repo", root / "home", root / "index"
        repo.mkdir(mode=0o700)
        home.mkdir(mode=0o700)
        _git(repo, home, index, ["init", "-q"])
        base_tree = _tree(repo, home, index, base)
        if base_tree != expected_base_tree:
            raise ValueError("base tree differs from committed tree")
        candidate_tree = _tree(repo, home, index, candidate)
        patch = _git(repo, home, index, ["diff", "--binary", "--full-index", "--no-ext-diff",
                                           "--no-textconv", "--no-renames", base_tree, candidate_tree])
        _git(repo, home, index, ["read-tree", base_tree])
        if patch:
            _git(repo, home, index, ["apply", "--cached", "--binary", "--whitespace=nowarn", "-"], patch)
        if _git(repo, home, index, ["write-tree"]).decode().strip() != candidate_tree:
            raise ValueError("patch does not reproduce candidate tree")
    if digest(capture(candidate_workspace, allow_root_git=True)) != identity:
        raise ValueError("candidate changed after capture")
    return {"patch": patch, "base_tree": base_tree, "candidate_tree": candidate_tree,
            "candidate_sha256": identity, "files": candidate}
