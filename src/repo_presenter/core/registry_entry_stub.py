"""Placeholder stand-in for the old repository's ``core/registry/models.RegistryEntry``.

``migration/reuse-manifest.yaml`` lists "registry / product discovery / processability / source
snapshots and safe git clones" as PENDING_REVIEW -- not yet read or ported in this repository.
``readme.correction.model.Context`` still needs a typed ``entry`` field (every detector signature
in the old repo takes one), so this module gives it the smallest shape actually read by the
detectors ported so far (none of them read any attribute of ``entry`` at all -- ``links``,
``examples``, ``gaps`` and ``structure`` only read ``ctx.facts``, ``ctx.lines`` and ``ctx.readme``).

This is NOT a port of the real ``RegistryEntry`` (a pydantic model with ``mode``, ``issues_mode``,
``policy_profile``, ``provider_identity`` and coordinate-naming validation against
``core/registry/naming.py``, none of which exist in this repository yet). Replace this stub with
the real port, in one pass, the day a detector or caller needs more than ``repository``/``family``/
``platform``/``ecosystem`` -- ``stale.py``, ``sections.py`` and ``additions.py`` (deferred; see the
readme_correction/ entry in migration/reuse-manifest.yaml) will need ``ecosystem`` the moment they
are ported, because they resolve an ``EcosystemSpec`` from it.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegistryEntryStub:
    """Just enough of a registry entry for ``Context.entry`` to be constructible in tests and by
    any future caller, until the real registry (``core/registry/``) is ported."""

    repository: str
    family: str = ""
    platform: str = ""
    ecosystem: str = ""
