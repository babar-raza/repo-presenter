# CLAUDE.md — Repository Presenter

**STOP — before anything else, read `docs/RULINGS.md` in full.** It holds every binding owner ruling (R1–R35) and the
pre-work checklist; a SessionStart hook prints it into every new session, and `tests/test_rulings_in_focus.py` fails
CI if this pointer or any ruling disappears. Then read `AGENTS.md`.

Non-negotiable summary (details in `docs/RULINGS.md`):
- Judge every action by **certified candidates produced** (≥ 25 per lane), never by machinery built (R27, R31).
- **Architecture freeze**: fixes to existing components only; the PHP extractor is the one sanctioned exception (R27, R29).
- **Never lose a seal** on a version bump; re-certify (R10). **Never drop live README content** without a recorded decision (R14).
- **No attribution or provenance wording** in any public README (R9).
- **No upstream push** before every candidate of both lanes passes; draft PRs only, allowlist (R15, R3, R22).
- **Decide, don't ask** the owner; report results first; when stuck, change approach (R11, R12).
