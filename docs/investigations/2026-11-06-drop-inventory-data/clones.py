"""Read-only pinned clones of every sealed repository at each seal revision (no push, no provider)."""
from pathlib import Path
from repo_presenter.core.git_safety.clone import pinned_read_only_clone
from repo_presenter.core.git_safety.git import run_git

SP = Path('/tmp/claude-0/-home-user/542f6e2c-a780-567b-84f4-4e5f84153686/scratchpad')
(SP / 'origs').mkdir(exist_ok=True)
pairs = [l.split() for l in (SP / 'revs.txt').read_text().splitlines() if l.strip()]
done = {}
for repo, rev in pairs:
    slug = repo.replace('/', '__')
    dest = SP / 'clones' / f'{slug}@{rev[:12]}'
    if not dest.exists():
        c = pinned_read_only_clone(f'https://github.com/{repo}.git', dest)
        if c.revision != rev:
            f = run_git(['fetch', '--depth', '1', 'origin', rev], cwd=dest, timeout=300)
            if f.returncode != 0:
                print('FETCH FAIL', repo, rev, f.stderr[:200]); continue
            co = run_git(['checkout', '-q', '--detach', rev], cwd=dest, timeout=300)
            if co.returncode != 0:
                print('CHECKOUT FAIL', repo, rev, co.stderr[:200]); continue
    head = run_git(['rev-parse', 'HEAD'], cwd=dest).stdout.strip()
    readme = dest / 'README.md'
    (SP / 'origs' / f'{slug}@{rev}.md').write_text(readme.read_text(encoding='utf-8'), encoding='utf-8')
    print('ok', repo, rev[:8], head[:8])
