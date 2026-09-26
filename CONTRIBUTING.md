# Contributing to Gyme

Thanks for considering a contribution. Gyme is a small, focused project — the
maintainers value correct, conservative changes that fit the existing patterns.

## Development setup

See [README → Quick start](https://github.com/Rastin-Amani/Gyme#quick-start-development)
for the full setup. In short:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r app/requirements.txt
npm install
npm run build            # or `npm run dev` for watch mode
uvicorn app.main:app --reload
```

You need a running PocketBase instance (`PB_URL`); hostname-based tenancy means
each environment resolves gyms by `Host` header (see
[docs/02-getting-started.md](docs/02-getting-started.md)).

## Before you open a PR

```bash
make test        # 54-test suite: i18n + security regression + known-issue fixes
ruff check .
black .
```

CI runs `ruff check .`, `black --check .`, and `pytest -q`. The test suite runs
against the local app only — no network calls.

## Code conventions

- Keep routes thin: business logic and PocketBase queries live in
  `app/services/`.
- UI strings are Persian msgids behind gettext: `_("…")` in Jinja templates
  (`{{ _("...") }}`) and Python. Update catalogs with the i18n Makefile targets
  (`make i18n-extract`, `make i18n-update`, `make i18n-compile`).
- Minimum Python is 3.11; type hints are welcome on new code.
- Keep server-rendered HTML + HTMX interaction style (partial swaps, toast
  headers via `app/utils.py`); no new front-end framework.
- Docs: user-facing behavioral changes should update
  [docs/07-troubleshooting-known-issues.md](docs/07-troubleshooting-known-issues.md)
  (and the README "Known limitations" when relevant).

## Submitting changes

1. Fork the repo (or use a branch), keep commits small and atomic, and use
   clear commit messages (e.g. `fix(auth): …`, `feat(plans): …`,
   `docs(security): …`, `build(ci): …`, `chore(version): …`).
2. Open a PR describing the problem, the change, and how you verified it
   (tests + manual run).
3. **AI assistance:** it's fine to use AI tools while developing, but if a
   non-trivial part of the change was AI-generated or AI-assisted, say so in
   the PR description. This keeps the contribution trail honest.

## Reporting security issues

Do **not** file a public issue for security problems. See
[SECURITY.md](SECURITY.md) for the disclosure process (private vulnerability
reporting is preferred).

## Code of conduct

Be respectful and constructive. This project has no formal CoC file yet — the
expectation is simply that communication stays professional.