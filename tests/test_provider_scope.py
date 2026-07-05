from sqlmodel import Session

from noviscope.core.crypto import SecretBox
from noviscope.models.provider import ProviderKind, ProviderScope
from noviscope.models.user import User, UserRole
from noviscope.providers.service import ProviderService


def make_user(email: str, role: UserRole = UserRole.MEMBER) -> User:
    return User(email=email, display_name=email.split("@")[0], password_hash="hash", role=role)


def test_member_sees_shared_and_own_personal_providers(db_session: Session):
    admin = make_user("admin@example.com", UserRole.ADMIN)
    member = make_user("member@example.com")
    other = make_user("other@example.com")
    db_session.add(admin)
    db_session.add(member)
    db_session.add(other)
    db_session.commit()

    service = ProviderService(db_session, SecretBox("test-secret"))
    shared = service.create_provider(
        name="shared-openai",
        kind=ProviderKind.OPENAI_COMPATIBLE,
        base_url="https://api.openai.com/v1",
        default_model="gpt-4.1",
        api_key="shared-key",
        scope=ProviderScope.SHARED,
        owner_user_id=None,
    )
    own = service.create_provider(
        name="member-deepseek",
        kind=ProviderKind.OPENAI_COMPATIBLE,
        base_url="https://api.deepseek.com",
        default_model="deepseek-chat",
        api_key="member-key",
        scope=ProviderScope.PERSONAL,
        owner_user_id=member.id,
    )
    service.create_provider(
        name="other-kimi",
        kind=ProviderKind.OPENAI_COMPATIBLE,
        base_url="https://api.moonshot.cn/v1",
        default_model="kimi-k2",
        api_key="other-key",
        scope=ProviderScope.PERSONAL,
        owner_user_id=other.id,
    )

    providers = service.list_providers_for_user(member)

    assert {provider.id for provider in providers} == {shared.id, own.id}


def test_member_cannot_access_other_users_personal_provider(db_session: Session):
    member = make_user("member@example.com")
    other = make_user("other@example.com")
    db_session.add(member)
    db_session.add(other)
    db_session.commit()

    service = ProviderService(db_session, SecretBox("test-secret"))
    provider = service.create_provider(
        name="other-kimi",
        kind=ProviderKind.OPENAI_COMPATIBLE,
        base_url="https://api.moonshot.cn/v1",
        default_model="kimi-k2",
        api_key="other-key",
        scope=ProviderScope.PERSONAL,
        owner_user_id=other.id,
    )

    try:
        service.get_provider_for_user(provider.id, member)
    except PermissionError as exc:
        assert provider.id in str(exc)
    else:
        raise AssertionError("member should not access another user's personal provider")


def test_admin_sees_all_providers(db_session: Session):
    admin = make_user("admin@example.com", UserRole.ADMIN)
    member = make_user("member@example.com")
    db_session.add(admin)
    db_session.add(member)
    db_session.commit()

    service = ProviderService(db_session, SecretBox("test-secret"))
    shared = service.create_provider(
        name="shared-openai",
        kind=ProviderKind.OPENAI_COMPATIBLE,
        base_url="https://api.openai.com/v1",
        default_model="gpt-4.1",
        api_key="shared-key",
        scope=ProviderScope.SHARED,
        created_by_user_id=admin.id,
    )
    personal = service.create_provider(
        name="member-deepseek",
        kind=ProviderKind.OPENAI_COMPATIBLE,
        base_url="https://api.deepseek.com",
        default_model="deepseek-chat",
        api_key="member-key",
        scope=ProviderScope.PERSONAL,
        owner_user_id=member.id,
        created_by_user_id=member.id,
    )

    providers = service.list_providers_for_user(admin)

    assert {provider.id for provider in providers} == {shared.id, personal.id}
