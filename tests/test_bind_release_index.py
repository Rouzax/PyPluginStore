import hashlib
import json

import pytest

from conftest import REPO_ROOT, load_module_from_path


bind = load_module_from_path(
    "bind_release_index", REPO_ROOT / ".github/scripts/bind_release_index.py"
)

OLD_REGISTRY = b'{"plugins": []}\n'
NEW_REGISTRY = b'{"plugins": [1]}\n'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def index(sequence: int, registry: bytes) -> dict:
    return {"sequence": sequence, "registry_sha256": sha(registry), "releases": []}


def test_rebinds_hash_without_previous_keeps_sequence() -> None:
    bound = bind.bind_release_index(index(21, OLD_REGISTRY), NEW_REGISTRY)

    assert bound["registry_sha256"] == sha(NEW_REGISTRY)
    assert bound["sequence"] == 21


def test_bumps_sequence_when_binding_changed() -> None:
    # Contributor PR already rebound the hash; sequence still matches master.
    current = index(21, NEW_REGISTRY)

    bound = bind.bind_release_index(current, NEW_REGISTRY, index(21, OLD_REGISTRY))

    assert bound["sequence"] == 22
    assert current["sequence"] == 21


def test_keeps_sequence_when_binding_unchanged() -> None:
    bound = bind.bind_release_index(
        index(21, OLD_REGISTRY), OLD_REGISTRY, index(21, OLD_REGISTRY)
    )

    assert bound["sequence"] == 21


def test_keeps_sequence_already_raised_by_generator() -> None:
    bound = bind.bind_release_index(
        index(25, NEW_REGISTRY), NEW_REGISTRY, index(21, OLD_REGISTRY)
    )

    assert bound["sequence"] == 25


def test_rejects_invalid_previous_sequence() -> None:
    previous = {"sequence": True, "registry_sha256": sha(OLD_REGISTRY)}

    with pytest.raises(ValueError):
        bind.bind_release_index(index(21, NEW_REGISTRY), NEW_REGISTRY, previous)


def test_main_writes_only_on_change(tmp_path) -> None:
    registry = tmp_path / "registry.json"
    registry.write_bytes(NEW_REGISTRY)
    current = tmp_path / "release_index.json"
    current.write_text(json.dumps(index(21, NEW_REGISTRY)), encoding="utf-8")
    previous = tmp_path / "previous.json"
    previous.write_text(json.dumps(index(21, OLD_REGISTRY)), encoding="utf-8")

    args = ["--registry", str(registry), "--index", str(current)]
    assert bind.main(args) == 0
    assert json.loads(current.read_text(encoding="utf-8"))["sequence"] == 21

    assert bind.main([*args, "--previous", str(previous)]) == 0
    written = current.read_text(encoding="utf-8")
    assert json.loads(written)["sequence"] == 22
    assert written.endswith("}\n")
