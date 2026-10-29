"""CLI entrypoint for read-only policy resolution."""

import argparse
import json
from pathlib import Path

from .engine import load_policy, resolve


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve applicable policy rules without changing a project")
    parser.add_argument("command", choices=("resolve",))
    parser.add_argument("--domain", required=True)
    parser.add_argument("--capability", required=True)
    parser.add_argument("--policy", type=Path, default=Path(__file__).resolve().parent.parent / "policies" / "seed.json")
    arguments = parser.parse_args()
    data = load_policy(arguments.policy)
    print(json.dumps(resolve(data, arguments.domain, arguments.capability), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
