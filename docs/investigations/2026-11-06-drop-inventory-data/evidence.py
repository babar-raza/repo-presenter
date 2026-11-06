"""Attach source evidence to every distinct dropped item (read-only, local clones, no provider)."""
import json, re, subprocess, glob
from pathlib import Path
from functools import lru_cache

SP = Path('/tmp/claude-0/-home-user/542f6e2c-a780-567b-84f4-4e5f84153686/scratchpad')
G = json.load(open(SP / 'groups.json'))
idx = json.load(open(SP / 'seals' / 'index.json'))
CL = SP / 'clones'

def clone_for(repo, rev):
    return CL / f"{repo.replace('/', '__')}@{rev[:12]}"

def bundle_of(row):
    if row['commit'].startswith('committed:'):
        d = Path('/home/user/repo-presenter/.claude/worktrees/agent-a967872da417c137a') / row['commit'].split(':', 1)[1]
        return d / row['revision']
    return next(Path(r['bundle']) for r in idx if r['commit'] == row['commit'])

@lru_cache(None)
def facts(bpath):
    return json.load(open(Path(bpath) / 'facts.json'))['facts']

@lru_cache(None)
def public(bpath):
    out = set()
    for f in facts(bpath):
        if f['kind'] in ('public_symbol', 'enum_member') and f['polarity'] == 'SUPPORTED':
            v = str(f['value'])
            out.add(re.split(r'::|\.', re.split(r'[(\s]', v.strip(), maxsplit=1)[0])[-1].lower())
    return frozenset(out)

@lru_cache(None)
def link_facts(bpath):
    return {str(f['value']).rstrip('/').lower(): f['polarity'] for f in facts(bpath) if f['kind'] == 'link_target'}

@lru_cache(None)
def readme(bpath):
    return (Path(bpath) / 'README.md').read_text(encoding='utf-8')

SRC_EXT = ('*.py', '*.cs', '*.java', '*.ts', '*.go', '*.rs', '*.h', '*.hpp', '*.cpp', '*.js')

@lru_cache(None)
def defined(clone, name):
    """path:line of a definition of name in source (excluding README/docs), or ''."""
    base = re.escape(name.split('(')[0].split('.')[-1].split('::')[-1])
    if not base or len(base) < 2:
        return ''
    pat = rf"(class|struct|enum|interface|trait|type|def|fn|func|function|record|const|let|var|static|public|export)\b[^\n]*\b{base}\b|\b{base}\s*[:=(]"
    args = ['grep', '-rnE', '-m1', pat, str(clone)] + [f'--include={e}' for e in SRC_EXT]
    p = subprocess.run(args, capture_output=True, text=True)
    for line in p.stdout.splitlines():
        if '/README' in line:
            continue
        return line.replace(str(clone) + '/', '')[:160]
    return ''

def path_exists(clone, target):
    t = target.split('#')[0].split('?')[0].strip()
    m = re.match(r'^https?://github\.com/[^/]+/[^/]+/(?:blob|tree)/[^/]+/(.+)$', t, re.I)
    if m:
        t = m.group(1)
    if t.startswith(('http://', 'https://', 'mailto:')) or not t:
        return None
    t = t[2:] if t.startswith('./') else t.lstrip('/')
    return (clone / t).exists()

SPAN = re.compile(r'`([^`\n]+)`')
LINK = re.compile(r'\]\(\s*<?([^)\s>]+)')
URL = re.compile(r'https?://[^\s)>\]`]+')

out = []
for i, g in enumerate(G):
    r = g['rows'][-1]
    clone = clone_for(r['repository'], r['revision'])
    b = str(bundle_of(r))
    item = r['piece'].split('  ||missing:')[0]
    missing = r['piece'].split('  ||missing:')[1].strip() if '||missing:' in r['piece'] else ''
    ev = {}
    spans = SPAN.findall(item)
    lead = re.match(r'^\s*(?:\|\s*|[-*+]\s+)?(?:\*\*)?`([^`\n]+)`', item)
    if lead:
        name = lead.group(1)
        ev['subject'] = name
        core = re.split(r'::|\.', re.split(r'[(\s<]', name.strip(), maxsplit=1)[0])[-1].lower()
        ev['subject_public'] = core in public(b)
        ev['subject_printed'] = name.lower() in readme(b).lower()
        rq = re.match(r'^([A-Za-z_]\w*)-([A-Za-z_]\w*)$', name)
        if rq:
            ev['requalified'] = f'{rq.group(2)}.{rq.group(1)}'
            ev['requalified_printed'] = f'`{ev["requalified"].lower()}`' in readme(b).lower()
            name = rq.group(1)
            core = name.lower()
            ev['subject_public'] = core in public(b)
        cells = [c.strip() for c in item.strip().strip('|').split('|')]
        if len(cells) >= 2:
            desc = re.sub(r'\s+', ' ', cells[-1]).lower()
            ev['description_printed'] = len(desc) > 12 and desc in re.sub(r'\s+', ' ', readme(b)).lower()
        if '/' in name or re.search(r'\.(ts|py|cs|go|rs|java|md|json|csproj|toml|xml)$', name):
            ev['subject_path_exists'] = path_exists(clone, name)
        else:
            ev['subject_defined'] = defined(clone, name)
    links = list(dict.fromkeys(LINK.findall(item) + URL.findall(item)))
    if links:
        ev['links'] = []
        for l in links:
            ev['links'].append(dict(target=l, path_exists=path_exists(clone, l),
                                    link_fact=link_facts(b).get(l.rstrip('/').lower()),
                                    printed=l.rstrip('/').lower() in readme(b).lower()))
    out.append(dict(i=i, repository=r['repository'], lane='R', unit=r['unit'], unit_kind=r['unit_kind'],
                    piece_kind=r['piece_kind'], item=item, missing=missing, disposition=r['disposition'],
                    rationale=r['rationale'], fact_ids=r['fact_ids'], section=r['section'],
                    occurrences=g['occ'], seals=sorted({x['commit'][:12] for x in g['rows']}),
                    revision=r['revision'], bc05=any(x['bc05_fails'] for x in g['rows']),
                    bc05_latest=r['bc05_fails'], bc17=any(x['bc17_fails'] for x in g['rows']), bc17_latest=r['bc17_fails'],
                    bc05_exempt=r['bc05_exempt'], nonloss=r['nonloss'], evidence=ev, bundle=b))
json.dump(out, open(SP / 'items.json', 'w'), indent=1)
print(len(out))
