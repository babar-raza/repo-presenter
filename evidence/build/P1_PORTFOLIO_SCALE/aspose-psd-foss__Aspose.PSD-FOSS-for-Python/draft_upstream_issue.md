<!-- NOT FILED. Owner authorization required per mission section 9 before filing; see this repo's docs/MISSION_AUTHORITY.md. -->

**Target repository:** `aspose-psd-foss/Aspose.PSD-FOSS-for-Python`
**Target revision:** `2271c228d991bcd79048bb61773bcbcb415399c6` (current `main` as of 2026-10-21)

## Proposed title

README claims Python 3.7+ support, but the published PyPI package requires Python >=3.8

## Proposed body

The README states twice that the package "runs on Python 3.7+" and "Requires
Python 3.7 or later," but the published package's own metadata on PyPI says
otherwise:

```
$ curl -s https://pypi.org/pypi/aspose-psd-foss/json | python -c "import json,sys; print(json.load(sys.stdin)['info']['requires_python'])"
>=3.8
```

`pip install aspose-psd-foss` on Python 3.7 will be refused by pip given this
metadata, contradicting the README's own installation instructions. No
`setup.py`/`pyproject.toml`/`setup.cfg` exists in this repository to check
which value the maintainers intended — recommend either correcting the README
to say 3.8+, or relaxing the published `python_requires` if 3.7 support is
actually intended and was dropped unintentionally.

## Dedup check performed

`gh issue list --repo aspose-psd-foss/Aspose.PSD-FOSS-for-Python --state all` returns
2 existing issues (#4 "Add a LICENSE file and merge real source to main", #1
"timeline for fully open-sourced"), neither related. `--search "python version requires"`
returns `[]`. Not a duplicate.
