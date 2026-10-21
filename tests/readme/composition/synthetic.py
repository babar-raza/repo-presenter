"""Shared synthetic fixtures for the Lane R composition pipeline tests."""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.registry.models import ProviderIdentity, RegistryEntry


def make_entry() -> RegistryEntry:
    return RegistryEntry(
        repository="org/Aspose.Widget-FOSS-for-Python",
        family="widget",
        platform="python",
        ecosystem="python",
        mode="full",
        policy_profile="default",
        active=True,
        provider_identity=ProviderIdentity(repository_id=1, node_id="MDEwOlJlcG9zaXRvcnkx"),
    )


def make_facts() -> FactsDocument:
    facts = (
        Fact("identity:repository", "identity", "org/Aspose.Widget-FOSS-for-Python", (Evidence("data/registry.json"),)),
        Fact("identity:ecosystem", "identity", "python", (Evidence("data/registry.json"),)),
        Fact("package:name", "package", "aspose-widget-foss", (Evidence("setup.py"),)),
        Fact(
            "install_command:pip",
            "install_command",
            "pip install aspose-widget-foss",
            (Evidence("README.md"),),
            attributes={"install_kind": "registry"},
        ),
        Fact("license:spdx", "license", "MIT", (Evidence("LICENSE"),)),
        Fact("license:file", "license", "LICENSE", (Evidence("LICENSE"),)),
        Fact(
            "example:001",
            "example",
            "import aspose_widget_foss\nw = aspose_widget_foss.Widget()\nw.render()\n",
            (Evidence("README.md", "unit inherited_unit:005.code_block"),),
        ),
        Fact(
            "public_symbol:aspose_widget_foss.widget",
            "public_symbol",
            "aspose_widget_foss.Widget",
            (Evidence("aspose_widget_foss/widget.py", "; class; "),),
            attributes={"symbol_kind": "class", "docstring": "A widget you can render."},
        ),
        Fact(
            "inherited_unit:005.code_block",
            "inherited_unit",
            "```python\nimport aspose_widget_foss\n```",
            (Evidence("README.md", "section 'Aspose Widget > Usage'"),),
            attributes={"section": "Aspose Widget > Usage"},
        ),
        Fact(
            "inherited_unit:010.paragraph",
            "inherited_unit",
            "Only PNG output is currently supported.",
            (Evidence("README.md", "section 'Aspose Widget > Limitations'"),),
            attributes={"section": "Aspose Widget > Limitations"},
        ),
    )
    return FactsDocument("org/Aspose.Widget-FOSS-for-Python", "f" * 40, facts)
