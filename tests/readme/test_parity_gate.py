"""Parity gate (R2): every dimension, pass and fail, on synthetic fixtures; seal selection; CLI."""

from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from repo_presenter.readme import parity_gate as pg

FENCE = "`" * 3
QUICK = 'var widget = new Widget();\nwidget.Save("out.png");\n'
MARKER = "*From the maintainers' README (not independently verified):*"


def benchmark() -> str:
    return "\n".join(
        [
            "# Foo for .NET",
            "",
            "## Installation",
            "",
            f"{FENCE}bash",
            "dotnet add package Foo.Bar",
            FENCE,
            "",
            "## Quick Start",
            "",
            f"{FENCE}csharp",
            QUICK.rstrip("\n"),
            FENCE,
            "",
            "Call `Widget.Save()` to write a file. Requires version 1.2.3.",
            "",
            "See [the docs](https://docs.example.com/foo) and [LICENSE](LICENSE).",
            "",
            "## Support",
            "",
            "Ask questions on the community forum, where maintainers answer support requests within two business days.",
            "",
        ]
    )


def fact(fid, kind, value, polarity="SUPPORTED", section=None):
    return {
        "id": fid,
        "kind": kind,
        "value": value,
        "polarity": polarity,
        "attributes": {"section": section} if section else None,
        "evidence": [],
        "confidence": 1.0,
    }


def base_facts(example_polarity="SUPPORTED", link_polarity="SUPPORTED"):
    return [
        fact("public_symbol:widget", "public_symbol", "Foo.Widget"),
        fact("public_symbol:save", "public_symbol", "Foo.Widget.Save"),
        fact("example:001", "example", QUICK, example_polarity),
        fact(
            "link_target:001",
            "link_target",
            "https://docs.example.com/foo",
            link_polarity,
        ),
        fact("link_target:002", "link_target", "LICENSE"),
        fact("package:version", "package", "1.2.3"),
        fact("install_command:dotnet", "install_command", "dotnet add package Foo.Bar"),
        fact("inherited_unit:001.heading", "inherited_unit", "# Foo for .NET"),
        fact(
            "inherited_unit:002.code_block",
            "inherited_unit",
            f"{FENCE}bash\ndotnet add package Foo.Bar\n{FENCE}",
            section="Foo for .NET > Installation",
        ),
        fact(
            "inherited_unit:003.code_block",
            "inherited_unit",
            f"{FENCE}csharp\n{QUICK}{FENCE}",
            section="Foo for .NET > Quick Start",
        ),
        fact(
            "inherited_unit:004.paragraph",
            "inherited_unit",
            "Call `Widget.Save()` to write a file. Requires version 1.2.3.",
            section="Foo for .NET > Quick Start",
        ),
        fact(
            "inherited_unit:005.paragraph",
            "inherited_unit",
            "See [the docs](https://docs.example.com/foo) and [LICENSE](LICENSE).",
            section="Foo for .NET > Quick Start",
        ),
        fact(
            "inherited_unit:006.heading",
            "inherited_unit",
            "## Support",
            section="Foo for .NET",
        ),
        fact(
            "inherited_unit:007.paragraph",
            "inherited_unit",
            "Ask questions on the community forum, where maintainers answer support requests within two business days.",
            section="Foo for .NET > Support",
        ),
    ]


def rows(**overrides):
    default = {
        "inherited_unit:001.heading": "SUPERSEDE_REDUNDANT",
        "inherited_unit:002.code_block": "VERIFIED_PRESERVE",
        "inherited_unit:003.code_block": "VERIFIED_PRESERVE",
        "inherited_unit:004.paragraph": "VERIFIED_PRESERVE",
        "inherited_unit:005.paragraph": "VERIFIED_PRESERVE",
        "inherited_unit:006.heading": "SUPERSEDE_REDUNDANT",
        "inherited_unit:007.paragraph": "VERIFIED_PRESERVE",
    }
    out = []
    for unit_id, value in {**default, **overrides}.items():
        disposition, fact_ids, rationale = (
            (value, [], "") if isinstance(value, str) else value
        )
        out.append(
            {
                "unit_id": unit_id,
                "disposition": disposition,
                "fact_ids": fact_ids,
                "rationale": rationale,
            }
        )
    return tuple(out)


