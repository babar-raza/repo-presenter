"""The Java plugin supplies what is Java's own and leaves the rest to the shared facades.

Ported (REUSE for manifest/registry/javadoc-prose coverage) from the old repository-presenter
project's ``tests/components/readme/extractors/platforms/test_java.py`` per
migration/reuse-manifest.yaml.

Tests deliberately NOT ported, matching the trims documented in ``extractors/platforms/java.py``'s
own docstring:
- Every ``java_examples``-backed test (``compilation_unit``, ``public_types``,
  ``unbound_variables``, ``_release_flags``, the javac-verification tests): ``java_examples.py``
  (the toolchain-backed example compiler) was not ported this pass.
- ``test_the_surface_is_read_from_the_main_tree_and_excludes_internal_packages``: needs the
  unported tree-sitter surface engine; this plugin's ``surface_facts`` always returns ``[]``.
- The ``extract_links`` cross-check inside the old javadoc-prose test (a different, unported
  module, ``readme/evidence/facts/links.py``); the ``_javadoc_prose`` assertions themselves are
  kept, since that function *was* ported (kept ready for when the surface engine lands, per
  ``java.py``'s own docstring).
- ``test_the_plugin_imports_no_sibling_ecosystem`` is replaced by a version matching this
  plugin's real (smaller) import set.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from repo_presenter.extractors.platforms import java
from repo_presenter.extractors.platforms.registry import known_ecosystems, plugin_for
from repo_presenter.core.ecosystems import spec_for
from repo_presenter.core.facts import Fact

POM = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>org.aspose</groupId>
    <artifactId>aspose-widget</artifactId>
    <version>26.5.0</version>
    <packaging>jar</packaging>
    <properties>
        <maven.compiler.target>21</maven.compiler.target>
        <junit.version>5.10.0</junit.version>
    </properties>
    <dependencies>
        <dependency>
            <groupId>org.junit.jupiter</groupId>
            <artifactId>junit-jupiter</artifactId>
            <version>${junit.version}</version>
            <scope>test</scope>
        </dependency>
    </dependencies>
</project>
"""
WIDGET = """package org.aspose.widget;

/** A widget. */
public class Widget {
    public String getName() { return "widget"; }
    public void save(String path) { }
}
"""
INTERNAL = """package org.aspose.widget.internal;

public class Buffer {
    public void flush() { }
}
"""


def _repository(root: Path, pom: str = POM) -> list[str]:
    (root / "pom.xml").write_text(pom, encoding="utf-8", newline="\n")
    source = root / "src" / "main" / "java" / "org" / "aspose" / "widget"
    (source / "internal").mkdir(parents=True)
    (source / "Widget.java").write_text(WIDGET, encoding="utf-8", newline="\n")
    (source / "internal" / "Buffer.java").write_text(INTERNAL, encoding="utf-8", newline="\n")
    tests = root / "src" / "test" / "java" / "org" / "aspose" / "widget"
    tests.mkdir(parents=True)
    (tests / "WidgetTest.java").write_text(
        WIDGET.replace("class Widget", "class WidgetTest"), encoding="utf-8", newline="\n"
    )
    return [
        "pom.xml",
        "src/main/java/org/aspose/widget/Widget.java",
        "src/main/java/org/aspose/widget/internal/Buffer.java",
        "src/test/java/org/aspose/widget/WidgetTest.java",
    ]


def test_the_plugin_and_its_spec_are_registered_by_the_module_alone() -> None:
    """Adding an ecosystem is a spec, a verifier and a negative control."""
    assert plugin_for("java") is java.PLUGIN
    assert "java" in known_ecosystems()
    assert spec_for("java") is java.JAVA
    assert java.JAVA.example_fences == frozenset({"java"})
    assert java.JAVA.registry == "Maven Central"


def test_the_governing_pom_is_the_module_that_packages_the_artifact(tmp_path: Path) -> None:
    """An aggregator publishes nothing and sits where depth always prefers it."""
    (tmp_path / "pom.xml").write_text(
        POM.replace("<packaging>jar</packaging>", "<packaging>pom</packaging>"),
        encoding="utf-8",
        newline="\n",
    )
    module = tmp_path / "library"
    module.mkdir()
    _repository(module)
    sample = tmp_path / "samples"
    sample.mkdir()
    _repository(sample)

    manifest = java.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    assert manifest.relative_to(tmp_path).as_posix() == "library/pom.xml"


