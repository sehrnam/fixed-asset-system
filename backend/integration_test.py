"""
integration_test.py — Comprehensive end-to-end test.

Exercises EVERY endpoint, EVERY role, and EVERY major business rule
in the Fixed Asset Accounting Workbook system.

Run from backend/ with the venv active:
    python integration_test.py

Exit code is 0 if all checks pass, 1 otherwise.
Uses a temporary database so it will NOT touch your dev data.
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

# --- Isolated DB + env BEFORE importing any app modules ---
_TMP_DB = Path(tempfile.gettempdir()) / "fas_integration_test.db"
if _TMP_DB.exists():
    _TMP_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB}"
os.environ["SECRET_KEY"] = "integration-test-secret-not-for-production"
os.environ["LOGIN_RATE_LIMIT_ATTEMPTS"] = "10000"

from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session  # noqa: E402

from app.database import engine, init_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.user import User  # noqa: E402
from app.security.passwords import hash_password  # noqa: E402
from app.security.permissions import Role  # noqa: E402


# ============================================================
# Harness
# ============================================================

class Harness:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.section = ""
        self.failures: list[str] = []

    def start(self, name: str) -> None:
        self.section = name
        print()
        print("-" * 72)
        print(f"  {name}")
        print("-" * 72)

    def check(self, label: str, condition: bool, detail: str = "") -> None:
        if condition:
            self.passed += 1
            print(f"  [PASS] {label}")
        else:
            self.failed += 1
            self.failures.append(f"{self.section} :: {label} {detail}")
            print(f"  [FAIL] {label}  {detail}")

    def eq(self, label: str, actual, expected) -> None:
        self.check(label, actual == expected, f"(got {actual!r}, expected {expected!r})")

    def in_(self, label: str, container, member) -> None:
        self.check(label, member in container, f"({member!r} not in {container!r})")

    def summary(self) -> int:
        total = self.passed + self.failed
        print()
        print("=" * 72)
        print(f"  TOTAL: {total}   PASSED: {self.passed}   FAILED: {self.failed}")
        print("=" * 72)
        if self.failures:
            print("\nFailures:")
            for f in self.failures:
                print(f"  - {f}")
        return 0 if self.failed == 0 else 1


# ============================================================
# Setup
# ============================================================

def seed_users() -> None:
    init_db()
    specs = [
        ("admin", "admin@example.com", "Admin User", "Admin123!", Role.ADMIN.value),
        ("accounting", "accounting@example.com", "Accounting User", "Account123!", Role.ACCOUNTING.value),
        ("approver", "approver@example.com", "Approver User", "Approve123!", Role.APPROVER.value),
        ("auditor", "auditor@example.com", "Auditor User", "Auditor123!", Role.AUDITOR.value),
    ]
    with Session(engine) as db:
        for username, email, name, pw, role in specs:
            db.add(User(
                username=username, email=email, full_name=name,
                password_hash=hash_password(pw), role=role, is_active=True,
            ))
        db.commit()


def mkclient(app) -> TestClient:
    return TestClient(app)


def login(c: TestClient, username: str, password: str) -> bool:
    r = c.post("/api/auth/login", json={"username": username, "password": password})
    return r.status_code == 200


# ============================================================
# Main
# ============================================================

def main() -> int:
    h = Harness()
    seed_users()
    app = create_app()

    admin = mkclient(app)
    accounting = mkclient(app)
    approver = mkclient(app)
    auditor = mkclient(app)
    anon = mkclient(app)

    # --------------------------------------------------------------
    h.start("1. Health & security headers")
    r = anon.get("/api/health")
    h.eq("GET /api/health → 200", r.status_code, 200)
    h.eq("body.status == 'ok'", r.json().get("status"), "ok")
    h.eq("X-Content-Type-Options header", r.headers.get("X-Content-Type-Options"), "nosniff")
    h.eq("X-Frame-Options header", r.headers.get("X-Frame-Options"), "DENY")
    h.eq("Referrer-Policy header", r.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")

    # --------------------------------------------------------------
    h.start("2. Authentication")
    r = anon.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    h.eq("Wrong password → 401", r.status_code, 401)
    r = anon.post("/api/auth/login", json={"username": "ghost", "password": "x"})
    h.eq("Unknown user → 401", r.status_code, 401)
    r = anon.get("/api/auth/me")
    h.eq("Anonymous /me → 401", r.status_code, 401)

    # Fake cookie
    fake = mkclient(app)
    fake.cookies.set("fas_session", "not-a-real-token")
    r = fake.get("/api/auth/me")
    h.eq("Bogus session cookie → 401", r.status_code, 401)

    h.check("Login admin", login(admin, "admin", "Admin123!"))
    h.check("Login accounting", login(accounting, "accounting", "Account123!"))
    h.check("Login approver", login(approver, "approver", "Approve123!"))
    h.check("Login auditor", login(auditor, "auditor", "Auditor123!"))

    r = admin.get("/api/auth/me")
    h.eq("/me after login → 200", r.status_code, 200)
    h.eq("/me returns admin role", r.json().get("role"), "admin")

    # --------------------------------------------------------------
    h.start("3. RBAC — Categories")
    h.eq("Anonymous cannot list categories", anon.get("/api/categories").status_code, 401)
    h.eq("Auditor cannot create category", auditor.post("/api/categories", json={"name": "X"}).status_code, 403)

    r = accounting.post("/api/categories", json={"name": "Vehicles", "description": "Fleet"})
    h.eq("Accounting can create category (201)", r.status_code, 201)
    cat_vehicles = r.json()

    r = accounting.post("/api/categories", json={"name": "Vehicles"})
    h.eq("Duplicate category name (409)", r.status_code, 409)

    cat_office = accounting.post("/api/categories", json={"name": "Office Equipment"}).json()
    cat_machinery = accounting.post("/api/categories", json={"name": "Machinery"}).json()

    r = auditor.get("/api/categories")
    h.eq("Auditor can list categories (200)", r.status_code, 200)
    h.eq("Three categories exist", len(r.json()), 3)

    r = auditor.get(f"/api/categories/{cat_vehicles['id']}")
    h.eq("Auditor can get category (200)", r.status_code, 200)
    h.eq("Category name matches", r.json()["name"], "Vehicles")

    r = accounting.patch(f"/api/categories/{cat_vehicles['id']}", json={"description": "Updated"})
    h.eq("Accounting can update category (200)", r.status_code, 200)

    # --------------------------------------------------------------
    h.start("4. RBAC — Assets")
    h.eq("Auditor cannot create asset", auditor.post("/api/assets", json={}).status_code, 403)

    r = accounting.post("/api/assets", json={
        "name": "Test Vehicle",
        "category_id": cat_vehicles["id"],
        "cost": 100000.0,
        "acquisition_date": "2024-01-15T00:00:00Z",
        "useful_life_years": 5,
        "depreciation_method": "straight_line",
        "residual_value": 10000.0,
    })
    h.eq("Accounting can create SL asset (201)", r.status_code, 201)
    asset1 = r.json()
    h.eq("Auto-code FA-00001", asset1["asset_code"], "FA-00001")
    h.eq("Status defaults to ACTIVE", asset1["status"], "ACTIVE")
    h.eq("Category name resolved", asset1["category_name"], "Vehicles")

    # Validation cases
    def mk_asset(**over):
        base = {
            "name": "X", "category_id": cat_vehicles["id"],
            "cost": 1000.0, "acquisition_date": "2024-01-15T00:00:00Z",
            "useful_life_years": 5, "depreciation_method": "straight_line",
            "residual_value": 0.0,
        }
        base.update(over)
        return base

    h.check("Cost = 0 rejected",
            accounting.post("/api/assets", json=mk_asset(cost=0)).status_code in (400, 422))
    h.eq("Residual ≥ cost rejected (400)",
         accounting.post("/api/assets", json=mk_asset(cost=1000, residual_value=1000)).status_code, 400)
    h.eq("RB without rate rejected (400)",
         accounting.post("/api/assets", json=mk_asset(depreciation_method="reducing_balance")).status_code, 400)
    h.eq("Future acquisition date rejected (400)",
         accounting.post("/api/assets", json=mk_asset(
             acquisition_date=(datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
         )).status_code, 400)
    h.eq("Non-existent category rejected (400)",
         accounting.post("/api/assets", json=mk_asset(category_id=99999)).status_code, 400)

    # Explicit code
    r = accounting.post("/api/assets", json=mk_asset(
        name="Custom Coded", category_id=cat_office["id"], asset_code="FA-CUSTOM-1"))
    h.eq("Explicit asset code accepted (201)", r.status_code, 201)
    h.eq("Custom code preserved", r.json()["asset_code"], "FA-CUSTOM-1")

    # RB asset
    r = accounting.post("/api/assets", json={
        "name": "RB Printer", "category_id": cat_office["id"],
        "cost": 50000, "acquisition_date": "2024-06-01T00:00:00Z",
        "useful_life_years": 5, "depreciation_method": "reducing_balance",
        "residual_value": 1000, "rate": 20.0,
    })
    h.eq("RB asset with rate (201)", r.status_code, 201)
    asset2 = r.json()

    # List / search / filter
    r = accounting.get("/api/assets")
    h.eq("List assets (200)", r.status_code, 200)
    h.check("At least 3 assets", len(r.json()) >= 3)

    r = accounting.get("/api/assets?search=vehicle")
    h.check("Search by name works", len(r.json()) >= 1)

    r = accounting.get(f"/api/assets?category_id={cat_office['id']}")
    h.check("Filter by category works", len(r.json()) >= 1)

    r = accounting.get("/api/assets?status=ACTIVE")
    h.check("Filter by status works", len(r.json()) >= 1)

    # Update
    r = accounting.patch(f"/api/assets/{asset1['id']}", json={"name": "Renamed Asset"})
    h.eq("Update asset name (200)", r.status_code, 200)
    h.eq("Name updated", r.json()["name"], "Renamed Asset")

    r = accounting.patch(f"/api/assets/{asset1['id']}", json={"residual_value": 999999})
    h.eq("Invalid residual update rejected (400)", r.status_code, 400)

    # --------------------------------------------------------------
    h.start("5. Workbook — provisioning & sheet operations")
    r = admin.get("/api/workbooks/default")
    h.eq("Default workbook provisioned (200)", r.status_code, 200)
    wb = r.json()
    h.eq("Workbook has 4 sheets", len(wb["sheets"]), 4)
    names = [s["name"] for s in wb["sheets"]]
    for n in ("Asset Register", "Depreciation", "Disposal", "Sheet 4"):
        h.in_(f"Contains {n}", names, n)

    user_sheet = next(s for s in wb["sheets"] if s["kind"] == "USER")
    system_sheet = next(s for s in wb["sheets"] if s["kind"] == "SYSTEM")

    r = admin.post(f"/api/workbooks/{wb['id']}/sheets", json={"name": "Analysis"})
    h.eq("Create user sheet (201)", r.status_code, 201)
    new_sheet = r.json()

    h.eq("Case/whitespace-insensitive uniqueness (409)",
         admin.post(f"/api/workbooks/{wb['id']}/sheets", json={"name": "  ANALYSIS  "}).status_code, 409)

    h.eq("Rename user sheet (200)",
         admin.patch(f"/api/sheets/{new_sheet['id']}", json={"name": "Renamed Sheet"}).status_code, 200)

    h.eq("Cannot rename system sheet (400)",
         admin.patch(f"/api/sheets/{system_sheet['id']}", json={"name": "Hacked"}).status_code, 400)

    h.eq("Cannot delete system sheet (400)",
         admin.delete(f"/api/sheets/{system_sheet['id']}").status_code, 400)

    r = admin.post(f"/api/sheets/{new_sheet['id']}/duplicate", json={"new_name": None})
    h.eq("Duplicate user sheet (201)", r.status_code, 201)
    dup_sheet = r.json()

    h.eq("Delete user sheet (204)", admin.delete(f"/api/sheets/{dup_sheet['id']}").status_code, 204)

    # Reorder
    ids = [s["id"] for s in admin.get("/api/workbooks/default").json()["sheets"]]
    reversed_ids = list(reversed(ids))
    r = admin.post(f"/api/workbooks/{wb['id']}/sheets/reorder", json={"sheet_ids": reversed_ids})
    h.eq("Reorder sheets (200)", r.status_code, 200)
    new_order = [s["id"] for s in admin.get("/api/workbooks/default").json()["sheets"]]
    h.eq("Order reversed", new_order, reversed_ids)
    # restore
    admin.post(f"/api/workbooks/{wb['id']}/sheets/reorder", json={"sheet_ids": ids})

    # --------------------------------------------------------------
    h.start("6. Workbook — cells & formulas")
    r = admin.patch(f"/api/sheets/{user_sheet['id']}/cells", json={
        "cells": [
            {"row": 1, "col": 1, "raw": "100"},
            {"row": 2, "col": 1, "raw": "250"},
            {"row": 3, "col": 1, "raw": "=A1+A2"},
            {"row": 4, "col": 1, "raw": "=SUM(A1:A2)"},
            {"row": 5, "col": 1, "raw": "=ROUND(3.14159, 2)"},
            {"row": 6, "col": 1, "raw": "=A1*20%"},
            {"row": 7, "col": 1, "raw": "=MAX(A1:A2)"},
            {"row": 8, "col": 1, "raw": "=MIN(A1:A2)"},
        ]
    })
    h.eq("Batch write cells (200)", r.status_code, 200)
    cells = {(c["row"], c["col"]): c for c in r.json()["grid"]["cells"]}
    h.eq("A1 = 100", cells[(1, 1)]["computed"], "100")
    h.eq("A3 = 350 (+)", cells[(3, 1)]["computed"], "350")
    h.eq("A4 = 350 (SUM)", cells[(4, 1)]["computed"], "350")
    h.eq("A5 = 3.14 (ROUND)", cells[(5, 1)]["computed"], "3.14")
    h.eq("A6 = 20 (percent)", cells[(6, 1)]["computed"], "20")
    h.eq("A7 = 250 (MAX)", cells[(7, 1)]["computed"], "250")
    h.eq("A8 = 100 (MIN)", cells[(8, 1)]["computed"], "100")

    # Errors
    r = admin.patch(f"/api/sheets/{user_sheet['id']}/cells", json={
        "cells": [{"row": 10, "col": 1, "raw": "=1/0"}]
    })
    cells = {(c["row"], c["col"]): c for c in r.json()["grid"]["cells"]}
    h.check("Division by zero → error", cells[(10, 1)]["error"] is not None)

    r = admin.patch(f"/api/sheets/{user_sheet['id']}/cells", json={
        "cells": [
            {"row": 11, "col": 1, "raw": "=A12"},
            {"row": 12, "col": 1, "raw": "=A11"},
        ]
    })
    cells = {(c["row"], c["col"]): c for c in r.json()["grid"]["cells"]}
    h.check("Circular ref detected", cells[(11, 1)]["error"] is not None or cells[(12, 1)]["error"] is not None)

    h.eq("Cannot write to system sheet (400)",
         admin.patch(f"/api/sheets/{system_sheet['id']}/cells", json={
             "cells": [{"row": 1, "col": 1, "raw": "x"}]
         }).status_code, 400)

    # --------------------------------------------------------------
    h.start("7. Depreciation engine")
    h.eq("Auditor cannot run dep (403)",
         auditor.post("/api/depreciation/run", json={"through_period": "2024"}).status_code, 403)

    r = accounting.post("/api/depreciation/run", json={"through_period": "2024", "asset_ids": None})
    h.eq("Accounting can run dep (200)", r.status_code, 200)
    h.check("Assets processed ≥ 3", r.json()["assets_processed"] >= 3)

    r = accounting.get(f"/api/depreciation/assets/{asset1['id']}")
    h.eq("Get schedule for asset (200)", r.status_code, 200)
    sched = r.json()
    h.check("Schedule has ≥ 1 record", len(sched) >= 1)
    rec = sched[0]
    h.eq("SL 2024 dep = 18,000", rec["depreciation"], 18000.0)
    h.eq("SL 2024 closing NBV = 82,000", rec["closing_nbv"], 82000.0)

    r = accounting.get("/api/depreciation/periods/2024")
    h.eq("Period summary (200)", r.status_code, 200)
    h.check("Summary total > 0", r.json()["total_depreciation"] > 0)

    # --------------------------------------------------------------
    h.start("8. Disposals")
    h.eq("Auditor cannot request disposal (403)",
         auditor.post("/api/disposals", json={
             "asset_id": asset2["id"],
             "disposal_date": "2024-09-15T00:00:00Z",
             "proceeds": 45000.0,
         }).status_code, 403)

    r = accounting.post("/api/disposals", json={
        "asset_id": asset2["id"],
        "disposal_date": "2024-09-15T00:00:00Z",
        "proceeds": 45000.0,
        "reason": "Sold to third party",
    })
    h.eq("Accounting creates disposal (201)", r.status_code, 201)
    disp = r.json()
    h.eq("Status PENDING", disp["status"], "PENDING")
    h.check("NBV recorded > 0", disp["nbv_at_disposal"] > 0)
    h.check("Gain/loss computed", "gain_loss" in disp)

    h.eq("Duplicate PENDING rejected (409)",
         accounting.post("/api/disposals", json={
             "asset_id": asset2["id"],
             "disposal_date": "2024-09-15T00:00:00Z",
             "proceeds": 1.0,
         }).status_code, 409)

    h.eq("Requester cannot approve own (403)",
         accounting.post(f"/api/disposals/{disp['id']}/approve").status_code, 403)

    r = approver.post(f"/api/disposals/{disp['id']}/approve")
    h.eq("Approver approves (200)", r.status_code, 200)
    h.eq("Status APPROVED", r.json()["status"], "APPROVED")

    h.eq("Asset now DISPOSED",
         approver.get(f"/api/assets/{asset2['id']}").json()["status"], "DISPOSED")

    h.eq("Cannot dispose disposed asset (400)",
         accounting.post("/api/disposals", json={
             "asset_id": asset2["id"],
             "disposal_date": "2024-10-01T00:00:00Z",
             "proceeds": 1.0,
         }).status_code, 400)

    h.check("Disposal register lists it",
            any(d["id"] == disp["id"] for d in auditor.get("/api/disposals").json()))

    # --------------------------------------------------------------
    h.start("9. Journals")
    h.eq("Auditor cannot prepare journal (403)",
         auditor.post("/api/journals/depreciation", json={"period_label": "2024"}).status_code, 403)

    r = accounting.post("/api/journals/depreciation", json={"period_label": "2024"})
    h.eq("Accounting prepares journal (201)", r.status_code, 201)
    je = r.json()
    h.eq("Debits = credits", je["total_debit"], je["total_credit"])
    h.eq("Two lines (DR + CR)", len(je["lines"]), 2)
    h.eq("Status DRAFT", je["status"], "DRAFT")

    r = accounting.post("/api/journals/depreciation", json={"period_label": "2024"})
    h.eq("Reprepare is idempotent", r.json()["id"], je["id"])

    h.eq("Preparer cannot approve own (403)",
         accounting.post(f"/api/journals/{je['id']}/approve").status_code, 403)

    r = approver.post(f"/api/journals/{je['id']}/approve")
    h.eq("Approver approves journal (200)", r.status_code, 200)
    h.eq("Journal status APPROVED", r.json()["status"], "APPROVED")

    # --------------------------------------------------------------
    h.start("10. Period locking")
    h.eq("Auditor cannot lock period (403)",
         auditor.post("/api/periods/2024/lock").status_code, 403)

    r = approver.post("/api/periods/2024/lock")
    h.eq("Approver locks period (200)", r.status_code, 200)
    h.eq("Status LOCKED", r.json()["status"], "LOCKED")

    # Locked period blocks new disposal
    r = accounting.post("/api/disposals", json={
        "asset_id": asset1["id"],
        "disposal_date": "2024-11-01T00:00:00Z",
        "proceeds": 1000.0,
    })
    h.eq("Locked period blocks disposal (409)", r.status_code, 409)

    r = approver.post("/api/periods/2024/unlock")
    h.eq("Approver unlocks (200)", r.status_code, 200)
    h.eq("Status OPEN", r.json()["status"], "OPEN")

    r = auditor.get("/api/periods")
    h.eq("Period list (200)", r.status_code, 200)

    # --------------------------------------------------------------
    h.start("11. Reports & dashboard")
    r = auditor.get("/api/reports/asset-register")
    h.eq("Asset register (200)", r.status_code, 200)
    h.eq("Title correct", r.json()["title"], "Asset Register")

    r = auditor.get("/api/reports/depreciation-schedule")
    h.eq("Depreciation schedule (200)", r.status_code, 200)

    r = auditor.get("/api/reports/asset-movement?period_label=2024")
    h.eq("Asset movement (200)", r.status_code, 200)

    r = auditor.get("/api/reports/disposal-register")
    h.eq("Disposal register (200)", r.status_code, 200)

    r = auditor.get("/api/dashboard")
    h.eq("Dashboard (200)", r.status_code, 200)
    dash = r.json()
    h.check("total_asset_cost present", "total_asset_cost" in dash)
    h.check("total_nbv present", "total_nbv" in dash)
    h.check("category_summary is list", isinstance(dash["category_summary"], list))

    # --------------------------------------------------------------
    h.start("12. Exports")
    r = auditor.get(f"/api/exports/sheets/{user_sheet['id']}/xlsx")
    h.eq("Export user sheet XLSX (200)", r.status_code, 200)
    h.check("XLSX content-type", "spreadsheet" in r.headers.get("content-type", ""))

    h.eq("Export system sheet rejected (400)",
         auditor.get(f"/api/exports/sheets/{system_sheet['id']}/xlsx").status_code, 400)

    h.eq("Export asset register XLSX (200)",
         auditor.get("/api/exports/reports/asset-register/xlsx").status_code, 200)

    r = auditor.get("/api/exports/reports/asset-register/pdf")
    h.eq("Export asset register PDF (200)", r.status_code, 200)
    h.check("PDF magic bytes %PDF", r.content[:4] == b"%PDF")

    h.eq("Unknown report → 404",
         auditor.get("/api/exports/reports/does-not-exist/xlsx").status_code, 404)

    # --------------------------------------------------------------
    h.start("13. XLSX import")
    from openpyxl import Workbook as XlWb
    buf = io.BytesIO()
    xl = XlWb()
    xl.active.cell(row=1, column=1, value="Imported")
    xl.active.cell(row=2, column=1, value=42)
    xl.save(buf)
    xlsx_bytes = buf.getvalue()

    r = admin.post(
        "/api/imports/xlsx-to-sheet",
        data={"workbook_id": str(wb["id"]), "sheet_name": "Imported Data"},
        files={"file": ("t.xlsx", xlsx_bytes,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    h.eq("Admin import creates sheet (201)", r.status_code, 201)
    imported = r.json()

    r = admin.get(f"/api/sheets/{imported['id']}/render")
    cells = {(c["row"], c["col"]): c for c in r.json()["grid"]["cells"]}
    h.eq("Imported A1 value", cells[(1, 1)]["raw"], "Imported")
    h.eq("Imported A2 value", cells[(2, 1)]["raw"], "42")

    h.eq("Duplicate sheet name rejected (409)",
         admin.post(
             "/api/imports/xlsx-to-sheet",
             data={"workbook_id": str(wb["id"]), "sheet_name": "Imported Data"},
             files={"file": ("t.xlsx", xlsx_bytes,
                             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
         ).status_code, 409)

    big = b"0" * 6_000_000
    h.eq("Oversized import rejected (413)",
         admin.post(
             "/api/imports/xlsx-to-sheet",
             data={"workbook_id": str(wb["id"]), "sheet_name": "Huge"},
             files={"file": ("b.xlsx", big,
                             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
         ).status_code, 413)

    # --------------------------------------------------------------
    h.start("14. Audit log")
    r = auditor.get("/api/audit?limit=500")
    h.eq("Auditor can view audit (200)", r.status_code, 200)
    actions = {e["action"] for e in r.json()}
    for action in ("LOGIN_SUCCESS", "ASSET_CREATED", "ASSET_UPDATED",
                   "DEPRECIATION_RUN", "DISPOSAL_REQUESTED", "DISPOSAL_APPROVED",
                   "JOURNAL_PREPARED", "JOURNAL_APPROVED",
                   "PERIOD_LOCKED", "PERIOD_UNLOCKED",
                   "SHEET_CREATED", "SHEET_RENAMED", "SHEET_DELETED",
                   "CELLS_WRITTEN", "XLSX_IMPORTED",
                   "EXPORT_REPORT_PDF", "EXPORT_REPORT_XLSX"):
        h.in_(f"Audit includes {action}", actions, action)

    # --------------------------------------------------------------
    h.start("15. Logout & session revocation")
    h.eq("Logout (200)", accounting.post("/api/auth/logout").status_code, 200)
    h.eq("Session invalid after logout (401)",
         accounting.get("/api/auth/me").status_code, 401)

    # --------------------------------------------------------------
    return h.summary()


if __name__ == "__main__":
    sys.exit(main())