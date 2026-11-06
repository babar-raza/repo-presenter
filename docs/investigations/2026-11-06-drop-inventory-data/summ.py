import json, re
from collections import Counter, defaultdict
from pathlib import Path
SP = Path('/tmp/claude-0/-home-user/542f6e2c-a780-567b-84f4-4e5f84153686/scratchpad')
raw = json.load(open(SP / 'drops_raw.json'))
def norm(s):
    return re.sub(r'\s+', ' ', s).strip().lower()
g = defaultdict(list)
for r in raw:
    g[(r['repository'], r['piece_kind'], norm(r['piece'].split('  ||missing:')[0]))].append(r)
print('distinct', len(g))
print(Counter(k[1] for k in g))
print(Counter((v[-1]['unit_kind'], v[-1]['disposition']) for v in g.values()).most_common(40))
print(Counter(k[0].split('/')[1] for k in g))
json.dump([dict(key=list(k), occ=len(v), rows=v) for k, v in g.items()], open(SP / 'groups.json', 'w'), indent=1)
