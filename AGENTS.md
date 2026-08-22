# Data Studio Development Rules

These rules apply to this repository.

## Scope and architecture

- This repository owns Data Studio PawApp features 1–6. Product behavior belongs here, not in generated copies under `zhiyun-ai-platform/apps/qwenpaw-embedded/runtime/pawapps`.
- QwenPaw 2.1.0 is the supported runtime. Preserve the `plugin.json` manifest and Data Core integration contract.
- Read `docs/PRD.md` and `docs/FEATURE_PROGRESS.md` before changing product behavior.

## Branch and delivery policy

- Never commit directly to `main`, force-push a shared branch, or merge automatically.
- Use one issue, one task branch, and one pull request. For multi-repository work, use the main-platform issue number and identical branch name in every involved repository.
- Complete and test this PawApp PR before the main platform updates its full-SHA lock. Only a formal merged commit SHA may be locked.
- Do not claim a capability is available without a real-data UI/backend/Agent path and reproducible acceptance evidence. Simulated data must remain optional and clearly labeled.

## Validation and safety

- Run `python scripts/verify_release.py` before delivery; keep the Windows and Linux GitHub gate passing.
- Add focused tests for changed backend, frontend contracts, Agent tools, persistence, empty/error states, and migrations.
- Preserve user data and rollback paths. Never commit secrets, customer data, runtime caches, or generated installations.
- Every PR must report its issue, design, exact tests, Windows/Linux impact, limitations, data/security risks, and rollback.