def cand(readme=None, lane="R", facts=None, dispositions=None, edits=()):
    return pg.SealedCandidate(
        lane,
        benchmark() if readme is None else readme,
        tuple(base_facts() if facts is None else facts),
        rows() if dispositions is None and lane == "R" else tuple(dispositions or ()),
        tuple(edits),
    )


def dim(result, name):
    return next(d for d in result.dimensions if d.name == name)


def run(candidate, bench=None):
    return pg.evaluate("o/n", candidate, benchmark() if bench is None else bench)


# --- whole-gate baseline -----------------------------------------------------------------------


def test_identical_candidate_reaches_parity_on_every_dimension():
    result = run(cand())
    assert result.parity, pg.render([result])
    assert [d.name for d in result.dimensions] == list(pg.DIMENSIONS)


def test_lane_l_identical_candidate_reaches_parity():
    assert run(cand(lane="L")).parity


# --- 1 section coverage ------------------------------------------------------------------------


def _without_support(text: str) -> str:
    return text.replace("## Support\n\nAsk questions on the community forum, where maintainers answer support requests within two business days.\n", "")


def test_section_missing_without_justification_fails():
    d = dim(run(cand(_without_support(benchmark()))), "section_coverage")
    assert not d.passed and d.numbers["missing"] == 1 and "Support" in d.details[0]


def test_section_missing_justified_by_non_loss_dispositions_passes():
    c = cand(
        _without_support(benchmark()),
        dispositions=rows(**{"inherited_unit:007.paragraph": "NON_CONTENT"}),
    )
    d = dim(run(c), "section_coverage")
    assert d.passed and d.numbers["justified"] == 1


def test_section_renamed_to_a_synonym_counts_as_present():
    d = dim(
        run(cand(benchmark().replace("## Installation", "## Install"))),
        "section_coverage",
    )
    assert d.passed and d.numbers["present"] == 3


# --- 2 technical content -----------------------------------------------------------------------


def test_lost_code_block_fails_technical_content():
    readme = benchmark().replace('widget.Save("out.png");', "")
    d = dim(run(cand(readme)), "technical_content")
    assert not d.passed and d.numbers["code_blocks"]["lost"] == 1


def test_code_block_with_contradicted_example_is_accounted():
    readme = benchmark().replace(f"{FENCE}csharp\n{QUICK}{FENCE}\n", "")
    d = dim(
        run(cand(readme, facts=base_facts(example_polarity="CONTRADICTED"))),
        "technical_content",
    )
    assert d.numbers["code_blocks"] == {
        "benchmark": 1,
        "carried": 0,
        "accounted": 1,
        "lost": 0,
    }


def test_lost_link_fails_and_contradicted_omission_is_accounted():
    readme = benchmark().replace("[the docs](https://docs.example.com/foo)", "the docs")
    lost = dim(run(cand(readme)), "technical_content")
    assert not lost.passed and lost.numbers["links"]["lost"] == 1
    omitted = rows(
        **{
            "inherited_unit:005.paragraph": (
                "OMIT_UNSUPPORTED",
                ["link_target:001"],
                "dead link",
            )
        }
    )
    ok = dim(
        run(
            cand(
                readme,
                facts=base_facts(link_polarity="CONTRADICTED"),
                dispositions=omitted,
            )
        ),
        "technical_content",
    )
    assert ok.numbers["links"]["lost"] == 0


def test_lost_api_identifier_fails():
    readme = benchmark().replace(
        "Call `Widget.Save()` to write a file.", "Write a file."
    )
    readme = readme.replace("widget.Save(", "widget.Write(").replace(
        "new Widget()", "new Thing()"
    )
    d = dim(run(cand(readme)), "technical_content")
    assert not d.passed and d.numbers["api_identifiers"]["lost"] == 1


