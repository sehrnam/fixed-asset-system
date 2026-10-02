# Fixed Asset Accounting Workbook & Management System

A professional fixed-asset accounting application with a spreadsheet-like
workbook workspace. Authoritative accounting calculations are performed
**server-side**; the browser is never trusted with official accounting totals.

> **Status: project / demo build.** This is a secure-by-design prototype,
> not a bank-certified production system. See `DEPLOYMENT.md` for the
> production checklist and additional assessments required before
> institutional adoption.

---

## Features

### Accounting
- **Asset Register** — create, edit, search, filter, lifecycle states
  (`ACTIVE` / `DISPOSED` / `RETIRED`), auto-generated asset codes
- **Depreciation Engine** — straight-line and reducing-balance, fully
  server-authoritative with a centralized policy layer
- **Disposals** — request → approve → finalize, maker-checker enforcement,
  gain/loss computed by the engine from NBV at disposal date
- **Journals** — depreciation journal preparation (prepare/export only;
  no external ledger posting)
- **Reports** — asset register, depreciation schedule, asset movement,
  disposal register
- **Period Locking** — `OPEN` / `LOCKED` state; writes to locked periods rejected

### Workbook
- Named sheets with a familiar spreadsheet-like interface
- Editable cell grid (26 columns × 50 rows)
- **Safe formula engine** — `+ - * / ( )`, `SUM`, `MIN`, `MAX`, `ROUND`,
  cell refs (`A1`, `AA12`), ranges (`A1:B10`), percentage arithmetic
- No `eval` / `exec` / macros / external workbook links
- System sheets (Asset Register, Depreciation, Disposal) are read-only
  views backed by live accounting data

### Security
- Argon2id password hashing
- HTTP-only cookie sessions (no localStorage tokens)
- Role-based access control (RBAC) with backend enforcement
- Rate-limited login
- Security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`)
- Centralized error handling (no stack traces to client)
- Full audit trail for every state-changing action

### Data
- XLSX export (sheets + reports)
- PDF export (reports)
- XLSX import — creates a **new** user sheet; never overwrites
  authoritative records
- Deterministic demo dataset for demonstration and testing

---

## Architecture
