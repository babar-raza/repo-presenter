"""Independent export-surface probes: a second, genuinely separate code path per ecosystem.

TC-017a. `extractors/surface/extractor.py`'s `surface_symbols` is the main extractor's own
symbol walk; it already refuses to trust its own `reachable: False` mark alone (see that
function's docstring) because the vendored engine's best-effort scan is "measurably wrong in
both directions for Rust." Nobody had ever supplied the independent `confirms_unreachable`
check it accepts, and nothing existed to let a later acceptance mechanism check a claim like
"this type is exported" against anything other than the engine that produced the claim in the
first place.

This package is that second path, one module per ecosystem (``python``, ``typescript``,
``cpp``, ``java``, ``go``, ``dotnet``, ``rust``). Every module exposes the same three-valued
contract:

- ``count(repo_root, kind) -> int | None`` -- how many public symbols of ``kind`` the probe can
  count, or ``None`` when it cannot determine a count for that kind in that ecosystem.
- ``exists(repo_root, qualified_name) -> bool | None`` -- whether the named symbol is declared
  anywhere in the source (public or private), or ``None`` when genuinely unknown.
- ``exported(repo_root, qualified_name) -> bool | None`` -- whether the named symbol is
  reachable from the ecosystem's own public entry point, or ``None`` when genuinely unknown.

``None`` means UNKNOWN. It is never coerced to ``True`` or ``False`` by any function in this
package, and no caller outside this package's own tests may do so either -- that is the single
most important contract property here (a later card, TC-017b, depends on it).

For Python and TypeScript, the per-ecosystem module is a thin wrapper around an existing,
already-independent reader this codebase already has
(``extractors/platforms/python_surface.py``'s ``PublicSurface``,
``extractors/platforms/typescript_barrel.py``'s barrel reader). For C++, Java, Go and .NET, the
module is a new, independent reader built from source text/paths, never from the main engine's
own symbol table. For Rust, the module wraps the vendored engine's own `pub use` reader
(``lang/rust.py``'s ``export_surface``) but never trusts it alone: it also exposes
``confirms_unreachable_for``, a factory that builds the exact ``confirms_unreachable`` callable
``surface_symbols`` already accepts, requiring two independent negative signals (absent from
`pub use` re-exports AND no bare `pub` declaration) before agreeing a name is unreachable.

This package does not wire these probes into the claim-proof pipeline or the obligations
inventory -- that is TC-017b's and TC-018's job. It only builds and tests the probes themselves
as standalone, independently callable functions.
"""

from __future__ import annotations

from repo_presenter.acceptance.probes import (
    cpp,
    dotnet,
    go,
    java,
    python,
    rust,
    typescript,
)

#: Every ecosystem probe module this package ships, keyed by the same ecosystem name the rest of
#: the codebase uses elsewhere (``family``/``language`` strings in the extractor façade).
ECOSYSTEMS: dict[str, object] = {
    "python": python,
    "typescript": typescript,
    "cpp": cpp,
    "java": java,
    "go": go,
    "dotnet": dotnet,
    "rust": rust,
}

__all__ = ["ECOSYSTEMS", "cpp", "dotnet", "go", "java", "python", "rust", "typescript"]
