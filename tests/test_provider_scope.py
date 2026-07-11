from sqlalchemy import text
from sqlmodel import Session, select

from noviscope.core.crypto import SecretBox
from noviscope.db.session import create_db_engine, create_schema
from noviscope.models.provider import ModelProvider, ProviderKind, ProviderScope
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


def test_create_schema_upgrades_legacy_provider_table_and_allows_duplicate_names(tmp_path):
    engine = create_db_engine(f"sqlite:///{tmp_path / 'legacy-provider-schema.db'}")

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE modelprovider (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    name VARCHAR NOT NULL UNIQUE,
                    kind VARCHAR NOT NULL,
                    base_url VARCHAR NOT NULL,
                    default_model VARCHAR NOT NULL,
                    api_key_ciphertext VARCHAR NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at VARCHAR NOT NULL,
                    updated_at VARCHAR NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO modelprovider (
                    id,
                    name,
                    kind,
                    base_url,
                    default_model,
                    api_key_ciphertext,
                    is_active,
                    created_at,
                    updated_at
                ) VALUES (
                    'provider_legacy_1',
                    'shared-name',
                    'openai_compatible',
                    'https://api.openai.com/v1',
                    'gpt-4.1',
                    'ciphertext-1',
                    1,
                    '2026-07-05T00:00:00+00:00',
                    '2026-07-05T00:00:00+00:00'
                )
                """
            )
        )

    create_schema(engine)
    create_schema(engine)

    with engine.begin() as connection:
        columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info('modelprovider')")).fetchall()
        }
        assert {
            "api_mode",
            "scope",
            "owner_user_id",
            "created_by_user_id",
        }.issubset(columns)
        assert connection.execute(
            text("SELECT scope FROM modelprovider WHERE id = 'provider_legacy_1'")
        ).scalar_one() == "shared"
        assert connection.execute(
            text("SELECT api_mode FROM modelprovider WHERE id = 'provider_legacy_1'")
        ).scalar_one() == "auto"

        index_rows = connection.execute(
            text("PRAGMA index_list('modelprovider')")
        ).mappings().all()
        provider_name_indexes = []
        for index_row in index_rows:
            columns_for_index = connection.execute(
                text(f"PRAGMA index_info('{index_row['name']}')")
            ).mappings().all()
            if [column["name"] for column in columns_for_index] == ["name"]:
                provider_name_indexes.append(index_row)

        assert provider_name_indexes
        assert any(index_row["unique"] == 0 for index_row in provider_name_indexes)

        connection.execute(
            text(
                """
                INSERT INTO modelprovider (
                    id,
                    name,
                    kind,
                    scope,
                    owner_user_id,
                    created_by_user_id,
                    base_url,
                    default_model,
                    api_key_ciphertext,
                    is_active,
                    created_at,
                    updated_at
                ) VALUES (
                    'provider_legacy_2',
                    'shared-name',
                    'openai_compatible',
                    'personal',
                    NULL,
                    NULL,
                    'https://api.deepseek.com',
                    'deepseek-chat',
                    'ciphertext-2',
                    1,
                    '2026-07-05T00:00:00+00:00',
                    '2026-07-05T00:00:00+00:00'
                )
                """
            )
        )

        assert connection.execute(
            text("SELECT COUNT(*) FROM modelprovider WHERE name = 'shared-name'")
        ).scalar_one() == 2

    with Session(engine) as session:
        member = make_user("member@example.com")
        session.add(member)
        session.commit()

        providers = ProviderService(session, SecretBox("test-secret")).list_providers_for_user(
            member
        )

        assert "provider_legacy_1" in {provider.id for provider in providers}


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


def test_two_users_can_create_personal_providers_with_same_name(db_session: Session):
    first_user = make_user("first@example.com")
    second_user = make_user("second@example.com")
    db_session.add(first_user)
    db_session.add(second_user)
    db_session.commit()

    service = ProviderService(db_session, SecretBox("test-secret"))
    first_provider = service.create_provider(
        name="team-openai",
        kind=ProviderKind.OPENAI_COMPATIBLE,
        base_url="https://api.openai.com/v1",
        default_model="gpt-4.1",
        api_key="first-key",
        scope=ProviderScope.PERSONAL,
        owner_user_id=first_user.id,
        created_by_user_id=first_user.id,
    )
    second_provider = service.create_provider(
        name="team-openai",
        kind=ProviderKind.OPENAI_COMPATIBLE,
        base_url="https://api.deepseek.com",
        default_model="deepseek-chat",
        api_key="second-key",
        scope=ProviderScope.PERSONAL,
        owner_user_id=second_user.id,
        created_by_user_id=second_user.id,
    )

    providers = db_session.exec(
        select(ModelProvider).where(ModelProvider.name == "team-openai")
    ).all()

    assert {provider.id for provider in providers} == {first_provider.id, second_provider.id}


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
