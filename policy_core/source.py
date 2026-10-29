"""Private source import: immutable bytes, bounded archive handling, exact-line lookup."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from .common import atomic_write, byte_digest, read_json, require, write_json


def import_source(home: Path, archive: Path) -> dict[str, Any]:
    require(archive.stat().st_size <= 16 * 1024 * 1024, "archive_too_large", "Source archive exceeds import limit")
    raw = archive.read_bytes()
    archive_hash = byte_digest(raw)
    collected: dict[str, bytes] = {}
    with zipfile.ZipFile(archive) as source:
        require(len(source.infolist()) <= 512, "archive_entries", "Too many source entries")
        total = 0
        for info in source.infolist():
            path = PurePosixPath(info.filename)
            require(not path.is_absolute() and ".." not in path.parts and "\\" not in info.filename,
                    "archive_path", "Unsafe source archive path", path=info.filename)
            require((info.external_attr >> 16) & 0o170000 != 0o120000, "archive_symlink", "Source symlinks are forbidden")
            if info.is_dir():
                continue
            require(path.suffix == ".md" and info.file_size <= 2 * 1024 * 1024, "source_file_type", "Only bounded Markdown source documents are accepted")
            total += info.file_size
            require(total <= 16 * 1024 * 1024, "archive_expansion", "Archive expanded beyond limit")
            require(path.name not in collected, "source_name_collision", "Source basenames must be unique")
            data = source.read(info)
            data.decode("utf-8-sig")
            collected[path.name] = data
    require("sha256_sums.md" in collected, "source_manifest_missing", "The source's checksum manifest is required")
    manifest_text = collected["sha256_sums.md"].decode("utf-8-sig")
    entries = re.findall(r"\b([a-fA-F0-9]{64})\s+[*`]?([^\s`|]+)", manifest_text)
    # The whitepaper uses a Markdown table: filename | sha256.
    if not entries:
        entries = [(checksum, name.strip(" `")) for name, checksum in re.findall(r"\|\s*([^|]+?)\s*\|\s*`?([a-fA-F0-9]{64})`?\s*\|", manifest_text)]
    require(bool(entries), "source_manifest_invalid", "No checksum entries found")
    verified = set()
    for expected, name in entries:
        link = re.fullmatch(r"\[([^\]]+)\]\(([^)]+)\)", name)
        if link:
            name = link.group(2)
        name = PurePosixPath(name).name
        require(name in collected and byte_digest(collected[name]) == expected.lower(), "source_hash_mismatch", "Source checksum mismatch", file=name)
        verified.add(name)
    require(verified == set(collected) - {"sha256_sums.md"}, "source_unlisted", "Every source document must be covered by the source manifest")
    directory = home / "sources" / archive_hash
    for name, data in collected.items():
        destination = directory / name
        require(not destination.exists() or destination.read_bytes() == data, "source_changed", "Immutable source changed")
        if not destination.exists():
            atomic_write(destination, data, private=True)
    index = {"archive_sha256": archive_hash, "files": {name: byte_digest(data) for name, data in collected.items()}}
    write_json(directory / "index.json", index, private=True)
    return {"ok": True, "source_id": archive_hash, "verified_files": len(verified), "privacy": "local_only"}


def read_source(home: Path, source_id: str, name: str, start: int, count: int) -> dict[str, Any]:
    require(re.fullmatch(r"[a-f0-9]{64}", source_id) is not None, "source_id", "Invalid source digest")
    require(Path(name).name == name and "\\" not in name and "/" not in name,
            "source_path", "Use an indexed source basename")
    require(start >= 1 and 1 <= count <= 200, "source_range", "Read one to 200 source lines at a time")
    directory = home / "sources" / source_id
    index = read_json(directory / "index.json")
    require(name in index["files"], "source_missing", "Unknown source document")
    raw = (directory / name).read_bytes()
    require(byte_digest(raw) == index["files"][name], "source_changed", "Source hash mismatch")
    lines = raw.decode("utf-8-sig").splitlines()
    return {"ok": True, "source_id": source_id, "file": name, "start_line": start,
            "lines": lines[start - 1:start - 1 + count], "total_lines": len(lines)}