def test_lost_install_command_fails_and_verified_replacement_is_accounted():
    readme = benchmark().replace(
        "dotnet add package Foo.Bar", "dotnet add package Other"
    )
    assert (
        dim(run(cand(readme)), "technical_content").numbers["install_commands"]["lost"]
        == 1
    )
    facts = [
        f
        if f["id"] != "install_command:dotnet"
        else fact(f["id"], "install_command", "dotnet add package Other")
        for f in base_facts()
    ]
    assert (
        dim(run(cand(readme, facts=facts)), "technical_content").numbers[
            "install_commands"
        ]["accounted"]
        == 1
    )


def test_version_number_lost_fails_unless_updated_to_the_verified_version():
    readme = benchmark().replace("1.2.3", "a recent release")
    assert dim(run(cand(readme)), "technical_content").numbers["versions"]["lost"] == 1
    updated = benchmark().replace("1.2.3", "1.4.0")
    facts = [
        f
        if f["id"] != "package:version"
        else fact("package:version", "package", "1.4.0")
        for f in base_facts()
    ]
    d = dim(run(cand(updated, facts=facts)), "technical_content")
    assert d.numbers["versions"] == {
        "benchmark": 1,
        "carried": 0,
        "accounted": 1,
        "lost": 0,
    }


def test_supersede_redundant_does_not_excuse_a_lost_item():
    readme = benchmark().replace("[the docs](https://docs.example.com/foo)", "the docs")
    c = cand(
        readme,
        dispositions=rows(**{"inherited_unit:005.paragraph": "SUPERSEDE_REDUNDANT"}),
    )
    assert dim(run(c), "technical_content").numbers["links"]["lost"] == 1


# --- 3 verified examples -----------------------------------------------------------------------


def test_candidate_dropping_a_runnable_example_fails():
    readme = benchmark().replace(f"{FENCE}csharp\n{QUICK}{FENCE}\n", "")
    d = dim(run(cand(readme)), "verified_examples")
    assert (
        not d.passed
        and d.numbers["benchmark_runnable"] == 1
        and d.numbers["candidate_verified"] == 0
    )


def test_candidate_printing_a_contradicted_example_fails():
    d = dim(
        run(cand(facts=base_facts(example_polarity="CONTRADICTED"))),
        "verified_examples",
    )
    assert not d.passed and d.numbers["candidate_contradicted"] == 1


def test_verified_example_with_a_prelude_still_counts():
    readme = benchmark().replace(f"{FENCE}csharp\n", f"{FENCE}csharp\nusing Foo;\n\n")
    d = dim(run(cand(readme)), "verified_examples")
    assert d.passed and d.numbers["candidate_verified"] == 1


# --- 4 links ------------------------------------------------------------------------------------


def test_candidate_link_marked_broken_fails():
    d = dim(run(cand(facts=base_facts(link_polarity="CONTRADICTED"))), "links")
    assert not d.passed and d.numbers["contradicted"] == 1


def test_dangling_anchor_fails():
    d = dim(
        run(cand(benchmark() + "\nJump to [nowhere](#no-such-heading).\n")), "links"
    )
    assert not d.passed and d.numbers["dangling_anchors"] == 1


def test_resolving_anchor_passes():
    d = dim(run(cand(benchmark() + "\nBack to [Support](#support).\n")), "links")
    assert d.passed


# --- 5 internal markers ------------------------------------------------------------------------


def test_internal_marker_fails():
    d = dim(run(cand(benchmark() + "\n" + MARKER + "\n")), "internal_markers")
    assert not d.passed and d.numbers["markers"] == 1


# --- 6 maintainer preservation -----------------------------------------------------------------


def test_superseded_unit_not_carried_fails_lane_r():
    c = cand(
        _without_support(benchmark()),
        dispositions=rows(**{"inherited_unit:007.paragraph": "SUPERSEDE_REDUNDANT"}),
    )
    d = dim(run(c), "maintainer_preservation")
    assert not d.passed and d.numbers["superseded_not_carried"] == 1


def test_superseded_unit_carried_passes_lane_r():
    c = cand(
        dispositions=rows(**{"inherited_unit:007.paragraph": "SUPERSEDE_REDUNDANT"})
    )
    d = dim(run(c), "maintainer_preservation")
    assert d.passed and d.numbers["superseded_carried"] == 3


