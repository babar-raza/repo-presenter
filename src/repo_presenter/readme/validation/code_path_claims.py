"""BC-14 rule (j), extended: behaviour claimed beyond the real code path (K02) and dependency
claims beyond the published package (K06).

``docs/investigations/2026-11-13-lane-r-false-claim-review.md``: 29 registered false claims (K02)
described a behaviour the code path does not have, and 6 (K06) described dependencies the
published package does not have. Rule (j) (``surface_claims._stub_findings``) read stubs only from
the maintainers' limitation statements, so a stub the source states (an ``implementation`` fact)
and every inverse shape went unjudged. Each rule here holds a sentence to a SUPPORTED fact that
positively contradicts it, and is silent without one:

(j1) Stated stubs. A member whose own body only raises ``NotImplemented*`` (its ``implementation``
     fact) is a stub exactly as a limitation statement makes it one; ``stub_members`` feeds those
     to rule (j)'s subject matching.
(j2) Never-thrown exceptions. "throws `X`" / "raising `X`", or a row or bullet whose subject is
     `X` and which says when it is raised, for an exception type no library code throws or
     constructs (``implementation`` aspect ``never_thrown``; Cells C++ ``FormulaException``, 3D
     Python ``TrialException``).
(j3) Stubs through a static instance. A static field constructed as a type whose member only
     throws (``implementation`` dispatch ``static_instance``; 3D .NET ``FileFormat.WavefrontOBJ``)
     described as usable with a load/save call.
(j4) Throws claimed, none in the body. "`X` ... throw(s) `NotImplementedException`" where every
     method of `X` (or the member `X.M`) was read and holds no throw at all (3D .NET
     ``NurbsSurface.ToMesh`` returns a placeholder grid; ``RenderFactory``'s methods return null).
(j5) Unreachable formats. A sentence that exports/saves/writes (or reads/loads/opens) a format whose
     fact for that direction is reachable only through a stub (``format`` attribute
     ``code_path: stub``; 3D Python ``.dae`` export behind ``FbxExporter.supports_format``).
(j6) "No dependencies" (K06). A sentence saying the package has no (third-party) dependencies while
     a ``dependency`` fact names one a consumer installs (Words .NET's nuspec declares three).
(j7) Samples and the package (K06). A sentence saying the sample/example projects use the package
     (at a version) while every sample project references the product project instead
     (``project_file:samples.product_reference``; Cells .NET, 15 ``ProjectReference`` samples).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable

from repo_presenter.core.facts import Fact, FactsDocument
from repo_presenter.readme.validation.claims import ClaimFinding

Sentence = tuple[str, int, int]
Make = Callable[[int, str, str, int], ClaimFinding]

_CODE_SPAN = re.compile(r"`([^`\n]+)`")
_STUB_EXCEPTION = re.compile(r"^(?:NotImplemented\w*|unimplemented!|todo!)$")
_LIMITATION = re.compile(
    r"(?i)\bnot\b|\bno\b|\bcannot\b|\bcan't\b|\bnever\b|\bunimplemented\b|\bunsupported\b|\bstub\b"
    r"|\bplaceholder\b|\bout\s+of\s+scope\b|\bunavailable\b|\bdeclared\s+only\b|\bunused\b"
)


def _supported(facts: FactsDocument, kind: str) -> list[Fact]:
    return [fact for fact in facts.by_kind(kind) if fact.polarity == "SUPPORTED"]  # type: ignore[arg-type]


def _last(name: str) -> str:
    return re.split(r"\.|::", name.strip().rstrip("()"))[-1]


# --- (j1) stubs the source states --------------------------------------------------------------


_BASES = re.compile(r"(?:\bclass\s+\w+\s*\((?P<py>[^)]*)\)|\bclass\s+\w+(?:<[^>]*>)?\s*:\s*(?P<cs>[^{]+)|\bextends\s+(?P<java>[\w.]+))")


def _subclasses(facts: FactsDocument) -> dict[str, set[str]]:
    """``{type: {direct subclass}}`` among the public types, by simple name, read from each
    type's signature or declaration (``class ObjExporter(Exporter)``, ``class A : B``)."""
    found: dict[str, set[str]] = {}
    for fact in _supported(facts, "public_symbol"):
        attributes = fact.attributes or {}
        if attributes.get("symbol_kind") not in ("class", "unknown"):
            continue
        text = attributes.get("signature") or attributes.get("declaration") or ""
        match = _BASES.search(text)
        if match is None:
            continue
        bases = match.group("py") or match.group("cs") or match.group("java") or ""
        for base in re.findall(r"[A-Za-z_][\w.]*", bases):
            found.setdefault(_last(base), set()).add(_last(fact.value))
    return found


