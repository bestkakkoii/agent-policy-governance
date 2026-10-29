"""Bounded persistence and diagnostics shared by embedded and service modes."""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import sqlite3
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

version = "0.2.0"
max_json_bytes = 8 * 1024 * 1024


class policy_error(RuntimeError):
    """A stable error code plus the original actionable cause."""

    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = code
        self.details = details

    def record(self) -> dict[str, Any]:
        return {"ok": False, "error": self.code, "message": str(self), **self.details}


def require(condition: bool, code: str, message: str, **details: Any) -> None:
    if not condition:
        raise policy_error(code, message, **details)


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def byte_digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, "duplicate_json_key", "Duplicate JSON key", key=key)
        result[key] = value
    return result


def invalid_constant(value: str) -> None:
    raise policy_error("invalid_json_constant", "Non-finite JSON number", value=value)


def decode_json(raw: str | bytes) -> Any:
    size = len(raw.encode("utf-8")) if isinstance(raw, str) else len(raw)
    require(size <= max_json_bytes, "input_too_large", "JSON input exceeds size limit")
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8-sig")
    return json.loads(raw, object_pairs_hook=unique_pairs, parse_constant=invalid_constant)


def read_json(path: Path) -> Any:
    with path.open("rb") as stream:
        return decode_json(stream.read(max_json_bytes + 1))


def atomic_write(path: Path, data: bytes, *, private: bool = False) -> None:
    """Replace one owned file; never follow a symlink at the destination."""
    require(not path.is_symlink(), "unsafe_symlink", "Refusing to replace a symlink", path=str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".apg_", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if private:
            temporary_path.chmod(0o600)
        elif path.exists():
            temporary_path.chmod(path.stat().st_mode & 0o777)
        else:
            temporary_path.chmod(0o644)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def write_json(path: Path, value: Any, *, private: bool = False) -> None:
    atomic_write(path, canonical(value) + b"\n", private=private)


def default_home() -> Path:
    override = os.environ.get("APG_HOME")
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "agent_policy_governance"
    return Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "agent_policy_governance"


class state_store:
    """SQLite transactions serialize concurrent adapters without a required daemon."""

    def __init__(self, home: Path) -> None:
        self.home = home.resolve()
        self.home.mkdir(parents=True, exist_ok=True)
        self.path = self.home / "state.sqlite3"
        require(not self.path.is_symlink(), "unsafe_symlink", "State database cannot be a symlink")
        with self.connection() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS documents (
                    kind TEXT NOT NULL, name TEXT NOT NULL, body TEXT NOT NULL,
                    updated REAL NOT NULL, PRIMARY KEY(kind, name));
                CREATE TABLE IF NOT EXISTS audit (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    created REAL NOT NULL, event TEXT NOT NULL, body TEXT NOT NULL);
            """)
        if os.name != "nt":
            self.home.chmod(0o700)
            self.path.chmod(0o600)

    @contextlib.contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA synchronous=FULL")
        try:
            yield connection
        finally:
            connection.close()

    @contextlib.contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
                connection.execute("COMMIT")
            except BaseException:
                connection.execute("ROLLBACK")
                raise

    @staticmethod
    def get(connection: sqlite3.Connection, kind: str, name: str) -> Any:
        row = connection.execute("SELECT body FROM documents WHERE kind=? AND name=?", (kind, name)).fetchone()
        return None if row is None else decode_json(row[0])

    @staticmethod
    def put(connection: sqlite3.Connection, kind: str, name: str, value: Any) -> None:
        connection.execute(
            "INSERT INTO documents VALUES (?,?,?,?) ON CONFLICT(kind,name) "
            "DO UPDATE SET body=excluded.body, updated=excluded.updated",
            (kind, name, canonical(value).decode(), time.time()),
        )

    @staticmethod
    def items(connection: sqlite3.Connection, kind: str) -> list[tuple[str, Any]]:
        return [(row[0], decode_json(row[1])) for row in connection.execute(
            "SELECT name,body FROM documents WHERE kind=? ORDER BY name", (kind,))]

    @staticmethod
    def audit(connection: sqlite3.Connection, event: str, value: Any) -> None:
        connection.execute("INSERT INTO audit(created,event,body) VALUES (?,?,?)",
                           (time.time(), event, canonical(value).decode()))
        connection.execute("DELETE FROM audit WHERE sequence <= "
                           "COALESCE((SELECT MAX(sequence)-2000 FROM audit),0)")


@contextlib.contextmanager
def file_lock(path: Path, timeout: float = 5.0) -> Iterator[None]:
    """OS-owned advisory lock: process death releases it without guessing stale PIDs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    require(not path.is_symlink(), "unsafe_symlink", "Lock file cannot be a symlink")
    with path.open("a+b") as stream:
        if stream.tell() == 0:
            stream.write(b"\0")
            stream.flush()
        deadline = time.monotonic() + timeout
        acquired = False
        try:
            while not acquired:
                try:
                    stream.seek(0)
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                except (BlockingIOError, PermissionError):
                    require(time.monotonic() < deadline, "lock_timeout", "Another policy operation holds the lock", path=str(path))
                    time.sleep(0.025)
            yield
        finally:
            if acquired:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