def test_lane_r_without_dispositions_cannot_show_preservation():
    c = pg.SealedCandidate("R", benchmark(), tuple(base_facts()), (), ())
    assert not dim(run(c), "maintainer_preservation").passed


def test_lane_l_line_lost_without_an_edit_fails_and_with_an_evidenced_edit_passes():
    readme = _without_support(benchmark())
    assert not dim(run(cand(readme, lane="L")), "maintainer_preservation").passed
    edit = {
        "detector": "structure",
        "original": "## Support\n\nAsk questions on the community forum, where maintainers answer support requests within two business days.\n",
        "replacement": "",
        "evidence": [{"fact_id": "x", "status": "CONTRADICTED"}],
    }
    d = dim(run(cand(readme, lane="L", edits=[edit])), "maintainer_preservation")
    assert d.passed and d.numbers["missing_lines"] == 2


def test_lane_l_unevidenced_edit_does_not_account():
    readme = _without_support(benchmark())
    edit = {
        "detector": "structure",
        "original": "## Support\n\nAsk questions on the community forum, where maintainers answer support requests within two business days.\n",
    }
    assert not dim(
        run(cand(readme, lane="L", edits=[edit])), "maintainer_preservation"
    ).passed


# --- non-loss rule, not-measured, rendering ----------------------------------------------------


def test_non_loss_rule():
    facts = {"f": {"polarity": "CONTRADICTED"}, "g": {"polarity": "SUPPORTED"}}
    assert pg.disposition_is_non_loss({"disposition": "NON_CONTENT"}, facts)
    assert pg.disposition_is_non_loss(
        {"disposition": "OMIT_UNSUPPORTED", "fact_ids": ["f"]}, facts
    )
    assert pg.disposition_is_non_loss(
        {"disposition": "OMIT_UNSUPPORTED", "rationale": "obsolete API"}, facts
    )
    assert not pg.disposition_is_non_loss(
        {
            "disposition": "OMIT_UNSUPPORTED",
            "fact_ids": ["g"],
            "rationale": "no fact supports it",
        },
        facts,
    )
    for loss in ("SUPERSEDE_REDUNDANT", "DEFER_UNRESOLVED", "VERIFIED_PRESERVE"):
        assert not pg.disposition_is_non_loss({"disposition": loss}, facts)


def test_not_measured_fails_every_dimension():
    result = pg.not_measured("o/n", "R", "NO_CURRENT_SET_SEAL")
    assert not result.parity and not any(d.passed for d in result.dimensions)
    assert "not measured" in pg.render([result])


def test_evaluation_is_deterministic():
    c = cand(_without_support(benchmark()))
    assert json.dumps(run(c).as_dict(), sort_keys=True) == json.dumps(
        run(c).as_dict(), sort_keys=True
    )


def test_load_revision_dir(tmp_path):
    (tmp_path / "README.md").write_text(benchmark(), encoding="utf-8")
    (tmp_path / "facts.json").write_text(
        json.dumps({"facts": base_facts()}), encoding="utf-8"
    )
    (tmp_path / "dispositions.json").write_text(
        json.dumps({"dispositions": list(rows())}), encoding="utf-8"
    )
    loaded = pg.load_revision_dir(tmp_path, "R")
    assert loaded.readme == benchmark() and len(loaded.dispositions) == 7
    assert pg.evaluate("o/n", loaded, benchmark()).parity


# --- seal selection ----------------------------------------------------------------------------


@dataclass
class FakeSeal:
    commit: str
    revision: str
    manifest_state: str
    dependencies: dict | None
    pipeline_good: bool = True
    counted: bool = True


def test_select_seal_current_and_older(tmp_path):
    from repo_presenter.core.version_set import fingerprint

    old = {"components": {"renderer": 1}}
    new = {"components": {"renderer": 2}}
    current = fingerprint(new, "R")
    history = [
        (FakeSeal("c1", "r", "ACCEPTED", old), tmp_path / "1"),
        (FakeSeal("c2", "r", "ACCEPTED", new), tmp_path / "2"),
        (FakeSeal("c3", "r", "INVALIDATED", new, pipeline_good=False), tmp_path / "3"),
        (FakeSeal("c4", "r", "ACCEPTED", old), tmp_path / "4"),
    ]
    assert pg.select_seal(history, "R", current).commit == "c2"
    assert pg.select_seal(history, "R", current, older=True).commit == "c4"
    assert pg.select_seal(history[:1], "R", current) is None