def stub_members(facts: FactsDocument) -> dict[str, dict[str, str]]:
    """``{type: {member: fact id}}`` for every public member whose own body only raises a
    not-implemented exception, keyed by the simple names a README spells. A base type's member
    that some subclass implements (a public ``Sub.member`` with no throw) is the abstract-method
    idiom (``Exporter.supports_format``), not a stub, and is left out."""
    throws: set[tuple[str, str]] = set()
    members: dict[str, dict[str, str]] = {}
    for fact in _supported(facts, "implementation"):
        attributes = fact.attributes or {}
        owner, _, member = attributes.get("member", "").rpartition(".")
        if attributes.get("aspect") == "throws" and owner:
            throws.add((_last(owner), member))
        if (
            attributes.get("aspect") != "throws"
            or attributes.get("condition") != "always"
            or attributes.get("visibility")
            or attributes.get("accessor")
            or attributes.get("dispatch")
            or not _STUB_EXCEPTION.match(attributes.get("exception", ""))
        ):
            continue
        if owner and member and not member.startswith("_"):
            members.setdefault(_last(owner), {}).setdefault(member, fact.id)
    if not members:
        return {}
    defined = {
        (_last(fact.value.rpartition(".")[0]), fact.value.rpartition(".")[2])
        for fact in _supported(facts, "public_symbol")
        if "." in fact.value
    }
    subclasses = _subclasses(facts)

    def implemented_below(owner: str, member: str, seen: frozenset[str] = frozenset()) -> bool:
        for sub in subclasses.get(owner, ()):
            if sub in seen:
                continue
            if (sub, member) in defined and (sub, member) not in throws:
                return True
            if implemented_below(sub, member, seen | {owner}):
                return True
        return False

    return {
        owner: kept
        for owner, stubbed in members.items()
        if (kept := {m: f for m, f in stubbed.items() if not implemented_below(owner, m)})
    }


_OFFERS = re.compile(
    r"(?i)\b(?:lets?\s+you|allows?\s+you|enables?\s+you|you\s+can|can|supports?|supporting"
    r"|provides?|offers?|exposes?|manages?)\b"
)


# An interface or base type describes a contract its implementers fulfil, not a working stub.
_CONTRACT = re.compile(r"(?i)\b(?:interface|implement\w*|abstract|base\s+(?:class|type))\b")
_FACTORY_WORDS = frozenset({"from", "to", "as", "with", "by", "for", "on"})


