"""Measure the current pipeline against the decisions and write data/drop_decisions.json."""
import json, re
from collections import Counter, defaultdict
from pathlib import Path

SP = Path('/tmp/claude-0/-home-user/542f6e2c-a780-567b-84f4-4e5f84153686/scratchpad')
WT = Path('/home/user/repo-presenter/.claude/worktrees/agent-a967872da417c137a')
D = json.load(open(SP / 'decisions.json'))
G = json.load(open(SP / 'groups.json'))
idx = json.load(open(SP / 'seals' / 'index.json'))

def n(s):
    return re.sub(r'[^a-z0-9]+', '', s.lower())

import sys
sys.path.insert(0, str(WT / 'src'))
from types import SimpleNamespace
from repo_presenter.readme.validation.content_presence import unstated
from repo_presenter.readme.validation import supersession as sup

def bc05_item(x, r):
    """Item-level BC-05: the superseded unit's owed missing pieces (the exact supersession computation) touch this item."""
    b = Path(x['bundle'])
    facts = json.load(open(b / 'facts.json'))['facts']
    view = SimpleNamespace(facts=SimpleNamespace(by_kind=lambda k: [SimpleNamespace(id=f['id'], value=str(f.get('value') or '')) for f in facts if f['kind'] == k]))
    pub = sup.public_names(view)
    text = next(str(f.get('value') or '') for f in facts if f['id'] == r['unit'])
    kind = sup._kind(r['unit'])
    pieces = [p for p in unstated(sup.owed_text(text, kind, pub), (b / 'README.md').read_text(encoding='utf-8'), kind=kind, strict=True) if sup.owed(p, pub)]
    item = n(x['item'])
    for p in pieces:
        m = re.match(r"^(?:span|link|number) '(.*)'$", p)
        core = n(m.group(1) if m else p.strip("'\""))[:40]
        if core and core in item:
            return True
    return False

def bc17_item(x, rows):
    """Item-level BC-17: a loss label of the latest occurrence's unit matches this item."""
    r = rows[-1]
    text = n(x['item'])
    for lab in r['bc17_items']:
        cat, _, item = lab.partition(':')
        li = n(item)
        if li and (li[:40] in text or (cat == 'code_blocks' and li[:30] in text)):
            return True
    return False