# --- CLI ----------------------------------------------------------------------------------------


def _cli():
    path = pg.REPO_ROOT / "ops" / "checks" / "parity_gate.py"
    spec = importlib.util.spec_from_file_location("parity_gate_cli", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_revision(root: Path, readme: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text(readme, encoding="utf-8")
    (root / "facts.json").write_text(
        json.dumps({"facts": base_facts()}), encoding="utf-8"
    )
    (root / "dispositions.json").write_text(
        json.dumps({"dispositions": list(rows())}), encoding="utf-8"
    )
    return root


def test_cli_offline_exit_codes(tmp_path):
    cli = _cli()
    bench = tmp_path / "bench.md"
    bench.write_text(benchmark(), encoding="utf-8")
    good = _write_revision(tmp_path / "good", benchmark())
    bad = _write_revision(tmp_path / "bad", benchmark() + "\n" + MARKER + "\n")
    out = tmp_path / "out.json"
    assert (
        cli.main(
            [
                "--candidate-dir",
                str(good),
                "--benchmark",
                str(bench),
                "--lane",
                "R",
                "--json",
                str(out),
            ]
        )
        == 0
    )
    document = json.loads(out.read_text(encoding="utf-8"))
    assert document["parity"] and not document["pause_lift_evidence"]
    assert (
        cli.main(
            ["--candidate-dir", str(bad), "--benchmark", str(bench), "--lane", "R"]
        )
        == 1
    )


def test_cli_pilot_set_evidence_and_dry_mode(tmp_path, monkeypatch):
    cli = _cli()
    passing = [run(cand()) for _ in range(6)]
    monkeypatch.setattr(cli, "run_live", lambda repos, lanes, older, remote: passing)
    out = tmp_path / "pilot.json"
    assert cli.main(["--pilot-set", "--json", str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["pause_lift_evidence"] is True
    # an older version set never counts, even at parity
    assert cli.main(["--pilot-set", "--older-set", "--json", str(out)]) == 3
    assert json.loads(out.read_text(encoding="utf-8"))["pause_lift_evidence"] is False
    # one lane short of parity, or one lane unmeasured, blocks the whole set
    monkeypatch.setattr(
        cli,
        "run_live",
        lambda *a: passing[:5] + [pg.not_measured("o/n", "L", "NO_CURRENT_SET_SEAL")],
    )
    assert cli.main(["--pilot-set"]) == 1
    # a repository with no published README does not apply and does not block
    na = pg.not_measured("o/x", "R", "NOT_APPLICABLE: no README.md at the root")
    monkeypatch.setattr(cli, "run_live", lambda *a: passing + [na])
    assert cli.main(["--pilot-set"]) == 0


def test_pilot_set_names_the_three_pause_lift_repositories():
    assert _cli().PILOT_SET == (
        "aspose-cells-foss/Aspose.Cells-FOSS-for-Rust",
        "aspose-email-foss/Aspose.Email-FOSS-for-.Net",
        "aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET",
    )


@pytest.mark.parametrize("name", pg.DIMENSIONS)
def test_every_dimension_is_reported(name):
    assert dim(run(cand()), name).passed


MAINTAINER_DIAGRAM = "```mermaid\nflowchart TD\n  input --> output\n```\n"
OWN_DIAGRAM = "```mermaid\nflowchart TD\n  a[Workbook] --> b[XLSX]\n```\n"


def test_a_maintainer_diagram_is_owed_unless_the_candidate_draws_its_own():
    bench = benchmark() + "\n" + MAINTAINER_DIAGRAM
    without = dim(run(cand(benchmark()), bench=bench), "technical_content")
    assert not without.passed
    with_own = dim(run(cand(benchmark() + "\n" + OWN_DIAGRAM), bench=bench), "technical_content")
    assert with_own.passed
