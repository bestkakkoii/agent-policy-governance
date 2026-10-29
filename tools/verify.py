"""Run actual checks and emit an environment-bound report; never infer host approval."""
from __future__ import annotations

import ast
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
from policy_core.common import canonical, byte_digest
from policy_core.engine import load_catalog
from policy_core.runtime import policy_runtime
from tools.package import source_files, plugin_files, build


def run(command: list[str], environment: dict[str, str]) -> dict:
    started = time.perf_counter()
    result = subprocess.run(command, cwd=root, env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180, check=False)
    print(result.stdout, end="")
    print(result.stderr, end="", file=sys.stderr)
    return {"command": command, "exit_code": result.returncode, "duration_seconds": time.perf_counter()-started,
            "stdout": result.stdout, "stderr": result.stderr}


def main() -> int:
    if os.environ.get("APG_VERIFICATION_RESOLVED") != "1":
        from install import installed_python
        executable, _ = installed_python()
        return subprocess.run([executable, __file__], env={**os.environ, "APG_VERIFICATION_RESOLVED": "1", "PYTHONUTF8": "1"}, check=False).returncode
    environment = {**os.environ, "APG_TEST_PYTHON": sys.executable, "PYTHONUTF8": "1"}
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Existing Node.js >=22 is required to validate native JS/MCP; no runtime is downloaded")
    node_version = subprocess.check_output([node, "--version"], text=True).strip()
    if int(node_version.removeprefix("v").split(".")[0]) < 22:
        raise RuntimeError("Installed Node.js is too old; verification blocked without forcing installation")
    checks = []
    for path in sorted(root.rglob("*.py")):
        if not any(part in {"dist", ".git", ".venv"} for part in path.parts):
            ast.parse(path.read_text("utf-8-sig"), filename=str(path))
    checks.append({"check":"all_owned_python_ast", "exit_code":0})
    # Packaged skills must remain reproducible from the one catalog authority.
    for name, expected in plugin_files().items():
        if (root / "plugins/chatgpt" / name).read_bytes() != expected:
            raise RuntimeError("Generated preview is stale: " + name)
    checks.append({"check":"preview_catalog_consistency", "exit_code":0})
    for command in ([sys.executable,"-W","error","-m","unittest","discover","-s","tests","-v"],
                    [node,"--test","tests/registry.test.mjs","tests/opencode.test.mjs"]):
        checks.append(run(command, environment))
    for name in ["registry/handler.mjs","registry/worker.mjs","adapters/opencode/plugin.mjs"]:
        checks.append(run([node,"--check",name],environment))
    latencies = []
    with tempfile.TemporaryDirectory(prefix="apg_benchmark_") as directory:
        base=Path(directory); runtime=policy_runtime(base/"state")
        first=runtime.context(base,"benchmark","verify code quality",begin=True)
        for _ in range(100):
            start=time.perf_counter(); following=runtime.context(base,"benchmark","verify code quality",begin=True)
            latencies.append((time.perf_counter()-start)*1000)
        restored=runtime.context(base,"benchmark",fresh=True)
    latencies.sort()
    benchmark={"fixture":"generic software quality task, warm embedded core, 100 repeats", "first_context_bytes":len(first["context"].encode()),
               "unchanged_context_bytes":len(following["context"].encode()), "restored_context_bytes":len(restored["context"].encode()),
               "p50_ms":latencies[49],"p95_ms":latencies[94],"model_tokens_measured":None,
               "warning":"Byte reduction is not an end-to-end model-token or speed claim; OpenCode refreshes each system array."}
    artifacts=build(root/"dist")
    report={"schema_version":1,"python":sys.version,"node":node_version,"platform":platform.platform(),
            "source_files":{name:byte_digest(body) for name,body in source_files().items()},
            "policy_snapshot":load_catalog()["snapshot_id"],"checks":checks,"benchmark":benchmark,"packages":artifacts,
            "native_authenticated_model_sessions_tested":False,"chatgpt_deployed":False,"official_listing_approved":False}
    report["ok"]=all(item["exit_code"]==0 for item in checks)
    destination=root/"artifacts"; destination.mkdir(exist_ok=True)
    (destination/"verification.json").write_bytes(canonical(report)+b"\n")
    print(json.dumps({"ok":report["ok"],"benchmark":benchmark,"report":str(destination/"verification.json")},indent=2))
    return 0 if report["ok"] else 1


if __name__=="__main__":
    raise SystemExit(main())
