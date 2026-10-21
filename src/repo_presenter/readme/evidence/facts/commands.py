"""Build/test/release command fact IDs and the pure text-level command comparisons.

Ported (TRIMMED, ADAPT) from the old repository-presenter project's ``components/readme/
evidence/facts/commands.py`` per migration/reuse-manifest.yaml ("readme/composition/" entry).
Only the fact-ID constants and the pure, text-only parsers composition's ``renderer.py`` and
``reconciliation/dispositions.py`` read are ported: ``CommandForm``/``command_form``/
``commands_in_text`` (reduce a shell command line to its program/verbs/targets so two spellings of
"the same command" compare equal) and ``matrix_axes`` (read a ``ci-matrix`` fact's own
``axis=value,value;axis=value`` value back into pairs).

The rest of the old module -- ``command_facts``, ``ci_matrix_fact``, ``release_workflow_fact``,
``ci_jobs``, and every workflow/Makefile/package.json-scanning helper beneath them -- is
extraction-time apparatus (it reads a cloned repository's own tree to FIRST produce these facts);
that belongs with the separate, PENDING_REVIEW extraction pull in migration/reuse-manifest.yaml.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from repo_presenter.core.facts import Fact, fact_id

BUILD_COMMAND_FACT_ID = fact_id("build_test_asset", "build-command")
TEST_COMMAND_FACT_ID = fact_id("build_test_asset", "test-command")
CI_MATRIX_FACT_ID = fact_id("build_test_asset", "ci-matrix")
RELEASE_WORKFLOW_FACT_ID = fact_id("build_test_asset", "release-workflow")
# The attribute a command fact carries when a reader must run something first: newline-joined.
PRECONDITION_ATTRIBUTE = "precondition"


def matrix_axes(fact: Fact) -> list[tuple[str, list[str]]]:
    """The ``(axis, values)`` pairs of a ``ci-matrix`` fact's value, in order."""
    pairs: list[tuple[str, list[str]]] = []
    for part in fact.value.split(";"):
        key, _, values = part.partition("=")
        if key and values:
            pairs.append((key, values.split(",")))
    return pairs


# --- Equivalent commands ---------------------------------------------------------------------
# Whether a command a README already shows makes another redundant: the same program, the same
# subcommand words and the same target, however the line is spelled (whitespace, a prompt, a
# ``python -m`` or ``uv run`` wrapper, ``npm run test`` for ``npm test``, flags, an extra goal as
# in ``mvn clean package`` for ``mvn package``).
_PROMPT = re.compile(r"^\s*(?:[$>]\s*)?")
_ENV_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=\S*")
_WRAPPERS = (
    ("sudo",),
    ("time",),
    ("uv", "run"),
    ("poetry", "run"),
    ("pipenv", "run"),
    ("hatch", "run"),
    ("pdm", "run"),
    ("npx",),
    ("bundle", "exec"),
    ("python", "-m"),
    ("python3", "-m"),
    ("py", "-m"),
)
_PROGRAM_FAMILY = {"yarn": "npm", "pnpm": "npm", "bun": "npm", "mvnw": "mvn", "gradlew": "gradle"}
_PROJECT_FILE = re.compile(r"(?i)\.(?:sln|slnx|csproj|fsproj|vbproj|vcxproj)$")
_PATH_LIKE = re.compile(r"[/\\]|^\.+$|\.\w{1,6}$")
_MODE_FLAGS = frozenset({"--build", "--install", "--preset", "--workflow"})
_DIRECTORY_FLAGS = {
    "cmake": frozenset({"-B", "--build"}),
    "ctest": frozenset({"--test-dir"}),
    "make": frozenset({"-C"}),
}
_VALUE_FLAGS = {
    "cmake": frozenset({"-S", "-C", "-j", "--config", "--target", "--parallel"}),
    "ctest": frozenset({"-C", "-j", "-R", "-E", "--build-config", "--parallel"}),
    "dotnet": frozenset({"-c", "-f", "--configuration", "--framework", "--logger"}),
    "pytest": frozenset({"-n", "-p"}),
    "mvn": frozenset({"-pl", "-f", "-T", "-P"}),
    "make": frozenset({"-j"}),
}
_COMMAND_SPLIT = re.compile(r"\s*(?:&&|\|\||[;|])\s*")
_INLINE_CODE = re.compile(r"`+([^`\n]+)`+")
_FENCE = re.compile(r"(`{3,}|~{3,})")


