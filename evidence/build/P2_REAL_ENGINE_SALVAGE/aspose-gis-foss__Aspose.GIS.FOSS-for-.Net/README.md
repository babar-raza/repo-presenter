# Lane L run — Aspose.GIS.FOSS-for-.Net — FAILED (no live README)

2026-10-22.

Repository shallow-cloned successfully (`git clone --depth 1
https://github.com/aspose-gis-foss/Aspose.GIS.FOSS-for-.Net.git`, 114 files in tree).

Command attempted:

```
python scripts/run_lane_l.py aspose-gis-foss/Aspose.GIS.FOSS-for-.Net net <clone>
```

## Real failure

Step `[2/5] fetching live README` crashed the script with:

```
Traceback (most recent call last):
  File "scripts\run_lane_l.py", line 217, in <module>
    main()
  File "scripts\run_lane_l.py", line 177, in main
    readme_bytes = fetch_live_readme(repository)
  File "scripts\run_lane_l.py", line 108, in fetch_live_readme
    result = subprocess.run(
        ["gh", "api", f"repos/{repository}/readme", "--jq", ".content"],
        ...
        check=True,
    )
  ...
subprocess.CalledProcessError: Command '['gh', 'api', 'repos/aspose-gis-foss/Aspose.GIS.FOSS-for-.Net/readme', '--jq', '.content']' returned non-zero exit status 1.
```

Root cause confirmed independently (not a `gh` auth problem — `gh auth status` shows this
session logged in and active):

```
$ gh api repos/aspose-gis-foss/Aspose.GIS.FOSS-for-.Net/readme --jq ".content"
{"message":"Not Found","documentation_url":"https://docs.github.com/rest/repos/contents#get-a-repository-readme","status":"404"}
gh: Not Found (HTTP 404)
```

```
$ gh api repos/aspose-gis-foss/Aspose.GIS.FOSS-for-.Net/contents
['.gitignore', 'Aspose.GIS.FOSS.Tests', 'Aspose.GIS.FOSS.slnx', 'Aspose.GIS.FOSS']
```

The repository's default-branch root genuinely has no `README.md` (or any other
GitHub-recognized README variant) — `gh`'s own repo-contents listing confirms the root
tree is exactly `.gitignore`, `Aspose.GIS.FOSS.Tests`, `Aspose.GIS.FOSS.slnx`,
`Aspose.GIS.FOSS`. This matches what the local shallow clone shows too.

This is a real, external precondition failure of the target repository, not a bug in
`scripts/run_lane_l.py` or in the Lane L engine — the script's `fetch_live_readme()`
correctly propagates the 404 as a hard failure rather than silently treating a missing
README as empty. No facts or findings were produced for this repository; no `facts.json`
exists in this directory. Per task instructions, not fixed and not worked around — the
underlying source was left untouched. Moved on to the next repository.