def test_build_output_never_governs_and_a_broken_pom_still_ranks(tmp_path: Path) -> None:
    """`target/` holds a copy of the POM at every build; a malformed POM claims nothing."""
    _repository(tmp_path)
    copied = tmp_path / "target" / "classes"
    copied.mkdir(parents=True)
    (copied / "pom.xml").write_text(POM, encoding="utf-8", newline="\n")
    assert java.PLUGIN.detect_manifest(tmp_path) == tmp_path / "pom.xml"

    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "pom.xml").write_text("<project", encoding="utf-8", newline="\n")
    assert java._read_pom(broken / "pom.xml") is None
    assert java.PLUGIN.detect_manifest(broken) == broken / "pom.xml"


def test_manifest_facts_carry_the_coordinate_version_floor_and_install_command(
    tmp_path: Path,
) -> None:
    tree = _repository(tmp_path)
    manifest = java.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = {fact.id: fact for fact in java.PLUGIN.manifest_facts(tmp_path, manifest, tree)}

    assert facts["package:name"].value == "org.aspose:aspose-widget"
    assert facts["package:version"].value == "26.5.0"
    floor = facts["package:java_release"]
    assert floor.value == "21"
    assert floor.evidence[0].detail == "`maven.compiler.target` declared by the POM"
    assert spec_for("java").floor_declaration == "maven.compiler"
    install = facts["install_command:maven"]
    assert install.value == "mvn dependency:get -Dartifact=org.aspose:aspose-widget:26.5.0"
    assert install.polarity == "UNRESOLVED" and install.confidence == 0.5


def test_the_floor_prefers_release_over_target_and_source(tmp_path: Path) -> None:
    """`release` also restricts the JDK API the code may call, so it outranks the other two."""
    _repository(
        tmp_path,
        POM.replace(
            "<maven.compiler.target>21</maven.compiler.target>",
            "<maven.compiler.release>17</maven.compiler.release>\n"
            "        <maven.compiler.target>21</maven.compiler.target>",
        ),
    )
    manifest = java.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = {fact.id: fact for fact in java.PLUGIN.manifest_facts(tmp_path, manifest, [])}
    floor = facts["package:java_release"]
    assert floor.value == "17"
    assert floor.evidence[0].detail == "`maven.compiler.release` declared by the POM"


def test_a_test_scoped_dependency_is_development_and_leaves_a_verified_zero(
    tmp_path: Path,
) -> None:
    """Every declared dependency of this cohort is `test` scope."""
    tree = _repository(tmp_path)
    manifest = java.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = {fact.id: fact for fact in java.PLUGIN.manifest_facts(tmp_path, manifest, tree)}

    development = facts["dependency:development.org.junit.jupiter-junit-jupiter"]
    assert development.value == "org.junit.jupiter:junit-jupiter 5.10.0"
    assert "<scope>test</scope>" in (development.evidence[0].detail or "")
    marker = facts["dependency:none"]
    assert marker.value == "none" and marker.polarity == "SUPPORTED"
    assert marker.evidence[0].path == "pom.xml"


def test_a_compile_scoped_dependency_is_required_and_an_optional_one_is_not(
    tmp_path: Path,
) -> None:
    """A consumer installs what Maven resolves; `<optional>` is declared but never inherited."""
    _repository(
        tmp_path,
        POM.replace(
            "    </dependencies>",
            """        <dependency>
            <groupId>org.apache.poi</groupId>
            <artifactId>poi-ooxml</artifactId>
            <version>5.3.0</version>
        </dependency>
        <dependency>
            <groupId>org.slf4j</groupId>
            <artifactId>slf4j-api</artifactId>
            <version>2.0.13</version>
            <optional>true</optional>
        </dependency>
    </dependencies>""",
        ),
    )
    manifest = java.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = {fact.id: fact for fact in java.PLUGIN.manifest_facts(tmp_path, manifest, [])}
    assert facts["dependency:org.apache.poi-poi-ooxml"].value == "org.apache.poi:poi-ooxml 5.3.0"
    assert facts["dependency:optional.org.slf4j-slf4j-api"].value == "org.slf4j:slf4j-api 2.0.13"
    assert "dependency:none" not in facts


