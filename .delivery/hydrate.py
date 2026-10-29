"""Verify the source transfer identity before materializing reviewed source."""
import hashlib
import json
import lzma
import sys
from pathlib import Path, PurePosixPath

expected = "6e18075252ed28ed3487abd2becf5a3af14684f33987f45ff8cd7b95bcfd4695"
base = Path(__file__).resolve().parent
raw = b"".join((base / f"part_{index:02d}.xz").read_bytes() for index in range(12))
if hashlib.sha256(raw).hexdigest() != expected:
    raise RuntimeError("Source delivery checksum mismatch")
decoder = lzma.LZMADecompressor()
plain = decoder.decompress(raw, max_length=2_000_000)
if not decoder.eof or decoder.unused_data:
    raise RuntimeError("Invalid or oversized source transfer")
files = json.loads(plain)
if not isinstance(files, dict) or len(files) != 63:
    raise RuntimeError("Unexpected source manifest")
out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=True)
for name, content in files.items():
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"..", ".git"} for part in path.parts) or "\\" in name or not isinstance(content, str):
        raise RuntimeError(f"Unsafe source path: {name}")
    destination = out.joinpath(*path.parts)
    if not destination.resolve().is_relative_to(out) or destination.is_symlink():
        raise RuntimeError(f"Source path escapes destination: {name}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content.encode("utf-8"))
print(json.dumps({"source_transfer_sha256": expected, "files": len(files), "destination": str(out)}))