def _stated_stub_findings(sentences: Iterable[Sentence], facts: FactsDocument, make: Make) -> list[ClaimFinding]:
    """(j1): a row or bullet whose subject is a type and which offers (``lets you``, ``can``,
    ``provides`` ...) what one of its stub members would do (the member's stem as a verb)."""
    from repo_presenter.readme.validation.surface_claims import (
        _LIMITATION_CUE,
        _SUBJECT,
        _member_stem,
        _verb_form,
    )

    stubs = stub_members(facts)
    if not stubs:
        return []
    findings: list[ClaimFinding] = []
    for sentence, first, last in sentences:
        if _LIMITATION_CUE.search(sentence.replace("`", " ")):
            continue
        subject = _SUBJECT.match(sentence)
        if subject is None:
            continue
        owner = _last(subject.group("name").strip().split(".", 1)[0])
        description = _CODE_SPAN.sub(" ", sentence[subject.end() :])
        offer = _OFFERS.search(description)
        if offer is None or owner not in stubs or _CONTRACT.search(description):
            continue
        offered = description[offer.end() :]
        for member, fact_id in sorted(stubs[owner].items()):
            if member.split("_", 1)[0].lower() in _FACTORY_WORDS or re.match(r"(?:From|To|As)[A-Z]", member):
                continue  # ``from_geometry``: a factory named for its input, not a capability verb
            stem = _member_stem(member)
            if stem and _verb_form(stem).search(offered):
                findings.append(
                    make(
                        first,
                        sentence,
                        f"the README describes `{owner}` as offering what `{owner}.{member}` would "
                        f"do, but {fact_id} states that member only raises a not-implemented "
                        "exception (a stub): describe it as not implemented or omit it",
                        last,
                    )
                )
                break
    return findings


# --- (j2) never-thrown exceptions --------------------------------------------------------------

_THROW_VERB = re.compile(r"(?i)\b(?:throws?|throwing|thrown|raises?|raising|raised)\s+(?:an?\s+|the\s+)?$")
_WHEN_RAISED = re.compile(
    r"(?i)\b(?:raised|thrown|throws?|raises|when|whenever|if|invalid|fails?|failure|on\s+error)\b"
)
_LEADING_SPANS = re.compile(
    r"^\s*(?:[-*+]\s+|\|\s*)?(?:\*\*)?(?P<spans>`[^`\n]+`(?:\s*(?:/|,|and|or)\s*`[^`\n]+`)*)(?:\*\*)?"
)


# The row itself says the type is not thrown ("never raised", "not applicable", "unused").
_NOT_THROWN = re.compile(
    r"(?i)\b(?:never|not)\s+(?:be\s+)?(?:thrown|raised|used)\b|\bdeclared\s+only\b|\bunused\b"
    r"|\bnot\s+applicable\b|\bno\s+longer\b"
)


def _never_thrown(facts: FactsDocument) -> dict[str, str]:
    found: dict[str, str] = {}
    for fact in _supported(facts, "implementation"):
        attributes = fact.attributes or {}
        if attributes.get("aspect") == "never_thrown":
            found[_last(attributes.get("member", fact.value))] = fact.id
    return found


#: What the renderer prints for a never-thrown exception type's row in place of a docstring that
#: says when it is thrown (BL-079 decision, docs/DECISION_LOG.md 2026-11-13): fact-true, and
#: matched by ``_NOT_THROWN`` so rule (j2) reads it as the disclaimer it is.
NOT_THROWN_DESCRIPTION = "Declared; not thrown by library code."


def refuted_thrown_description(name: str, description: str, facts: FactsDocument) -> str | None:
    """The ``implementation`` fact id that refutes ``description`` as the row text of type
    ``name`` (rule (j2)'s row form: a description saying when the type is raised, for a type no
    library code throws or constructs), else ``None``. The renderer calls this with exactly what
    it prints, so it and the rule can never disagree about a Core API row (hosted runs
    43489976823 / 43489981024: ``DriverException`` "Exception thrown when rendering driver
    fails.", ``ExportException`` "Exceptions when Aspose.3D failed to export ...")."""
    fact_id = _never_thrown(facts).get(_last(name))
    if fact_id is None:
        return None
    if _WHEN_RAISED.search(description) and not _NOT_THROWN.search(description):
        return fact_id
    return None