RULES = {
 'R-CODE-EVIDENCE': ('code_block (any disposition) whose example fact is not CONTRADICTED, every path/identifier it names exists at the revision, and no identical block is printed', 'READD', 'first decision 2026-11-06 (Imaging 018); a lead-in/heading goes with its block (R-LEADIN)'),
 'R-HARNESS': ('code_block whose example fact is CONTRADICTED only by an isolation failure: an undefined helper or an absent optional dependency that the block itself names, and that the repository defines or the README documents', 'READD', 'a failure on a real API defect is R-CONTRADICTED'),
 'R-CONTRADICTED': ('code_block whose example fails against the source at the revision for a reason inside the block (compile error on a missing include, AttributeError on the maintainers\' own fixture)', 'KEEP_DROPPED', 'a CORRECT_WITH_EVIDENCE repair would be better than a drop where the fix is mechanical (Cells C++ missing #include)'),
 'R-DIAGRAM': ('maintainers\' mermaid code_block when the candidate draws its own At a Glance diagram', 'KEEP_DROPPED', 'matches BC-05/BC-17 exemption'),
 'R-VERSION-REPLACED': ('install snippet / command reprinted by the candidate with the verified current version (package:version / published_version) for the same tool and package', 'KEEP_DROPPED', ''),
 'R-CORRECTION-PRINTED': ('CORRECT_WITH_EVIDENCE unit whose corrected text the candidate does not print', 'READD', 'the pipeline treats CORRECT_WITH_EVIDENCE as always non-loss; a correction that is never printed is a drop'),
 'R-LINK-RESOLVES': ('link or file path (in any unit kind, incl. table cells and badges) whose target exists at the revision or resolves, and that the candidate prints nowhere', 'READD', '3D .NET aspose.org doc links: host unreachable from the sandbox, decided by the sibling-seal URL pattern'),
 'R-LINK-DEAD': ('link or path whose target does not exist at the revision (link_target CONTRADICTED / file absent)', 'KEEP_DROPPED', ''),
 'R-API-PRIVATE': ('API table row whose subject is outside the language\'s own export surface (Rust lib.rs re-exports, TS index.ts exports, C++ include/ headers, Python package __init__/__all__, else facts.json public surface)', 'KEEP_DROPPED', 'extends supersession.owed() calibration (Cells-Rust core_*) to all languages'),
 'R-API-REQUALIFIED': ('API table row `Name-suffix` carried as `<qualifier>.Name` sharing a token with suffix', 'KEEP_DROPPED', 'detector false positive: carried'),
 'R-API-FILLER': ('API table row for a public subject whose original description is generator filler ("Class with N methods", "Class in the X API.", "Interface with N properties")', 'KEEP_DROPPED', ''),
 'R-API-ROW-MISSING': ('API table row for a public subject with no row in the candidate', 'READD', ''),
 'R-API-DESC': ('API table row for a public subject whose maintainer description (spec section, members, tag, signature) the candidate replaced by a generic restatement', 'READD', ''),
 'R-API-IDENT': ('prose/list item naming a public member (by the language\'s own surface or facts) that the candidate prints nowhere', 'READD', 'facts.json misses struct fields, enum members and some methods (Rust CellStyle, Note enums): the surface must come from source'),
 'R-PROSE-VALID': ('prose/list item stating a technical fact (platform, dependency purpose, limitation, build/test/CI guidance, behaviour) that the source does not contradict and the candidate prints nowhere', 'READD', ''),
 'R-VERSION': ('dependency/tool version pinned in a project file at the revision that the candidate prints nowhere', 'READD', ''),
 'R-LEADIN': ('lead-in sentence or heading of a block: decided with its block', 'same as block', '2 KEEP (block carried), 10 READD (block READD or block printed without its explanation)'),
 'R-CARRIED': ('item whose substance the candidate states (paraphrase, qualified name, same link/file under another path); only a markup token, example value or literal spelling differs', 'KEEP_DROPPED', 'detector false positive of unstated(strict=True)'),
 'R-POSITIONAL': ('positional pointer prose ("collected below", "beyond the Quick Start above")', 'KEEP_DROPPED', 'matches supersession.exempt positional_only'),
 'R-COUNT': ('a count of public types the verified surface contradicts or that points at a table the renderer replaces', 'KEEP_DROPPED', ''),
 'R-HEADING': ('heading / <details> wrapper markup the renderer owns, when the content under it is carried or decided separately', 'KEEP_DROPPED', 'not when its section is re-added (R-LEADIN)'),
 'R-BADGE': ('badge whose information (license, package version, runtime floor) is printed elsewhere, or a decorative contributor/issue count', 'KEEP_DROPPED', 'a badge carrying a resolving product link the candidate lacks is R-LINK-RESOLVES (3D .NET banner)'),
 'R-NAMING': ('Lane L enterprise_edition_naming edit replacing "the commercial X" by "X - Enterprise Edition" (link_target:product.enterprise)', 'KEEP_DROPPED', 'only the substitute wording is removed; the referent is carried'),
}

out_items = []
pipe = Counter(); per_rule = defaultdict(Counter); disagreements = defaultdict(list)
for x in D:
    rows = G[x['i']]['rows']
    bc05u = rows[-1]['bc05_fails']
    bc05 = bc05u and bc05_item(x, rows[-1])
    bc17u = rows[-1]['bc17_fails']
    bc17i = bc17_item(x, rows)
    flagged = bc05 or bc17i
    pdec = 'READD' if flagged else 'KEEP_DROPPED'
    agree = pdec == x['decision']
    per_rule[x['rule']]['n'] += 1
    per_rule[x['rule']]['agree' if agree else 'disagree'] += 1
    if not agree:
        disagreements[x['rule']].append(x['i'])
    dropped_as = f"{x['disposition']}: {x['rationale'][:200]}" if x['disposition'] != 'NO_ROW' else 'no disposition row'
    out_items.append(dict(
        repository=x['repository'], lane='R', item=f"{x['unit']} ({x['piece_kind']})",
        text=x['item'][:300], dropped_as=dropped_as, decision=x['decision'], evidence=x['decision_evidence'],
        rule=x['rule'], occurrences=x['occurrences'], seals=x['seals'], revision=x['revision'],
        pipeline=dict(stored_disposition=x['disposition'], disposition_non_loss=x['nonloss'], bc05_unit_fails=bc05u, bc05_item_flagged=bc05,
                      bc17_unit_fails=bc17u, bc17_item_flagged=bc17i, decides=pdec, agrees=agree),
        decided_by='supervisor-worker (w/drop-inventory)', decided_at='2026-11-06', inventory_id=x['i']))

