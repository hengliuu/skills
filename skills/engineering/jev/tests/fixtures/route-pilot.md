# Pilot plan (synthetic tasks, expected answers known)

| # | Task | Depends on | Files it writes | Role | Effort | Check |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Settings parser keeps unknown values | none | `<module>/settings/**` | worker | medium | the settings unit tests |
| 2 | Adapter for a second payment provider | none | `<module>/payments/**`, `tests/payments/**` | worker | high | the adapter's tests |
| 3 | Settings screen offers the new provider | 1, 2 | `web/src/features/settings/**` | worker | high | frontend tests and the visual gate |
| 4 | Docs page for the new option | 3 | `docs/**` | chore | medium | the docs lint |
| 5 | Review before merge | 1, 2, 3, 4 | none (read only) | reviewer | high | findings list |
| 6 | Bump plugin version 0.2.0 to 0.3.0 in plugin.json | none | `plugin.json` | chore | low | json.tool |
| 7 | Find why exports sometimes produce empty files on Windows | none | none | designer | medium | a written root cause with a repro |
| 8 | Write the architecture spec for multi-tenant billing | none | `docs/specs/**` | designer | high | spec reviewed by the human |
| 9 | Decide the pricing page headline and the free tier wording | none | `docs/product/**` | product | medium | recommendation with reason |
| 10 | Rename getUserById to findUser across the service, as listed in the review | none | `src/**` | chore | medium | unit tests |
| 11 | Animate the sidebar collapse with reduced-motion support per the motion spec | 8 | `web/src/layout/**` | worker | high | visual gate at phone width |
| 12 | Migration that merges duplicate customer rows in the ledger | none | `migrations/**`, `src/ledger/**` | worker | high | migration test on a prod snapshot |