def _never_thrown_findings(sentences: Iterable[Sentence], facts: FactsDocument, make: Make) -> list[ClaimFinding]:
    never = _never_thrown(facts)
    if not never:
        return []
    findings: list[ClaimFinding] = []
    for sentence, first, last in sentences:
        named: list[str] = []
        for span in _CODE_SPAN.finditer(sentence):
            name = _last(span.group(1))
            if name in never and _THROW_VERB.search(sentence[: span.start()]):
                named.append(name)
        lead = _LEADING_SPANS.match(sentence)
        if lead is not None:
            description = sentence[lead.end() :]
            if _WHEN_RAISED.search(description) and not _NOT_THROWN.search(description):
                named.extend(
                    name for name in (_last(s) for s in _CODE_SPAN.findall(lead.group("spans"))) if name in never
                )
        for name in dict.fromkeys(named):
            findings.append(
                make(
                    first,
                    sentence,
                    f"the README says `{name}` is thrown, but {never[name]} states no library code "
                    "throws or constructs it (it is only declared): drop the claim or say it is unused",
                    last,
                )
            )
    return findings


# --- (j3) stubs reached through a static instance ---------------------------------------------

_USE = re.compile(
    r"(?i)\b(?:used?\s+(?:with|by|in|for)|pass(?:ed|ing)?|save|saves|saving|load|loads|loading"
    r"|open|opens|opening|export|exports|import|imports|FromFile|FromStream|Save|Open)\b"
)


def _static_findings(sentences: Iterable[Sentence], facts: FactsDocument, make: Make) -> list[ClaimFinding]:
    fields: dict[str, tuple[str, str]] = {}
    for fact in _supported(facts, "implementation"):
        attributes = fact.attributes or {}
        if attributes.get("dispatch") == "static_instance":
            field = attributes.get("field", "")
            fields.setdefault(_last(field), (field, fact.id))
    if not fields:
        return []
    findings: list[ClaimFinding] = []
    for sentence, first, last in sentences:
        if _LIMITATION.search(sentence.replace("`", " ")) or not _USE.search(sentence):
            continue
        names = [_last(span) for span in _CODE_SPAN.findall(sentence)]
        stubbed = [name for name in dict.fromkeys(names) if len(name) >= 3 and name in fields]
        if not stubbed:
            continue
        cited = ", ".join(f"`{name}`" for name in stubbed)
        findings.append(
            make(
                first,
                sentence,
                f"the README describes {cited} as usable for loading or saving, but "
                f"{fields[stubbed[0]][1]} states the instance only throws there (it is constructed "
                "as a type that does not implement the member): name only the instances that work",
                last,
            )
        )
    return findings


# --- (j4) "throws NotImplemented" for a body that does not throw ------------------------------

_STUB_THROW = re.compile(
    r"(?i)\b(?:throws?|throwing|raises?|raising)\s+(?:an?\s+|the\s+)?`?(?:NotImplemented\w*)`?"
)
_CLAUSE = re.compile(r"(?:\.\s+|;\s+|\s+[—–]\s+|,\s+(?:but|while|whereas|so)\s+|\n\s*[-*+]\s+)")
_SUBJECT_GAP = 10


def _subject_spans(clause: str, end: int) -> list[re.Match[str]]:
    """The code spans that lead up to ``end`` (a throw marker) as its subject: walking back,
    a run of spans no more than a few words apart (``A``, ``B``, and the ``C`` pipeline)."""
    spans = [span for span in _CODE_SPAN.finditer(clause) if span.end() <= end]
    chain: list[re.Match[str]] = []
    boundary = end
    for span in reversed(spans):
        if len(re.findall(r"[A-Za-z]+", clause[span.end() : boundary])) > _SUBJECT_GAP:
            break
        chain.insert(0, span)
        boundary = span.start()
    return chain


