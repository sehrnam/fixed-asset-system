"""
verify_frontend_deploy.py - Static verification of the frontend deploy changes.

Checks that the VITE_API_BASE_URL migration was applied consistently:
  - config.ts exports API_BASE and reads VITE_API_BASE_URL
  - every api.ts imports API_BASE (no local const)
  - exportUtils.ts prepends API_BASE
  - downloadBlob callers use short paths
  - vite.config.ts proxy is intact
  - frontend/.env.example exists
  - backend config has cookie_samesite
  - npm run build succeeds

Run from the project root:
    python verify_frontend_deploy.py

Exit code 0 if all checks pass, 1 otherwise.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
BACKEND = ROOT / "backend"


class Harness:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.section = ""
        self.failures: list[str] = []

    def start(self, name: str) -> None:
        self.section = name
        print()
        print("-" * 74)
        print(f"  {name}")
        print("-" * 74)

    def check(self, label: str, cond: bool, detail: str = "") -> None:
        if cond:
            self.passed += 1
            print(f"  [PASS] {label}")
        else:
            self.failed += 1
            self.failures.append(f"{self.section} :: {label} {detail}".strip())
            print(f"  [FAIL] {label}  {detail}")

    def summary(self) -> int:
        total = self.passed + self.failed
        print()
        print("=" * 74)
        print(f"  TOTAL: {total}   PASSED: {self.passed}   FAILED: {self.failed}")
        print("=" * 74)
        if self.failures:
            print("\nFailures:")
            for f in self.failures:
                print(f"  - {f}")
        return 0 if self.failed == 0 else 1


def read(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def has(text: str, needle: str) -> bool:
    return needle in text


def matches(text: str, pattern: str) -> bool:
    return re.search(pattern, text) is not None


# ---------------------------------------------------------------- checks

def check_root(h: Harness) -> None:
    h.start("0. Project structure")
    h.check("Project root detected", (ROOT / "frontend").is_dir() and (ROOT / "backend").is_dir(),
            f"(root={ROOT})")
    h.check("frontend/src exists", (FRONTEND / "src").is_dir())
    h.check("backend/app exists", (BACKEND / "app").is_dir())


def check_config_ts(h: Harness) -> None:
    h.start("1. frontend/src/config.ts")
    p = FRONTEND / "src" / "config.ts"
    h.check("File exists", p.exists(), f"({p})")
    txt = read(p)

    h.check("Exports CURRENCY", matches(txt, r"export\s+const\s+CURRENCY\b"))
    h.check("Exports API_BASE", matches(txt, r"export\s+const\s+API_BASE\b"))
    h.check("Reads VITE_API_BASE_URL",
            has(txt, "import.meta.env.VITE_API_BASE_URL"))
    h.check("Strips trailing slashes",
            matches(txt, r"replace\(\s*/\\\+/"))
    h.check("Falls back to /api when unset",
            matches(txt, r"trimmed\s*\?\s*`\$\{trimmed\}/api`\s*:\s*[\"']/api[\"']"))


API_FILES = [
    ("features/assets/api.ts",         "../../config"),
    ("features/workbook/api.ts",       "../../config"),
    ("features/depreciation/api.ts",   "../../config"),
    ("features/disposals/api.ts",      "../../config"),
    ("features/reports/api.ts",        "../../config"),
    ("features/dashboard/api.ts",      "../../config"),
    ("services/api.ts",                "../config"),
]


def check_api_files(h: Harness) -> None:
    h.start("2. api.ts files - no local const, import from config")
    for rel, import_path in API_FILES:
        p = FRONTEND / "src" / rel
        name = rel

        if not p.exists():
            h.check(f"{name} exists", False, f"({p})")
            continue

        txt = read(p)

        # Must NOT declare its own API_BASE
        has_local = matches(txt, r"const\s+API_BASE\s*=\s*[\"']/api[\"']")
        h.check(f"{name} - no local `const API_BASE = \"/api\"`", not has_local)

        # Must import API_BASE from the expected relative path
        escaped = re.escape(import_path)
        import_re = rf"import\s*\{{\s*API_BASE\s*\}}\s*from\s*[\"']{escaped}[\"']"
        h.check(f"{name} - imports API_BASE from {import_path!r}",
                matches(txt, import_re))

        # Still uses API_BASE somewhere in the file
        h.check(f"{name} - references API_BASE in body",
                has(txt, "API_BASE"))


def check_settings_page(h: Harness) -> None:
    h.start("3. features/settings/SettingsPage.tsx")
    p = FRONTEND / "src" / "features" / "settings" / "SettingsPage.tsx"
    h.check("File exists", p.exists(), f"({p})")
    txt = read(p)

    h.check("No local `const API_BASE = \"/api\"`",
            not matches(txt, r"const\s+API_BASE\s*=\s*[\"']/api[\"']"))
    h.check("Imports API_BASE from ../../config",
            matches(txt, r"import\s*\{\s*API_BASE\s*\}\s*from\s*[\"']\.\./\.\./config[\"']"))
    h.check("References API_BASE in body", has(txt, "API_BASE"))


def check_export_utils(h: Harness) -> None:
    h.start("4. features/reports/exportUtils.ts")
    p = FRONTEND / "src" / "features" / "reports" / "exportUtils.ts"
    h.check("File exists", p.exists(), f"({p})")
    txt = read(p)

    h.check("Imports API_BASE from ../../config",
            matches(txt, r"import\s*\{\s*API_BASE\s*\}\s*from\s*[\"']\.\./\.\./config[\"']"))
    h.check("Exports downloadBlob",
            matches(txt, r"export\s+async\s+function\s+downloadBlob\b"))
    h.check("Exports safeFilename",
            matches(txt, r"export\s+function\s+safeFilename\b"))
    h.check("Prepends API_BASE to relative paths",
            matches(txt, r"`\$\{API_BASE\}\$\{path\}`"))
    h.check("Accepts absolute URLs (startsWith http)",
            has(txt, "path.startsWith(\"http\")") or has(txt, "path.startsWith('http')"))
    h.check("No hard-coded `/api` prefix in download URLs",
            not matches(txt, r"[\"']/api/exports/"))


def check_downloadblob_callers(h: Harness) -> None:
    h.start("5. downloadBlob callers - short paths")

    # workbook/api.ts - exportSheetXlsx
    p1 = FRONTEND / "src" / "features" / "workbook" / "api.ts"
    t1 = read(p1)
    h.check("workbook/api.ts exists", p1.exists())
    # Uses /exports/sheets/... NOT /api/exports/... NOT ${API_BASE}/exports/...
    h.check("workbook/api.ts uses short /exports/sheets/ path",
            matches(t1, r"downloadBlob\(\s*\n?\s*`/exports/sheets/"))
    h.check("workbook/api.ts does NOT use ${API_BASE} in download path",
            not matches(t1, r"downloadBlob\(\s*\n?\s*`\$\{API_BASE\}/exports/"))

    # ReportsPage.tsx - onExport
    p2 = FRONTEND / "src" / "features" / "reports" / "ReportsPage.tsx"
    t2 = read(p2)
    h.check("ReportsPage.tsx exists", p2.exists())
    h.check("ReportsPage.tsx uses short /exports/reports/ path",
            matches(t2, r"`/exports/reports/\$\{selected\}/xlsx`"))
    h.check("ReportsPage.tsx uses short /exports/reports/ path (pdf)",
            matches(t2, r"`/exports/reports/\$\{selected\}/pdf`"))
    h.check("ReportsPage.tsx does NOT use /api/exports/",
            not matches(t2, r"[\"']/api/exports/"))


def check_frontend_env_example(h: Harness) -> None:
    h.start("6. frontend/.env.example")
    p = FRONTEND / ".env.example"
    h.check("File exists", p.exists(), f"({p})")
    txt = read(p)
    h.check("Mentions VITE_API_BASE_URL", has(txt, "VITE_API_BASE_URL"))
    h.check("Explains local dev behavior",
            has(txt, "proxy") or has(txt, "proxies"))


def check_vite_config(h: Harness) -> None:
    h.start("7. frontend/vite.config.ts - proxy intact")
    p = FRONTEND / "vite.config.ts"
    h.check("File exists", p.exists())
    txt = read(p)

    h.check("Proxy for /api present",
            matches(txt, r"[\"']/api[\"']\s*:"))
    h.check("Proxy targets localhost:8000",
            has(txt, "http://localhost:8000"))
    h.check("changeOrigin enabled", has(txt, "changeOrigin"))


def check_backend_config(h: Harness) -> None:
    h.start("8. backend config - cookie_samesite available")
    p = BACKEND / "app" / "config.py"
    h.check("File exists", p.exists())
    txt = read(p)

    h.check("cookie_samesite field present",
            matches(txt, r"cookie_samesite\s*:\s*str"))
    h.check("cookie_secure field present",
            matches(txt, r"cookie_secure\s*:\s*bool"))
    h.check("auto_bootstrap field present",
            matches(txt, r"auto_bootstrap\s*:\s*bool"))


def check_no_stale_hardcoded_paths(h: Harness) -> None:
    h.start("9. No stale hard-coded /api paths in source")
    bad_files: list[str] = []

    src = FRONTEND / "src"
    if src.exists():
        for p in src.rglob("*.ts*"):
            if p.name == "config.ts":
                continue
            txt = read(p)
            # Any occurrence of a string literal exactly "/api" that would
            # be the old local const pattern
            if matches(txt, r"const\s+API_BASE\s*=\s*[\"']/api[\"']"):
                bad_files.append(str(p.relative_to(FRONTEND)))

    h.check("No file declares local `const API_BASE = \"/api\"`",
            len(bad_files) == 0,
            f"(found in: {bad_files})" if bad_files else "")


def check_build(h: Harness) -> None:
    h.start("10. npm run build (TypeScript + Vite)")
    if not (FRONTEND / "package.json").exists():
        h.check("package.json present", False)
        return

    try:
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=str(FRONTEND),
            capture_output=True,
            text=True,
            shell=True,
            timeout=180,
        )
    except Exception as e:
        h.check("Build ran", False, f"(exception: {e})")
        return

    ok = result.returncode == 0
    h.check("Build exited 0", ok, f"(exit={result.returncode})")

    if not ok:
        # Print a short tail of stderr/stdout for debugging
        tail = ((result.stdout or "") + "\n" + (result.stderr or "")).strip().splitlines()[-20:]
        print("\n  ---- build output (tail) ----")
        for line in tail:
            print(f"    {line}")
        print("  -----------------------------")


# ---------------------------------------------------------------- main

def main() -> int:
    h = Harness()
    print("=" * 74)
    print("  Frontend deploy verification")
    print(f"  Project root: {ROOT}")
    print("=" * 74)

    check_root(h)
    check_config_ts(h)
    check_api_files(h)
    check_settings_page(h)
    check_export_utils(h)
    check_downloadblob_callers(h)
    check_frontend_env_example(h)
    check_vite_config(h)
    check_backend_config(h)
    check_no_stale_hardcoded_paths(h)
    check_build(h)

    return h.summary()


if __name__ == "__main__":
    sys.exit(main())