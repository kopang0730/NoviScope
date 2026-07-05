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
        invite = self._get_active_invite(invite_code)
        user = User(
            email=email,
            display_name=display_name,
            password_hash=hash_password(password),
            role=UserRole.MEMBER,
        )
        invite.used_count += 1
        if invite.used_count >= invite.max_uses:
            invite.status = InviteStatus.EXHAUSTED
        invite.updated_at = utc_now().isoformat()
        self.session.add(user)
        self.session.add(invite)
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

    def _get_active_invite(self, code: str) -> InviteCode:
        invite = self.session.exec(select(InviteCode).where(InviteCode.code == code)).first()
        if invite is None or invite.status != InviteStatus.ACTIVE:
            raise ValueError("Invalid invite code")
        if invite.used_count >= invite.max_uses:
            raise ValueError("Invalid invite code")
        return invite
