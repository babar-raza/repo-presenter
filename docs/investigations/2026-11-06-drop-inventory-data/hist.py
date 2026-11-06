import json, sys
from pathlib import Path
from repo_presenter.core.state.bundle_store import seal_history
S = Path(sys.argv[1])
S.mkdir(parents=True, exist_ok=True)
h = seal_history(scratch=S)
out = []
for (repo, lane), rows in sorted(h.items()):
    for r in rows:
        out.append(dict(repository=repo, lane=lane, commit=r.commit, revision=r.revision,
                        state=r.manifest_state, error=r.error,
                        bundle=str(r.bundle) if r.bundle else None, files=sorted(r.files),
                        recert=bool(r.recertified_from), counted=r.counted))
json.dump(out, open(S / 'index.json', 'w'), indent=1)
print(len(out))
