from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"
    ACCOUNTING = "accounting"
    APPROVER = "approver"
    AUDITOR = "auditor"


class Permission(str, Enum):
    VIEW_ASSETS = "view_assets"
    EDIT_ASSETS = "edit_assets"
    CALC_DEPRECIATION = "calc_depreciation"
    CREATE_DISPOSAL = "create_disposal"
    APPROVE_DISPOSAL = "approve_disposal"
    PREPARE_JOURNAL = "prepare_journal"
    APPROVE_JOURNAL = "approve_journal"
    MANAGE_USERS = "manage_users"
    VIEW_AUDIT = "view_audit"
    DELETE_SHEET = "delete_sheet"
    EXPORT_SENSITIVE = "export_sensitive"


# Derived from Document 05 §3 (roles/permissions matrix).
# Where the matrix said "as policy permits" / "if permitted", this MVP grants the
# permission only to roles that clearly should have it. Ambiguous cells are denied
# by default per Doc 05 §5 (deny by default).
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.ADMIN: set(Permission),
    Role.ACCOUNTING: {
        Permission.VIEW_ASSETS,
        Permission.EDIT_ASSETS,
        Permission.CALC_DEPRECIATION,
        Permission.CREATE_DISPOSAL,
        Permission.PREPARE_JOURNAL,
        Permission.VIEW_AUDIT,
        Permission.DELETE_SHEET,
        Permission.EXPORT_SENSITIVE,
    },
    Role.APPROVER: {
        Permission.VIEW_ASSETS,
        Permission.CALC_DEPRECIATION,
        Permission.APPROVE_DISPOSAL,
        Permission.PREPARE_JOURNAL,
        Permission.APPROVE_JOURNAL,
        Permission.VIEW_AUDIT,
        Permission.EXPORT_SENSITIVE,
    },
    Role.AUDITOR: {
        Permission.VIEW_ASSETS,
        Permission.VIEW_AUDIT,
    },
}