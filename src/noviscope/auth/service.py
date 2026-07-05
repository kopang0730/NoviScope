from datetime import datetime

from sqlalchemy import case, update
from sqlmodel import Session, select

from noviscope.auth.passwords import hash_password, verify_password
from noviscope.models.common import utc_now
from noviscope.models.user import InviteCode, InviteStatus, User, UserRole


class AuthService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_invite(
        self,
        *,
        code: str,
        created_by_user_id: str | None,
        max_uses: int = 1,
        expires_at: str | None = None,
    ) -> InviteCode:
        invite = InviteCode(
            code=code,
            created_by_user_id=created_by_user_id,
            max_uses=max_uses,
            expires_at=expires_at,
        )
        self.session.add(invite)
        self.session.commit()
        self.session.refresh(invite)
        return invite

    def register_member(
        self,
        *,
        invite_code: str,
        email: str,
        display_name: str,
        password: str,
    ) -> User:
        now = utc_now()
        invite = self._get_active_invite(invite_code, now=now)
        user = User(
            email=email,
            display_name=display_name,
            password_hash=hash_password(password),
            role=UserRole.MEMBER,
        )
        update_result = self.session.execute(
            update(InviteCode)
            .where(
                InviteCode.id == invite.id,
                InviteCode.status == InviteStatus.ACTIVE,
                InviteCode.used_count < InviteCode.max_uses,
                InviteCode.expires_at == invite.expires_at,
            )
            .values(
                used_count=InviteCode.used_count + 1,
                status=case(
                    (
                        InviteCode.used_count + 1 >= InviteCode.max_uses,
                        InviteStatus.EXHAUSTED.value,
                    ),
                    else_=InviteCode.status,
                ),
                updated_at=now.isoformat(),
            )
        )
        if update_result.rowcount != 1:
            self.session.rollback()
            raise ValueError("Invalid invite code")
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def authenticate(self, *, email: str, password: str) -> User:
        user = self.session.exec(select(User).where(User.email == email)).first()
        if user is None or not user.is_active:
            raise ValueError("Invalid email or password")
        if not verify_password(password, user.password_hash):
            raise ValueError("Invalid email or password")
        return user

    def _get_active_invite(self, code: str, *, now: datetime | None = None) -> InviteCode:
        invite = self.session.exec(select(InviteCode).where(InviteCode.code == code)).first()
        if invite is None or invite.status != InviteStatus.ACTIVE:
            raise ValueError("Invalid invite code")
        if invite.used_count >= invite.max_uses:
            raise ValueError("Invalid invite code")
        if invite.expires_at is not None:
            try:
                expires_at = datetime.fromisoformat(invite.expires_at)
            except ValueError as exc:
                raise ValueError("Invalid invite code") from exc
            if expires_at.tzinfo is None:
                raise ValueError("Invalid invite code")
            if expires_at <= (now or utc_now()):
                raise ValueError("Invalid invite code")
        return invite
