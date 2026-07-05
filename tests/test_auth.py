from sqlmodel import Session, select

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
