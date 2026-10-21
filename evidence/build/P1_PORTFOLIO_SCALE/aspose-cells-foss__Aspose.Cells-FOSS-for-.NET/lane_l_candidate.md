Empty-patch ACCEPT. All 12 checked facts in facts.json are SUPPORTED (0 CONTRADICTED) --
every Quick Start / Additional Examples snippet, the build command, two sample projects,
the API Reference spot-checks, and both Scope and Limitations negative claims (no formula
engine, XLSX-only load) were reproduced live against a real `dotnet build`/`dotnet run` of
this exact source_revision. Per the playbook's fast path, the Lane L candidate is the live
README unchanged at source_revision 941814fd138dc28cf47123d48194f329f283498d. No
`lane_l_candidate.diff` is produced for this reason.
