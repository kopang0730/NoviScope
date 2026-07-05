import pytest
from sqlmodel import Session, select

from noviscope.auth.passwords import hash_password, verify_password
from noviscope.auth.service import AuthService
from noviscope.models.user import InviteCode, InviteStatus, User, UserRole


def test_user_and_invite_persist(db_session: Session):
    admin = User(
        email="admin@example.com",
        display_name="Admin",
        password_hash="hashed-password",
        role=UserRole.ADMIN,
    )
    invite = InviteCode(
        code="LAB-2026-0001",
        created_by_user_id=admin.id,
        max_uses=1,
    )
    db_session.add(admin)
    db_session.add(invite)
    db_session.commit()

    saved_user = db_session.exec(select(User)).one()
    saved_invite = db_session.exec(select(InviteCode)).one()

    assert saved_user.email == "admin@example.com"
    assert saved_user.role == UserRole.ADMIN
    assert saved_invite.status == InviteStatus.ACTIVE
    assert saved_invite.used_count == 0


def test_password_hash_verification():
    password_hash = hash_password("correct-horse-battery-staple")

    assert password_hash != "correct-horse-battery-staple"
    assert verify_password("correct-horse-battery-staple", password_hash) is True
    assert verify_password("wrong-password", password_hash) is False


def test_register_member_consumes_invite(db_session: Session):
    admin = User(
        email="admin@example.com",
        display_name="Admin",
        password_hash="hash",
        role=UserRole.ADMIN,
    )
    invite = InviteCode(code="LAB-INVITE", created_by_user_id=admin.id)
    db_session.add(admin)
    db_session.add(invite)
    db_session.commit()

    service = AuthService(db_session)
    user = service.register_member(
        invite_code="LAB-INVITE",
        email="student@example.com",
        display_name="Student",
        password="student-password",
    )
    saved_invite = db_session.get(InviteCode, invite.id)

    assert user.email == "student@example.com"
    assert user.role == UserRole.MEMBER
    assert verify_password("student-password", user.password_hash) is True
    assert saved_invite is not None
    assert saved_invite.used_count == 1
    assert saved_invite.status == InviteStatus.EXHAUSTED


def test_one_use_invite_cannot_register_twice(db_session: Session):
    admin = User(
        email="admin@example.com",
        display_name="Admin",
        password_hash="hash",
        role=UserRole.ADMIN,
    )
    invite = InviteCode(code="LAB-ONCE", created_by_user_id=admin.id, max_uses=1)
    db_session.add(admin)
    db_session.add(invite)
    db_session.commit()

    service = AuthService(db_session)
    service.register_member(
        invite_code="LAB-ONCE",
        email="first@example.com",
        display_name="First",
        password="student-password",
    )

    with pytest.raises(ValueError, match="Invalid invite code"):
        service.register_member(
            invite_code="LAB-ONCE",
            email="second@example.com",
            display_name="Second",
            password="student-password",
        )

    saved_invite = db_session.get(InviteCode, invite.id)
    assert saved_invite is not None
    assert saved_invite.used_count == 1
    assert saved_invite.status == InviteStatus.EXHAUSTED


def test_register_member_rejects_invalid_invite(db_session: Session):
    service = AuthService(db_session)

    with pytest.raises(ValueError, match="Invalid invite code"):
        service.register_member(
            invite_code="MISSING",
            email="student@example.com",
            display_name="Student",
            password="student-password",
        )


def test_register_member_rejects_expired_invite(db_session: Session):
    admin = User(
        email="admin@example.com",
        display_name="Admin",
        password_hash="hash",
        role=UserRole.ADMIN,
    )
    invite = InviteCode(
        code="LAB-EXPIRED",
        created_by_user_id=admin.id,
        expires_at="2000-01-01T00:00:00+00:00",
    )
    db_session.add(admin)
    db_session.add(invite)
    db_session.commit()

    service = AuthService(db_session)

    with pytest.raises(ValueError, match="Invalid invite code"):
        service.register_member(
            invite_code="LAB-EXPIRED",
            email="student@example.com",
            display_name="Student",
            password="student-password",
        )
