"""``scripts/run_cascade.py`` is a thin, untested CLI wrapper (AUDIT_2026_11_01_ITEM_10): it must
not let an unsealed run look like a success. A caller relying on the process exit code (CI, a
supervisor script) has to be able to tell "sealed" apart from "ran, sealed nothing" without
parsing stdout text."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "run_cascade.py"


def _load_run_cascade_script():
    spec = importlib.util.spec_from_file_location("run_cascade_script", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _fake_cascade_result() -> SimpleNamespace:
    return SimpleNamespace(
        invocation=SimpleNamespace(invocation_id="fake-invocation"),
        provider_calls=0,
        review_verdict=SimpleNamespace(verdict="ACCEPT", findings=()),
        readme_path=Path("README.md"),
        entry=object(),
        source_revision="deadbeef",
        document=object(),
        out_dir=Path("out"),
        facts_path=Path("facts.json"),
    )


def test_an_unsealed_run_exits_non_zero_rather_than_looking_like_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_run_cascade_script()
    monkeypatch.setattr(module, "run_cascade", lambda *a, **k: _fake_cascade_result())
    monkeypatch.setattr(module, "load_gateway_config", lambda *a, **k: object())
    monkeypatch.setattr(module, "load_manifests", lambda *a, **k: object())

    def _raise_not_implemented(*_a: object, **_k: object) -> None:
        raise NotImplementedError("already sealed")

    monkeypatch.setattr(module, "seal_candidate", _raise_not_implemented)
    monkeypatch.setattr(sys, "argv", ["run_cascade.py", "owner/repo", "python", "/tmp/clone"])

    with pytest.raises(SystemExit) as excinfo:
        module.main()
    assert excinfo.value.code != 0


def test_falsifier_a_sealed_run_does_not_call_sys_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The falsifier for the fix above: reverting it (having the except branch `return` instead
    of `sys.exit(1)`) must make the first test fail. This test pins the companion behaviour --
    a genuinely sealed run must NOT raise SystemExit at all -- so the fix cannot be satisfied by
    always exiting non-zero regardless of outcome."""
    module = _load_run_cascade_script()
    monkeypatch.setattr(module, "run_cascade", lambda *a, **k: _fake_cascade_result())
    monkeypatch.setattr(module, "load_gateway_config", lambda *a, **k: object())
    monkeypatch.setattr(module, "load_manifests", lambda *a, **k: object())
    monkeypatch.setattr(
        module,
        "seal_candidate",
        lambda *a, **k: SimpleNamespace(bundle="owner__repo/deadbeef", state="ACCEPTED"),
    )
    monkeypatch.setattr(sys, "argv", ["run_cascade.py", "owner/repo", "python", "/tmp/clone"])

    module.main()
