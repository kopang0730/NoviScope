import argparse
from collections.abc import Sequence
from typing import Final

from pydantic import BaseModel, ConfigDict, SecretStr
from sqlmodel import Session, select

from noviscope.agents.assignments import AgentAssignmentService
from noviscope.auth.passwords import hash_password
from noviscope.core.config import get_settings, is_sqlite_database_url
from noviscope.core.crypto import SecretBox
from noviscope.db.session import create_db_engine, create_schema
from noviscope.models.provider import ProviderKind, ProviderScope
from noviscope.models.user import User, UserRole
from noviscope.providers.service import ProviderService
from noviscope.quests.service import QuestService

ADMIN_EMAIL: Final = "admin.e2e@example.test"
ADMIN_PASSWORD: Final = "NoviScope-e2e-admin-2026"
MEMBER_EMAIL: Final = "member.e2e@example.test"
MEMBER_PASSWORD: Final = "NoviScope-e2e-member-2026"
E2E_MODEL: Final = "noviscope-e2e-model"
E2E_API_KEY: Final = "local-e2e-key"
SHARED_PROVIDER_NAME: Final = "NoviScope E2E Shared"
PERSONAL_PROVIDER_NAME: Final = "NoviScope E2E Personal"
QUEST_TITLE: Final = "Badminton Performance Analysis"
QUEST_DIRECTION: Final = (
    "Analyze badminton movement and shuttle trajectories for coaching support. "
    "Treat the demand as unverified until a human reviews real user evidence."
)


class E2ESeedError(RuntimeError):
    pass


class SeededIds(BaseModel):
    model_config = ConfigDict(frozen=True)

    admin_user_id: str
    member_user_id: str
    shared_provider_id: str
    personal_provider_id: str
    assignment_agent_id: str
    quest_id: str
    stage_ids: tuple[str, ...]


def seed_workbench_e2e(
    database_url: str,
    provider_base_url: str,
    provider_secret_key: SecretStr,
) -> SeededIds:
    if not is_sqlite_database_url(database_url):
        raise E2ESeedError("E2E seeding accepts SQLite database URLs only")

    engine = create_db_engine(database_url)
    create_schema(engine)
    with Session(engine) as session:
        if session.exec(select(User)).first() is not None:
            raise E2ESeedError("E2E database already contains users; refusing to seed")

        admin = User(
            display_name="E2E Admin",
            email=ADMIN_EMAIL,
            password_hash=hash_password(ADMIN_PASSWORD),
            role=UserRole.ADMIN,
        )
        member = User(
            display_name="E2E Member",
            email=MEMBER_EMAIL,
            password_hash=hash_password(MEMBER_PASSWORD),
            role=UserRole.MEMBER,
        )
        session.add(admin)
        session.add(member)
        session.commit()
        session.refresh(admin)
        session.refresh(member)

        provider_service = ProviderService(
            session,
            SecretBox(provider_secret_key.get_secret_value()),
        )
        shared_provider = provider_service.create_provider(
            api_key=E2E_API_KEY,
            base_url=provider_base_url,
            created_by_user_id=admin.id,
            default_model=E2E_MODEL,
            kind=ProviderKind.OPENAI_COMPATIBLE,
            name=SHARED_PROVIDER_NAME,
            scope=ProviderScope.SHARED,
        )
        personal_provider = provider_service.create_provider(
            api_key=E2E_API_KEY,
            base_url=provider_base_url,
            created_by_user_id=member.id,
            default_model=E2E_MODEL,
            kind=ProviderKind.OPENAI_COMPATIBLE,
            name=PERSONAL_PROVIDER_NAME,
            owner_user_id=member.id,
            scope=ProviderScope.PERSONAL,
        )
        assignment = AgentAssignmentService(session).upsert_assignment(
            "demand_validator",
            model_name=E2E_MODEL,
            provider_id=shared_provider.id,
        )
        quest_service = QuestService(session)
        quest = quest_service.create_quest(
            initial_direction=QUEST_DIRECTION,
            owner_user_id=member.id,
            title=QUEST_TITLE,
        )
        stages = quest_service.list_stage_cards(quest.id)
        seeded_ids = SeededIds(
            admin_user_id=admin.id,
            assignment_agent_id=assignment.agent_id,
            member_user_id=member.id,
            personal_provider_id=personal_provider.id,
            quest_id=quest.id,
            shared_provider_id=shared_provider.id,
            stage_ids=tuple(stage.id for stage in stages),
        )

    return seeded_ids


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--provider-base-url", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        seeded_ids = seed_workbench_e2e(
            args.database_url,
            args.provider_base_url,
            SecretStr(get_settings().provider_secret_key),
        )
    except E2ESeedError as exc:
        parser.error(str(exc))
    print(seeded_ids.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