class _Bodies:
    """Which public methods were read and hold no throw at all, by simple ``Type.Member``."""

    def __init__(self, facts: FactsDocument) -> None:
        self.no_throw: dict[str, set[str]] = {}
        self.methods: dict[str, set[str]] = {}
        self.throws: set[tuple[str, str]] = set()
        self.types: set[str] = set()
        returns: set[tuple[str, str]] = set()
        for fact in _supported(facts, "implementation"):
            attributes = fact.attributes or {}
            owner, _, member = attributes.get("member", "").rpartition(".")
            if not owner:
                continue
            key = (_last(owner), member)
            if attributes.get("aspect") == "throws":
                self.throws.add(key)
            elif attributes.get("aspect") == "constant_return" and not attributes.get("accessor"):
                returns.add(key)
        for fact in _supported(facts, "public_symbol"):
            attributes = fact.attributes or {}
            kind = attributes.get("symbol_kind", "")
            owner, _, member = fact.value.rpartition(".")
            if kind in ("class", "enum"):
                self.types.add(_last(fact.value))
            if kind not in ("method", "function") or not owner:
                continue
            key = (_last(owner), member)
            self.methods.setdefault(key[0], set()).add(member)
            if attributes.get("body_throws") == "no" or key in returns:
                self.no_throw.setdefault(key[0], set()).add(member)

    def member_does_not_throw(self, owner: str, member: str) -> bool:
        return member in self.no_throw.get(owner, set()) and (owner, member) not in self.throws

    def type_does_not_throw(self, owner: str) -> bool:
        methods = self.methods.get(owner, set())
        return (
            owner in self.types
            and bool(methods)
            and methods <= self.no_throw.get(owner, set())
            and not any(key[0] == owner for key in self.throws)
        )


def type_returns_values(name: str, facts: FactsDocument) -> bool:
    """Whether every method body of type ``name`` was read and holds no throw (rule (j4)'s own
    reading): a limitation statement saying the type only throws is then refuted, so nothing may
    describe it as a stub (BL-080: the Lane L correction's stub cell)."""
    return _Bodies(facts).type_does_not_throw(_last(name))


def _throw_findings(sentences: Iterable[Sentence], facts: FactsDocument, make: Make) -> list[ClaimFinding]:
    bodies = _Bodies(facts)
    if not bodies.no_throw:
        return []
    findings: list[ClaimFinding] = []
    for sentence, first, last in sentences:
        wrong: list[str] = []
        for clause in _CLAUSE.split(sentence):
            marker = _STUB_THROW.search(clause)
            if marker is None:
                continue
            owner: str | None = None
            for span in _subject_spans(clause, marker.start()):
                token = span.group(1).strip()
                if _STUB_THROW.search(f"throws {token}"):
                    continue
                match = re.fullmatch(r"(?:[\w.]+\.)?(?P<owner>[A-Z]\w*)\.(?P<member>\w+)(?:\(.*\))?", token)
                if match is not None:
                    owner = match.group("owner")
                    if bodies.member_does_not_throw(owner, match.group("member")):
                        wrong.append(f"{owner}.{match.group('member')}")
                    continue
                bare = re.fullmatch(r"(?P<member>\w+)\(.*\)", token)
                if bare is not None and owner is not None:
                    if bodies.member_does_not_throw(owner, bare.group("member")):
                        wrong.append(f"{owner}.{bare.group('member')}")
                    continue
                name = _last(token)
                owner = name
                if bodies.type_does_not_throw(name):
                    wrong.append(name)
        for name in dict.fromkeys(wrong):
            findings.append(
                make(
                    first,
                    sentence,
                    f"the README says `{name}` throws a not-implemented exception, but its body was "
                    "read and holds no throw (it returns a value): describe what it really does",
                    last,
                )
            )
    return findings


# --- (j5) formats reachable only through a stub ----------------------------------------------

_OUTPUT_VERB = re.compile(r"(?i)\b(?:export(?:s|ed|ing)?|sav(?:e|es|ed|ing)|writ(?:e|es|ing|ten)|convert(?:s|ed|ing)?\s+to)\b")
_INPUT_VERB = re.compile(r"(?i)\b(?:import(?:s|ed|ing)?|load(?:s|ed|ing)?|read(?:s|ing)?|open(?:s|ed|ing)?|pars(?:e|es|ed|ing))\b")
_EXTENSION = re.compile(r"`\.(?P<ext>[A-Za-z0-9]{2,6})`|\b(?P<word>[A-Z][A-Za-z0-9]{1,8})\b")
_FORMAT_ALIASES = {"collada": "dae", "wavefront": "obj"}
_NEGATED = re.compile(r"(?i)\b(?:no|not|never|without|except|cannot|can't|unsupported|unreachable)\b(?:\s+\S+){0,3}\s*$")