@dataclass(frozen=True)
class CommandForm:
    """A command reduced to what makes it the same command: its program, its subcommand words and
    the targets it names."""

    program: str
    verbs: frozenset[str]
    targets: frozenset[str]

    def covers(self, other: CommandForm) -> bool:
        """Whether running this command already does what ``other`` does."""
        return (
            self.program == other.program
            and other.verbs <= self.verbs
            and (bool(other.verbs) or not self.verbs)
            and (not other.targets or other.targets <= self.targets)
        )


def command_form(text: str) -> CommandForm | None:
    """The ``CommandForm`` of one command line, or ``None`` for a line that is not one."""
    tokens = _PROMPT.sub("", text.split(" #", 1)[0]).split()
    if not tokens or tokens[0].startswith("#"):
        return None
    while tokens and _ENV_ASSIGNMENT.fullmatch(tokens[0]):
        tokens.pop(0)
    stripped = True
    while stripped and tokens:
        stripped = False
        for wrapper in _WRAPPERS:
            if len(tokens) > len(wrapper) and tuple(tokens[: len(wrapper)]) == wrapper:
                tokens, stripped = tokens[len(wrapper) :], True
    if not tokens:
        return None
    name = tokens[0].removeprefix("./").removeprefix(".\\").lower()
    name = re.sub(r"\.(?:cmd|bat|exe|sh)$", "", name)
    program = _PROGRAM_FAMILY.get(name, name)
    verbs: set[str] = set()
    targets: set[str] = set()
    directory_flags = _DIRECTORY_FLAGS.get(program, frozenset())
    value_flags = _VALUE_FLAGS.get(program, frozenset())
    pending = ""
    for token in tokens[1:]:
        if pending:
            if pending in directory_flags:
                targets.add(token.rstrip("/\\"))
            pending = ""
        elif token.startswith("-"):
            flag, equals, value = token.partition("=")
            if flag in _MODE_FLAGS:
                verbs.add(flag)
            if equals:
                if flag in directory_flags:
                    targets.add(value.rstrip("/\\"))
            elif flag in directory_flags or flag in value_flags:
                pending = flag
        elif (program == "npm" and token == "run") or (
            program in {"dotnet", "msbuild"} and _PROJECT_FILE.search(token)
        ):
            continue
        elif _PATH_LIKE.search(token):
            targets.add(token.rstrip("/\\"))
        else:
            verbs.add(token.lower())
    return CommandForm(program, frozenset(verbs), frozenset(targets))


def commands_in_text(text: str) -> list[CommandForm]:
    """Every command a README text shows: each line of a code fence or of an indented or prompted
    block, and each inline code span, split at ``&&``, ``;`` and pipes."""
    forms: list[CommandForm] = []
    fence = ""
    for raw in text.splitlines():
        marker = _FENCE.match(raw.strip())
        if marker is not None and (not fence or marker.group(1)[0] == fence):
            fence = "" if fence else marker.group(1)[0]
            continue
        if fence or raw.startswith(("    ", "\t")) or raw.lstrip().startswith(("$ ", "> ")):
            sources = [raw]
        else:
            sources = _INLINE_CODE.findall(raw)
        for source in sources:
            for part in _COMMAND_SPLIT.split(source):
                form = command_form(part)
                if form is not None:
                    forms.append(form)
    return forms
