"""HTTP status of every external link in a dropped item (read-only GET/HEAD, no provider)."""
import json, urllib.request, ssl
from pathlib import Path
SP = Path('/tmp/claude-0/-home-user/542f6e2c-a780-567b-84f4-4e5f84153686/scratchpad')
it = json.load(open(SP / 'items.json'))
urls = sorted({l['target'] for x in it for l in x['evidence'].get('links', []) if l['target'].startswith('http')})
ctx = ssl.create_default_context(cafile='/root/.ccr/ca-bundle.crt')
out = {}
for u in urls:
    try:
        req = urllib.request.Request(u, method='GET', headers={'User-Agent': 'Mozilla/5.0 drop-inventory'})
        with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
            out[u] = r.status
    except urllib.error.HTTPError as e:
        out[u] = e.code
    except Exception as e:
        out[u] = type(e).__name__
    print(out[u], u)
json.dump(out, open(SP / 'link_status.json', 'w'), indent=1)