def _stubbed_formats(facts: FactsDocument) -> dict[tuple[str, str], str]:
    found: dict[tuple[str, str], str] = {}
    for fact in facts.by_kind("format"):
        if (fact.attributes or {}).get("code_path") != "stub" or fact.polarity == "SUPPORTED":
            continue
        direction = fact.id.split(":", 1)[1].split(".", 1)[0]
        found[(direction, fact.value.lower().lstrip("."))] = fact.id
    return found


def _format_findings(sentences: Iterable[Sentence], facts: FactsDocument, make: Make) -> list[ClaimFinding]:
    stubbed = _stubbed_formats(facts)
    if not stubbed:
        return []
    extensions = {extension for _, extension in stubbed}
    findings: list[ClaimFinding] = []
    for sentence, first, last in sentences:
        hits: list[tuple[str, str]] = []
        for clause in re.split(r";\s+|,\s+but\s+|\s+[—–]\s+", sentence):
            if _LIMITATION.search(clause.replace("`", " ")):
                continue  # the clause itself states the limit
            for match in _EXTENSION.finditer(clause):
                extension = (match.group("ext") or "").lower() or _FORMAT_ALIASES.get(
                    (match.group("word") or "").lower(), (match.group("word") or "").lower()
                )
                if match.group("word") and not match.group("word").isupper() and match.group("word") != "glTF":
                    continue  # a format name is spelled in capitals (``COLLADA``, ``OBJ``)
                if extension not in extensions or _NEGATED.search(clause[: match.start()]):
                    continue
                before = clause[: match.start()]
                for direction, verb in (("output", _OUTPUT_VERB), ("input", _INPUT_VERB)):
                    if verb.search(before) and (direction, extension) in stubbed:
                        hits.append((direction, extension))
        for direction, extension in dict.fromkeys(hits):
            findings.append(
                make(
                    first,
                    sentence,
                    f"the README claims .{extension} {direction}, but {stubbed[(direction, extension)]} "
                    "is reachable only through a stub (the dispatcher raises before reaching a real "
                    f"implementation): drop .{extension} from the {direction} formats",
                    last,
                )
            )
    return findings


# --- (j6) "no dependencies" against the published package (K06) ------------------------------

_NO_DEPENDENCIES = re.compile(
    r"(?i)\b(?:no|zero|without(?:\s+any)?)\s+(?:required\s+|external\s+|runtime\s+)?(?:third[- ]party\s+)?"
    r"(?:package\s+|NuGet\s+|runtime\s+)?dependenc(?:y|ies)\b|\bdoes\s+not\s+depend\s+on\s+any\b"
    r"|\bdependency[- ]free\b|\bhas\s+no\s+dependencies\b"
)


# The statement is about the package itself: it opens the sentence, or the package is its subject.
_PACKAGE_SUBJECT = re.compile(
    r"(?i)^[\W_]*$|\b(?:package|library|it|project|product|FOSS|SDK|module)\b[^.;]*$"
)


def _consumer_dependencies(facts: FactsDocument) -> list[Fact]:
    return [
        fact
        for fact in _supported(facts, "dependency")
        if fact.id != "dependency:none"
        and not fact.id.startswith(("dependency:development.", "dependency:optional."))
    ]


