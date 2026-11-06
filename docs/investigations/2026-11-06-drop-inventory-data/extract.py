"""Enumerate every item dropped from the live README across every Lane R seal (and the committed
3D .NET candidate). Read-only, zero provider calls. Writes drops_raw.json and pipeline.json."""
import json, re, shutil, subprocess, sys, tempfile
from pathlib import Path
from types import SimpleNamespace

from repo_presenter.readme.validation.content_presence import unstated, _anchors, _plain
from repo_presenter.readme import parity_gate as pg
from repo_presenter.readme.validation.supersession import superseded_failures, exempt as bc05_exempt

SP = Path('/tmp/claude-0/-home-user/542f6e2c-a780-567b-84f4-4e5f84153686/scratchpad')
S = SP / 'seals'
WT = Path('/home/user/repo-presenter/.claude/worktrees/agent-a967872da417c137a')
idx = json.load(open(S / 'index.json'))
targets = [(r['repository'], r['lane'], r['commit'], Path(r['bundle'])) for r in idx if r['lane'] == 'R' and r['bundle']]
for c in sorted((WT / 'candidates').glob('*/CURRENT')):
    rev = c.read_text().strip()
    d = c.parent / rev
    if (d / 'dispositions.json').exists():
        targets.append((c.parent.name.replace('__', '/', 1), 'R', 'committed:candidates/' + c.parent.name, d))


def original(bundle: Path) -> str:
    with tempfile.TemporaryDirectory() as t:
        out = Path(t) / 'orig.md'
        p = subprocess.run(['patch', '-R', '-s', '-o', str(out), str(bundle / 'README.md'), str(bundle / 'README.patch.diff')],
                           capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(p.stdout + p.stderr)
        return out.read_text(encoding='utf-8')


def kind_of(uid):
    return uid.rsplit('.', 1)[-1]


raw, pipe = [], []
for repo, lane, commit, b in targets:
    readme = (b / 'README.md').read_text(encoding='utf-8')
    orig = (SP / 'origs' / f"{repo.replace('/', '__')}@{b.name}.md").read_text(encoding='utf-8')
    facts = json.load(open(b / 'facts.json'))['facts']
    units = {f['id']: f for f in facts if f['kind'] == 'inherited_unit'}
    rows = {r['unit_id']: r for r in json.load(open(b / 'dispositions.json'))['dispositions']}
    # sanity: each unit's text in the reconstructed original
    bad = [u for u, f in units.items() if (f.get('value') or '').strip() and (f['value'].strip().splitlines()[0] not in orig)]
    cand = pg.SealedCandidate('R', readme, tuple(facts), tuple(rows.values()))
    losses = pg.content_losses(cand, orig)
    view = SimpleNamespace(facts=SimpleNamespace(by_kind=lambda k: [SimpleNamespace(id=f['id'], value=str(f.get('value') or '')) for f in facts if f['kind'] == k]),
                           dispositions={'dispositions': list(rows.values())}, readme=readme)
    bc05 = {f.unit: f.detail for f in superseded_failures(view)}
    bc17_units = {}
    for l in losses:
        for u in l.units:
            bc17_units.setdefault(u, []).append(f'{l.category}:{l.item}')
    bc17_unheld = [f'{l.category}:{l.item}' for l in losses if not l.units]
    pipe.append(dict(repository=repo, commit=commit, revision=b.name, unmatched_units=bad,
                     bc17_losses=[dict(category=l.category, item=l.item, units=list(l.units), stage=l.stage) for l in losses],
                     bc05_failures=bc05))
    cand_doc = pg.read_markdown(readme)
    cand_topics = [n for lv, n in cand_doc.headings if lv in (2, 3, 4)]
    for uid, f in units.items():
        text = str(f.get('value') or '')
        if not text.strip():
            continue
        k = kind_of(uid)
        row = rows.get(uid) or {}
        disp = row.get('disposition', 'NO_ROW')
        section = (f.get('attributes') or {}).get('section', '')
        pieces = []
        if k == 'heading':
            name = text.lstrip('#').strip()
            if not any(pg.topics_match(name, o) for o in cand_topics) and _plain(name) not in _plain(readme):
                pieces.append(('heading', name))
        elif k == 'code_block':
            miss = unstated(text, readme, kind='code_block')
            if miss:
                pieces.append(('code_block', text))
        elif k in ('list', 'table'):
            if k == 'list':
                from repo_presenter.readme.composition.list_coverage import list_items
                rows_ = list_items(text) or [l for l in text.splitlines() if l.strip()]
            else:
                rows_ = [l for l in text.splitlines() if l.strip() and not re.fullmatch(r"[\s|:-]+", l)]
                rows_ = rows_[1:] if len(rows_) > 1 else rows_  # header row judged with the table
            for it in rows_:
                miss = unstated(it, readme, kind='paragraph', strict=True)
                if miss:
                    pieces.append((k + '_item', it.strip() + '  ||missing: ' + '; '.join(miss[:6])))
        else:
            from repo_presenter.readme.validation.content_presence import _sentences
            for sent in _sentences(text, 'paragraph') if k == 'paragraph' else [text]:
                miss = unstated(sent, readme, kind='paragraph', strict=True)
                if miss:
                    pieces.append(((k if k != 'paragraph' else 'sentence'), sent.strip() + '  ||missing: ' + '; '.join(miss[:6])))
        for pk, pv in pieces:
            raw.append(dict(repository=repo, lane='R', commit=commit, revision=b.name, unit=uid, unit_kind=k,
                            section=section, piece_kind=pk, piece=pv, disposition=disp,
                            rationale=row.get('rationale', ''), fact_ids=row.get('fact_ids', []),
                            unit_text=text,
                            bc05_fails=uid in bc05, bc05_exempt=(disp == 'SUPERSEDE_REDUNDANT' and bc05_exempt(uid, text, row.get('rationale') or '')),
                            bc17_fails=uid in bc17_units, bc17_items=bc17_units.get(uid, []),
                            nonloss=pg.disposition_is_non_loss(row, {x['id']: x for x in facts}) if row else False))
json.dump(raw, open(SP / 'drops_raw.json', 'w'), indent=1)
json.dump(pipe, open(SP / 'pipeline.json', 'w'), indent=1)
print(len(targets), 'targets', len(raw), 'raw drop pieces')
for p in pipe:
    print(p['repository'].split('/')[1][:28], p['commit'][:8], 'unmatched', len(p['unmatched_units']), 'bc17', len(p['bc17_losses']), 'bc05', len(p['bc05_failures']))
