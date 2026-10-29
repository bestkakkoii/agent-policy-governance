"""Select the newest suitable installed Python, then run the authorized installer."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def installed_python() -> tuple[str, list[dict[str, str]]]:
    candidates = {str(Path(sys.executable).resolve())}
    diagnostics = []
    for directory in os.get_exec_path():
        try:
            for entry in Path(directory).iterdir():
                if re.fullmatch(r"python(?:3(?:\.\d+)?)?(?:\.exe)?", entry.name, re.IGNORECASE) and entry.is_file():
                    candidates.add(str(entry.resolve()))
        except (FileNotFoundError, NotADirectoryError, PermissionError):
            continue  # Absent PATH entries are not installed runtimes.
    if os.name == "nt" and shutil.which("py"):
        try:
            listing = subprocess.run(["py", "-0p"], capture_output=True, text=True, timeout=4, check=False)
            for line in listing.stdout.splitlines():
                match = re.search(r"([a-zA-Z]:\\.+\.exe)\s*$", line)
                if match:
                    candidates.add(match.group(1))
        except (OSError, subprocess.TimeoutExpired) as error:
            diagnostics.append({"candidate": "py launcher", "reason": str(error)})
    usable = []
    for candidate in sorted(candidates):
        try:
            result = subprocess.run([candidate, "-I", "-c", "import json,sys;print(json.dumps(list(sys.version_info[:3])))"],
                                    capture_output=True, text=True, timeout=3, check=False)
            if result.returncode != 0:
                diagnostics.append({"candidate": candidate, "reason": result.stderr.strip() or "Probe failed"})
                continue
            observed = json.loads(result.stdout)
            if len(observed) == 3 and all(isinstance(item, int) for item in observed) and tuple(observed) >= (3, 13, 0):
                usable.append((tuple(observed), candidate))
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            diagnostics.append({"candidate": candidate, "reason": str(error)})
    if not usable:
        raise RuntimeError("No suitable installed Python >=3.13 was found. No runtime was downloaded. Probe diagnostics: " + json.dumps(diagnostics))
    return max(usable)[1], diagnostics


if __name__ == "__main__":
    try:
        executable, diagnostics = installed_python()
        print(json.dumps({"stage": "environment_resolution", "selected_python": executable,
                          "probe_diagnostics": diagnostics, "downloads": False}), file=sys.stderr)
        result = subprocess.run([executable, str(Path(__file__).resolve().parent / "apg.py"), "install", *sys.argv[1:]], check=False)
        raise SystemExit(result.returncode)
    except (OSError, RuntimeError) as error:
        print(json.dumps({"ok": False, "stage": "bootstrap", "message": str(error)}), file=sys.stderr)
        raise SystemExit(2)