def _dependency_findings(sentences: Iterable[Sentence], facts: FactsDocument, make: Make) -> list[ClaimFinding]:
    dependencies = _consumer_dependencies(facts)
    if not dependencies:
        return []
    names = ", ".join(fact.value for fact in dependencies[:4])
    listed = [re.split(r"[\s<>=!~^@]", fact.value, maxsplit=1)[0].lower() for fact in dependencies]
    findings: list[ClaimFinding] = []
    for sentence, first, last in sentences:
        match = _NO_DEPENDENCIES.search(sentence)
        if match is None or any(name and name in sentence.lower() for name in listed):
            continue
        if not _PACKAGE_SUBJECT.search(sentence[: match.start()]):
            continue  # "SVG output has no third-party dependency" is about one feature
        findings.append(
            make(
                first,
                sentence,
                f"the README says the package has no dependencies, but the published package "
                f"declares {names} ({dependencies[0].id}): list them",
                last,
            )
        )
    return findings


# --- (j7) samples said to use the package (K06) -----------------------------------------------

# The repository's sample projects, not a README code example ("The first example reads ...").
_SAMPLES = re.compile(
    r"(?i)\bsamples\b|\bsamples?/|\b(?:sample|example)s?\s+(?:projects?|programs?|apps?|applications?|directory|folder)\b"
)
# "usage of" / "demonstrating usage of" (BL-079, hosted run 43489984973): a Cells .NET repair
# reworded "demonstrating how to use `Aspose.Cells.FOSS` version 26.10.0" to "demonstrating usage
# of Aspose.Cells FOSS for .NET version 26.10.0.0" -- the same false claim, which the verb list
# did not read, so the repair was accepted as having cleared it.
_CONSUME = re.compile(r"(?i)\b(?:use|uses|using|usage\s+of|reference|references|referencing|consume|consumes|built?\s+(?:against|with|on)|demonstrat\w*\s+how\s+to\s+use)\b")
_VERSION = re.compile(r"\bversion\s+\d+(?:\.\d+)+\b|\b\d+\.\d+\.\d+\b|\bNuGet\s+package\b|\bPackageReference\b", re.IGNORECASE)


def _sample_findings(sentences: Iterable[Sentence], facts: FactsDocument, make: Make) -> list[ClaimFinding]:
    fact = next(
        (f for f in _supported(facts, "project_file") if f.id == "project_file:samples.product_reference"),
        None,
    )
    attributes = (fact.attributes or {}) if fact is not None else {}
    if fact is None or attributes.get("package_reference") != "0" or attributes.get("project_reference", "0") == "0":
        return []
    package = attributes.get("package", "")
    # The package's own versions: a sentence that names the product by its prose name and gives one
    # of these ("usage of Aspose.Cells FOSS for .NET version 26.10.0.0", BL-079, hosted run
    # 43489984973) claims the samples use that package as surely as one naming its id.
    own_versions = [
        re.compile(rf"(?<![\w.]){re.escape(fact.value)}(?![\w]|\.\d)")
        for fact in facts.facts
        if fact.id in ("package:version", "package:published_version") and fact.value
    ]
    findings: list[ClaimFinding] = []
    for sentence, first, last in sentences:
        plain = sentence.replace("`", "")
        if not (_SAMPLES.search(plain) and _CONSUME.search(plain) and _VERSION.search(plain)):
            continue
        if (
            package
            and package.lower() not in plain.lower()
            and not any(version.search(plain) for version in own_versions)
        ):
            continue
        findings.append(
            make(
                first,
                sentence,
                f"the README says the samples use the published package, but {fact.id} states "
                f"{fact.value}: say they build against the source project",
                last,
            )
        )
    return findings


def code_path_findings(sentences: Iterable[Sentence], facts: FactsDocument, make: Make) -> list[ClaimFinding]:
    """Rules (j1)-(j7) over one README's sentences (``(text, first line, last line)``)."""
    every = list(sentences)
    return [
        *_stated_stub_findings(every, facts, make),
        *_never_thrown_findings(every, facts, make),
        *_static_findings(every, facts, make),
        *_throw_findings(every, facts, make),
        *_format_findings(every, facts, make),
        *_dependency_findings(every, facts, make),
        *_sample_findings(every, facts, make),
    ]


__all__ = [
    "NOT_THROWN_DESCRIPTION",
    "code_path_findings",
    "refuted_thrown_description",
    "stub_members",
]
