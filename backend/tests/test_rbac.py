from app.security.permissions import ROLE_PERMISSIONS, Permission, Role


def test_admin_has_all_permissions():
    assert ROLE_PERMISSIONS[Role.ADMIN] == set(Permission)


def test_accounting_cannot_manage_users():
    assert Permission.MANAGE_USERS not in ROLE_PERMISSIONS[Role.ACCOUNTING]


def test_accounting_cannot_approve_journal_or_disposal():
    assert Permission.APPROVE_JOURNAL not in ROLE_PERMISSIONS[Role.ACCOUNTING]
    assert Permission.APPROVE_DISPOSAL not in ROLE_PERMISSIONS[Role.ACCOUNTING]


def test_approver_can_approve_but_not_manage_users():
    assert Permission.APPROVE_DISPOSAL in ROLE_PERMISSIONS[Role.APPROVER]
    assert Permission.APPROVE_JOURNAL in ROLE_PERMISSIONS[Role.APPROVER]
    assert Permission.MANAGE_USERS not in ROLE_PERMISSIONS[Role.APPROVER]


def test_auditor_is_read_only():
    assert Permission.VIEW_ASSETS in ROLE_PERMISSIONS[Role.AUDITOR]
    assert Permission.VIEW_AUDIT in ROLE_PERMISSIONS[Role.AUDITOR]
    assert Permission.EDIT_ASSETS not in ROLE_PERMISSIONS[Role.AUDITOR]
    assert Permission.APPROVE_DISPOSAL not in ROLE_PERMISSIONS[Role.AUDITOR]
    assert Permission.MANAGE_USERS not in ROLE_PERMISSIONS[Role.AUDITOR]