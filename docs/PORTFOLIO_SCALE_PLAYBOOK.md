# Portfolio-scale candidate playbook (P1_PORTFOLIO_SCALE)

Methodology for producing a real, independently-reviewed Lane L + Lane R candidate
for one repository, calibrated for throughput across the registry (`data/registry.json`)
rather than the exhaustive single-repo depth used for the P1 mechanism proof
(`evidence/build/P1_VERTICAL_SLICE/aspose-3d-foss__Aspose.3D-FOSS-for-Python/` —
read it once as the worked example before starting; this playbook assumes you have).

## Environment constraints (checked 2026-10-21, this machine)

- **Available for real execution-based verification:** `python` (pip install the
  real PyPI package into an isolated venv under your scratchpad, exactly as the
  worked example did) and `dotnet` (10.0.401).
- **NOT available:** `java`, `node`/`npm`, `go`, `cargo`, `cmake`, `mvn`. For
  repositories on these platforms, verification is **code-reading only** — read
  the actual dispatch/registration code (format plugin lists, public API surface,
  build scripts) and cross-check it against the README's specific claims. This is
  still real verification (mission: "repository code and executable evidence take
  precedence... for factual truth" — code IS evidence, not just execution), just
  without a runtime confirmation step. Mark anything you could not establish from
  code reading alone `UNVERIFIED`, never `SUPPORTED` by assumption and never
  `CONTRADICTED` by suspicion alone.

## Per-repository steps

1. **Fetch live state.** `gh api repos/<owner>/<repo>/readme --jq '.content' | base64 -d`
   for the README; `gh api repos/<owner>/<repo>/git/trees/<default_branch>?recursive=1`
   for the file tree. Record the exact head SHA (`gh api repos/<owner>/<repo>/commits/<default_branch> --jq '{sha,date:.commit.committer.date}'`)
   and the README blob SHA in `facts.json`'s `source_revision`/`readme_blob_sha`.

2. **Read the README's own specific claims** — format support lists, API surface
   claims, installation/package claims, any existing Scope-and-Limitations-style
   section. Note which claims are concrete enough to check (a format name, a
   class/method existing, a package name/version) versus general marketing prose
   (not independently checkable, leave untouched either way).

3. **Cross-check against real source.** For format/plugin-style libraries, find
   the actual registration/dispatch point (the worked example's `IOService`
   pattern) and compare it against every concrete claim. For API/example claims,
   read the actual class/method referenced. Where Python or .NET and a quick
   install+run is cheap, do it (it catches things code-reading alone cannot,
   like the worked example's two independent OBJ-export bugs). Don't force
   execution where it isn't cheap or the toolchain isn't available.

4. **Record facts** in `evidence/build/P1_PORTFOLIO_SCALE/<owner>__<repo>/facts.json`,
   same shape as the worked example: one entry per checked claim, `disposition`
   one of `SUPPORTED`/`CONTRADICTED`/`UNVERIFIED`, `evidence` citing exact file/line
   or exact reproduction output. **Do not pad this with claims you didn't actually
   check** — a short, honest facts.json beats a long speculative one.

5. **Lane L.** If zero `CONTRADICTED` facts: the candidate is the live README
   unchanged (an empty-patch ACCEPT — idea.md's own "fast path" for an already-
   strong README; this is a legitimate, expected outcome for a well-maintained
   repository, not a failure to find something). If any `CONTRADICTED` fact
   exists: make the smallest possible precise edit per fact (see the worked
   example's 7-hunk diff for the shape — correct the specific claim, don't
   rewrite the surrounding prose), save as `lane_l_candidate.md` +
   `lane_l_candidate.diff` (only if corrected; omit the diff file for an
   empty-patch ACCEPT and say so in `lane_l_review.json` instead).

6. **Lane R.** Classify per mission §7: case (A) substantial live README
   (the common case here) or case (B) deficient/missing. For case (A), write a
   short `lane_r_plan.md` (a few sentences, not the worked example's full essay)
   stating whether Lane R converges to Lane L's output and why (per-repository
   reasoning from this repository's own facts, not copy-pasted boilerplate from
   the worked example). For case (B) — a genuinely weak or missing README — this
   is where the two lanes should actually diverge; if you hit one, say so clearly
   and produce a real from-facts composed candidate, not a converged one, and
   flag it prominently in your report (this is the falsification case the worked
   example's lane_r_plan.md explicitly asked a future run to find).

7. **Independent review.** `lane_l_review.json` and `lane_r_review.json` (or one
   combined `review.json` if the two lanes converged and the review logic is
   identical — say explicitly that it's shared, don't silently skip the R review).
   At minimum check: every edit traces to a fact, nothing outside the edit span
   changed (diff it), no UNVERIFIED fact got corrected as if CONTRADICTED. Verdict
   `ACCEPT` or `REJECT` with a reason; a `REJECT` stands unless you can point to a
   specific deterministic refutation — don't demote a real finding because it's
   inconvenient.

8. **Report back** (to the dispatching supervisor) a one-line-per-repository
   summary: repo, verdict both lanes, whether corrected or empty-patch, the single
   most important fact found (or "none, README is accurate" — that is a valid,
   useful result). Flag loudly: any case-B repository, any toolchain gap that
   blocked verification entirely, any claim you genuinely could not resolve.

## What NOT to do

- Do not fabricate execution results for an unavailable toolchain.
- Do not copy the worked example's specific OBJ-export finding or its prose into
  an unrelated repository "because the shape looks similar" — every finding must
  be this repository's own, independently derived.
- Do not mark a repository's registry entry with any write/effect authorization —
  that is explicitly out of scope here (mission §5: new findings begin read-only).
- Do not spend more than roughly 15-20 minutes of real verification effort per
  repository — an honest, narrower facts.json beats an exhaustive one if the
  portfolio-scale goal (28+ repositories) would otherwise stall on one repo.
