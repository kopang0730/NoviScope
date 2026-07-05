from sqlmodel import Session

from noviscope.models.user import User, UserRole
from noviscope.quests.service import QuestService


def make_user(email: str, role: UserRole = UserRole.MEMBER) -> User:
    return User(
        email=email,
        display_name=email.split("@")[0],
        password_hash="hash",
        role=role,
    )


def test_member_lists_only_owned_quests(db_session: Session):
    member = make_user("member@example.com")
    other = make_user("other@example.com")
    db_session.add(member)
    db_session.add(other)
    db_session.commit()

    service = QuestService(db_session)
    owned = service.create_quest(
        title="Owned",
        initial_direction="AI+体育",
        owner_user_id=member.id,
    )
    service.create_quest(
        title="Other",
        initial_direction="手写文本擦除",
        owner_user_id=other.id,
    )

    quests = service.list_quests_for_user(member)

    assert [quest.id for quest in quests] == [owned.id]


def test_admin_lists_all_quests(db_session: Session):
    admin = make_user("admin@example.com", UserRole.ADMIN)
    member = make_user("member@example.com")
    db_session.add(admin)
    db_session.add(member)
    db_session.commit()

    service = QuestService(db_session)
    service.create_quest(title="One", initial_direction="AI+体育", owner_user_id=member.id)
    service.create_quest(title="Two", initial_direction="手写文本擦除", owner_user_id=member.id)

    assert len(service.list_quests_for_user(admin)) == 2