def test_an_unreadable_registry_leaves_the_install_claim_unresolved(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """Silence is not absence: a probe that cannot read must not contradict the claim."""
    tree = _repository(tmp_path)
    manifest = java.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = java.PLUGIN.manifest_facts(tmp_path, manifest, tree)

    def unreadable(*args: Any, **kwargs: Any) -> Any:
        from repo_presenter.extractors.surface.registry import RegistryObservation

        return RegistryObservation("maven", "org.aspose:aspose-widget", False, True, None, None, "")

    monkeypatch.setattr(java, "observe", unreadable)
    resolved, probes = java.PLUGIN.registry_facts(facts)
    assert [fact.polarity for fact in resolved] == ["UNRESOLVED"]
    # Not the facade's "answered ambiguously": the shared probe takes a name, and Maven Central's
    # metadata is addressed by group and artifact id, so no read happened at all.
    assert "was not read" in (resolved[0].evidence[-1].detail or "")
    assert probes and probes[0].outcome == "UNRESOLVED"


def test_a_missing_verifier_reports_not_verified_rather_than_failure(tmp_path: Path) -> None:
    """A check this plugin cannot run is UNRESOLVED (NOT_VERIFIED), never CONTRADICTED."""
    from repo_presenter.core.examples import ExampleCandidate

    candidates = [ExampleCandidate(1, "java", "new Widget();", "README.md", 1, 3, "unit:001")]
    receipts = java.PLUGIN.verify_examples(tmp_path, [], candidates, tmp_path / "run")
    assert [receipt.outcome for receipt in receipts] == ["NOT_VERIFIED"]


def test_the_plugin_imports_only_core_and_the_shared_surface_facades(tmp_path: Path) -> None:
    """This pull's java.py imports only core/, the shared surface facades, and stdlib - no
    sibling platform module, and (unlike the old repo) no tree-sitter grammars or execution
    toolchain, since surface_facts/verify_examples were deliberately not ported this pass."""
    import ast

    source = Path(java.__file__).read_text("utf-8")
    imported = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not any(".platforms." in name and not name.endswith(".java") for name in imported)
    assert all(
        name.startswith(
            (
                "repo_presenter.core",
                "repo_presenter.extractors.surface",
                "collections",
                "pathlib",
                "typing",
                "__future__",
                "xml.etree",
            )
        )
        for name in imported
    ), sorted(imported)


def test_a_published_install_fact_shows_both_readings_bc02_asks_for(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """A validator reading the install fact's own evidence must find both a manifest reading and
    a registry one - this plugin names the file "manifest" (not its ecosystem nickname), the word
    every other ecosystem's plugin also uses, so this test pins that predicate rather than the
    exact sentence."""
    tree = _repository(tmp_path)
    manifest = java.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = java.PLUGIN.manifest_facts(tmp_path, manifest, tree)

    def published(*args: Any, **kwargs: Any) -> Any:
        from repo_presenter.extractors.surface.registry import RegistryObservation

        return RegistryObservation(
            "maven",
            "org.aspose:aspose-widget",
            True,
            False,
            "https://repo1.maven.org/maven2/org/aspose/aspose-widget/maven-metadata.xml",
            "maven-metadata",
            "live",
            repository_matched=True,
        )

    monkeypatch.setattr(java, "observe", published)
    resolved, _ = java.PLUGIN.registry_facts(facts)
    install = resolved[0]
    assert install.polarity == "SUPPORTED"
    details = " ".join(evidence.detail or "" for evidence in install.evidence)
    assert "manifest" in details and "package registry" in details


def test_the_floor_fact_names_this_poms_own_property_not_the_family(tmp_path: Path) -> None:
    """The spec keeps `maven.compiler` because a POM may declare the floor as `release`,
    `target` or `source` and this cohort uses all three; the fact carries the one this POM
    declares."""
    _repository(tmp_path)
    manifest = java.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = {fact.id: fact for fact in java.PLUGIN.manifest_facts(tmp_path, manifest, [])}
    floor = facts["package:java_release"]
    assert (floor.attributes or {})["floor_declaration"] == "maven.compiler.target"
    assert spec_for("java").floor_declaration == "maven.compiler"


def test_a_javadoc_comment_becomes_prose_and_never_a_markdown_autolink() -> None:
    """Javadoc is not Markdown, and the API Reference cell is prose with its backticks stripped."""
    assert java._javadoc_prose("The {@code <xfa:datasets>} packet wrapper.") == (
        "The xfa:datasets packet wrapper."
    )
    assert java._javadoc_prose("Collection of {@link Artifact} objects.") == (
        "Collection of Artifact objects."
    )
    assert java._javadoc_prose("Options for {@link Document#compactFlow(Options)}.") == (
        "Options for Document.compactFlow(Options)."
    )
    assert java._javadoc_prose("Set via {@link #setTarget(BaseParagraph)}.") == (
        "Set via setTarget(BaseParagraph)."
    )
    # Presentation markup goes; an element name that merely looks like a tag stays.
    assert java._javadoc_prose("Re-flows the text <b>and images</b> of a PDF.") == (
        "Re-flows the text and images of a PDF."
    )
    assert java._javadoc_prose("The <pageSet> element.") == "The pageSet element."
    assert java._javadoc_prose("Named &quot;Collections&quot;.") == 'Named "Collections".'
    assert java._javadoc_prose("{@inheritDoc}") == ""
    assert java._javadoc_prose("A plain sentence.") == "A plain sentence."
    # A product's own types may document themselves in braces all the way down, and some
    # callers keep only a docstring's first line - so a tag can also arrive already cut, with
    # its closing brace on a line that was never handed over.
    assert java._javadoc_prose("{@code try { } catch (p) { } finally { }}") == (
        "try { } catch (p) { } finally { }"
    )
    assert java._javadoc_prose("{@code {...") == "{..."


def test_every_fact_the_plugin_emits_is_typed_as_a_fact(tmp_path: Path) -> None:
    tree = _repository(tmp_path)
    manifest = java.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    for fact in [
        *java.PLUGIN.manifest_facts(tmp_path, manifest, tree),
        *java.PLUGIN.surface_facts(tmp_path, tree),
    ]:
        assert isinstance(fact, Fact)


# Identity read by first-match regex took the <parent> block's coordinates. Trimmed real POMs:
# spring-projects/spring-petclinic (parent first, own groupId and version) and
# apache/commons-lang (groupId inherited from the parent).
_POM_FIXTURES = Path(__file__).parent / "fixtures"


def _facts_of(tmp_path: Path, pom: str) -> dict[str, Fact]:
    (tmp_path / "pom.xml").write_text(pom, encoding="utf-8", newline="\n")
    manifest = java.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    return {fact.id: fact for fact in java.PLUGIN.manifest_facts(tmp_path, manifest, [])}


def test_the_project_identity_is_the_projects_own_not_its_parents(tmp_path: Path) -> None:
    facts = _facts_of(tmp_path, (_POM_FIXTURES / "petclinic" / "pom.xml").read_text("utf-8"))
    assert facts["package:name"].value == "org.springframework.samples:spring-petclinic"
    assert facts["package:version"].value == "4.0.0-SNAPSHOT"
    assert facts["install_command:maven"].value == (
        "mvn dependency:get -Dartifact=org.springframework.samples:spring-petclinic:4.0.0-SNAPSHOT"
    )


def test_an_absent_group_id_is_inherited_from_the_parent(tmp_path: Path) -> None:
    facts = _facts_of(tmp_path, (_POM_FIXTURES / "commons_lang" / "pom.xml").read_text("utf-8"))
    assert facts["package:name"].value == "org.apache.commons:commons-lang3"
    assert facts["package:version"].value == "3.21.1-SNAPSHOT"


def test_an_absent_version_is_inherited_from_the_parent(tmp_path: Path) -> None:
    pom = (_POM_FIXTURES / "commons_lang" / "pom.xml").read_text("utf-8")
    facts = _facts_of(tmp_path, pom.replace("<version>3.21.1-SNAPSHOT</version>", ""))
    assert facts["package:version"].value == "105"


def test_a_parent_only_pom_declares_no_identity_of_its_own(tmp_path: Path) -> None:
    pom = (_POM_FIXTURES / "commons_lang" / "pom.xml").read_text("utf-8")
    facts = _facts_of(tmp_path, pom.replace("<artifactId>commons-lang3</artifactId>", ""))
    assert "package:name" not in facts
    assert "install_command:maven" not in facts