# Lane L: every text removal across the 37 Lane L seals (34 are byte-identical no-ops)
lane_l = [
 ('aspose-3d-foss/Aspose.3D-FOSS-for-Java', 'README.md:634 edit 0 (enterprise_edition_naming)', 'the commercial Aspose.3D for Java', 3, ['9cbfd021e153', '77f3fc2c99d3', 'e0d4134ef1ea']),
 ('aspose-words-foss/Aspose.Words-FOSS-for-Python', 'README.md:11 edit 0 (enterprise_edition_naming)', 'the commercial Aspose.Words for Python', 2, ['68c5a9b39716', 'b890630f5be5']),
 ('aspose-words-foss/Aspose.Words-FOSS-for-Python', 'README.md:625 edit 1 (enterprise_edition_naming)', 'the commercial Aspose.Words', 2, ['68c5a9b39716', 'b890630f5be5']),
]
for repo, item, text, occ, seals in lane_l:
    per_rule['R-NAMING']['n'] += 1; per_rule['R-NAMING']['agree'] += 1
    out_items.append(dict(repository=repo, lane='L', item=item, text=text,
        dropped_as='Lane L FALSE_CLAIM_FIX (enterprise_edition_naming), evidence link_target:product.enterprise SUPPORTED',
        decision='KEEP_DROPPED', evidence='corrections.json edit: replacement "... - Enterprise Edition" carries the referent; only the substitute name "the commercial" is removed (mission naming rule)',
        rule='R-NAMING', occurrences=occ, seals=seals, revision='',
        pipeline=dict(stored_disposition='evidenced Lane L edit', bc05_fails=False, bc17_unit_fails=False, bc17_item_flagged=False, decides='KEEP_DROPPED', agrees=True),
        decided_by='supervisor-worker (w/drop-inventory)', decided_at='2026-11-06'))

path = WT / 'data' / 'drop_decisions.json'
doc = json.load(open(path))
first = doc['decisions'][0]
doc['schema_version'] = 2
doc['inventory'] = dict(
    method='scripts are in the decision doc; every seal of every bundle ref on origin (bundle_store.seal_history, 59 seals: 22 Lane R across 11 repositories, 37 Lane L across 13) plus the committed candidates/ 3D .NET bundle; original README read from a pinned read-only clone at each seal revision; an item is dropped when validation.content_presence.unstated(strict=True) finds it unstated in the sealed README (per list item, table row, sentence, code block, heading, badge); deduplicated per repository by normalized text',
    seals_read=60, lane_r_seals=22, lane_l_seals=37, committed_candidates=1, lane_l_seals_with_text_removal=5,
    calibration_candidates='iteration-4/5 calibration bases are the sealed candidates themselves (registration.json facts_revision = seal revision); their mutants are not drops from a live README and carry no dispositions, so they add no items',
    distinct_items=len(out_items), raw_occurrences=sum(i['occurrences'] for i in out_items))
doc['rules'] = {k: dict(predicate=v[0], decision=v[1], note=v[2], items=per_rule[k]['n'],
                        pipeline_agrees=per_rule[k]['agree'], pipeline_disagrees=per_rule[k]['disagree'])
                for k, v in RULES.items()}
doc['pipeline_measure'] = dict(
    definition='current pipeline decides READD when BC-05 (validation/supersession.superseded_failures) fails the unit or BC-17 (parity_gate.content_losses, run against the original README at the seal revision) reports a loss matching the item, on the latest seal holding the item; otherwise it keeps the drop',
    agreement=sum(1 for i in out_items if i['pipeline']['agrees']), total=len(out_items))
seen_first = False
decisions = [first]
for i in out_items:
    if i['repository'] == first['repository'] and i['item'].startswith(first['item']):
        i['note'] = 'same item as decisions[0] (first decision); repeated here with inventory measurement'
    decisions.append(i)
doc['decisions'] = decisions
path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')

tot = Counter(i['decision'] for i in out_items)
print('items', len(out_items), tot, 'raw', sum(i['occurrences'] for i in out_items))
print('agreement', doc['pipeline_measure'])
for k in RULES:
    c = per_rule[k]
    print(f"{k:22s} {RULES[k][1]:13s} n={c['n']:3d} agree={c['agree']:3d} dis={c['disagree']:3d}", disagreements.get(k, [])[:12])
json.dump({k: v for k, v in disagreements.items()}, open(SP / 'disagreements.json', 'w'))
