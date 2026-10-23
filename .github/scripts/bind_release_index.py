# Copyright (C) 2018-2026 adrighem and PyPluginStore contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Bind release_index.json to registry.json bytes.

Clients only accept a remote metadata pair whose sequence exceeds their
durable watermark. A registry change that rebinds the hash without raising
the sequence is therefore ignored by every install that already trusts the
current sequence. With --previous, the sequence is raised whenever the
binding changed relative to that previously published index.
"""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def bind_release_index(
    index: dict[str, Any],
    registry_bytes: bytes,
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a copy of index bound to registry_bytes."""
    bound = dict(index)
    bound["registry_sha256"] = hashlib.sha256(registry_bytes).hexdigest()
    if previous is None:
        return bound
    previous_sequence = previous["sequence"]
    if not isinstance(previous_sequence, int) or isinstance(previous_sequence, bool):
        raise ValueError("previous release_index.sequence must be an integer.")
    binding_changed = bound["registry_sha256"] != previous["registry_sha256"]
    if binding_changed and bound["sequence"] <= previous_sequence:
        bound["sequence"] = previous_sequence + 1
    return bound


def _read_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path("registry.json"))
    parser.add_argument("--index", type=Path, default=Path("release_index.json"))
    parser.add_argument(
        "--previous",
        type=Path,
        help="Previously published release_index.json; enables sequence bump.",
    )
    args = parser.parse_args(argv)

    index = _read_json(args.index)
    previous = _read_json(args.previous) if args.previous else None
    bound = bind_release_index(index, args.registry.read_bytes(), previous)
    if bound != index:
        with args.index.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(bound, handle, indent=2)
            handle.write("\n")
        print(
            f"Bound {args.index} to sha256 {bound['registry_sha256']}"
            f" at sequence {bound['sequence']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
