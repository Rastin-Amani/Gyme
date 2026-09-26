# Security Policy

Gyme is a self-hosted, multi-tenant gym management platform. This policy describes
how security issues are reported, assessed, and disclosed.

## Supported versions

| Version | Supported |
| --- | --- |
| latest release | ✅ |
| older releases | ❌ — upgrade to the latest release |

Only the most recent tagged release receives security fixes.

## Reporting a vulnerability

We ask that you **do not open a public issue** for security findings.

Preferred channels, in order:

1. **GitHub private vulnerability reporting** (recommended) — use the "Report a
   vulnerability" button on the repository's Security tab. If it is not enabled
   yet, enable it in *Settings → Code security and analysis → Private
   vulnerability reporting* and use this option for future reports.
2. If private reporting is unavailable, open a **draft GitHub Security Advisory**
   from the Security tab instead (no public disclosure until triaged).

Please include in the report:

- Affected version(s) and commit/tag if known
- A minimal reproduction (steps, configuration, endpoints involved)
- Impact and proposed severity, if you have one

## What is in scope

- The FastAPI application: auth/session handling, tenant resolution, route and
  service layer logic under `app/`
- Docker image build and runtime defaults (`Dockerfile`)
- Default configuration and environment-variable handling (`PB_URL`, `ENV`,
  `ALLOWED_HOSTS`)

## What is out of scope

- **PocketBase itself** — report PocketBase vulnerabilities to its own project.
  Gyme is a client of it and does not control its behavior.
- Third-party Python/Node dependencies — report upstream.
- Misconfigurations specific to a deployment (choose strong admin passwords,
  use HTTPS, set `ENV=production` and a private `PB_URL`).

## Process

1. The maintainer triages within a reasonable time and confirms receipt.
2. A fix is prepared, tested against the regression suite, and released as a
   patch version.
3. After the fix is released (or after a reasonable disclosure deadline where a
   fix cannot be produced), the issue is disclosed in a GitHub Security Advisory
   or in the release notes.

## Known limitations

Current known limitations and their status are tracked in
[`SECURITY_REPORT.md`](SECURITY_REPORT.md) and
[`docs/07-troubleshooting-known-issues.md`](docs/07-troubleshooting-known-issues.md).
Examples: login is rate-limited (5 attempts / 5 min per IP+identity+tenant) but
password change is not; there is no forgot-password flow.

## Acknowledgment

We thank contributors who report issues responsibly. Reported, verified
vulnerabilities are acknowledged in the release notes that fix them.