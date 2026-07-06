from collections.abc import Generator
from sqlite3 import Connection as SQLiteConnection
from sqlite3 import Error as SQLiteError

from sqlalchemy import event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import ConnectionPoolEntry, StaticPool
from sqlmodel import Session, SQLModel, create_engine

from noviscope.models.agent import AgentAssignment  # noqa: F401
from noviscope.models.provider import ModelProvider  # noqa: F401
from noviscope.models.quest import Quest, StageCard  # noqa: F401
from noviscope.models.user import InviteCode, User  # noqa: F401


def create_db_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    if database_url in {"sqlite:///:memory:", "sqlite://"}:
        engine = create_engine(database_url, connect_args=connect_args, poolclass=StaticPool)
    else:
        engine = create_engine(database_url, connect_args=connect_args)
    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(
            dbapi_connection: SQLiteConnection,
            _: ConnectionPoolEntry,
        ) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_schema(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine)
    _upgrade_modelprovider_schema(engine)
    _upgrade_quest_schema(engine)
    SQLModel.metadata.create_all(engine)
    _ensure_modelprovider_name_index(engine)
    _ensure_quest_owner_user_id_index(engine)


def _upgrade_modelprovider_schema(engine: Engine) -> None:
    with engine.connect() as connection:
        inspector = inspect(connection)
        if not inspector.has_table("modelprovider"):
            return

        columns = {column["name"] for column in inspector.get_columns("modelprovider")}
        missing_columns = {
            "scope",
            "owner_user_id",
            "created_by_user_id",
        } - columns
        legacy_unique_name_constraints, legacy_unique_name_indexes = (
            _legacy_unique_name_artifacts(connection, inspector)
        )
        has_legacy_unique_name = bool(
            legacy_unique_name_constraints or legacy_unique_name_indexes
        )

    if not missing_columns and not has_legacy_unique_name:
        return

    if engine.dialect.name == "sqlite":
        _upgrade_sqlite_modelprovider_schema(engine, columns)
        return

    with engine.begin() as connection:
        if "scope" in missing_columns:
            connection.execute(text("ALTER TABLE modelprovider ADD COLUMN scope VARCHAR"))
            connection.execute(
                text("UPDATE modelprovider SET scope = 'shared' WHERE scope IS NULL")
            )
            connection.execute(
                text("ALTER TABLE modelprovider ALTER COLUMN scope SET DEFAULT 'shared'")
            )
            connection.execute(text("ALTER TABLE modelprovider ALTER COLUMN scope SET NOT NULL"))
        if "owner_user_id" in missing_columns:
            connection.execute(text("ALTER TABLE modelprovider ADD COLUMN owner_user_id VARCHAR"))
        if "created_by_user_id" in missing_columns:
            connection.execute(
                text("ALTER TABLE modelprovider ADD COLUMN created_by_user_id VARCHAR")
            )
        _drop_legacy_unique_name_constraints(
            connection,
            legacy_unique_name_constraints,
            legacy_unique_name_indexes,
        )


def _legacy_unique_name_artifacts(connection, inspector) -> tuple[list[str], list[str]]:
    constraint_names: list[str] = []
    index_names: list[str] = []

    for constraint in inspector.get_unique_constraints("modelprovider"):
        if constraint.get("column_names") == ["name"] and constraint.get("name"):
            constraint_names.append(constraint["name"])

    for index in inspector.get_indexes("modelprovider"):
        if index.get("unique") and index.get("column_names") == ["name"] and index.get("name"):
            index_names.append(index["name"])

    if connection.dialect.name != "sqlite":
        return constraint_names, index_names

    rows = connection.execute(text("PRAGMA index_list('modelprovider')")).mappings().all()
    for row in rows:
        if row["unique"] != 1:
            continue
        columns = connection.execute(
            text(f"PRAGMA index_info('{row['name']}')")
        ).mappings().all()
        if [column["name"] for column in columns] == ["name"]:
            index_names.append(row["name"])
    return constraint_names, index_names


def _upgrade_sqlite_modelprovider_schema(engine: Engine, existing_columns: set[str]) -> None:
    raw_connection = engine.raw_connection()
    cursor = raw_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute(
            """
            CREATE TABLE modelprovider__noviscope_upgrade (
                id VARCHAR NOT NULL PRIMARY KEY,
                name VARCHAR NOT NULL,
                kind VARCHAR NOT NULL,
                scope VARCHAR NOT NULL DEFAULT 'personal',
                owner_user_id VARCHAR,
                created_by_user_id VARCHAR,
                base_url VARCHAR NOT NULL,
                default_model VARCHAR NOT NULL,
                api_key_ciphertext VARCHAR NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at VARCHAR NOT NULL,
                updated_at VARCHAR NOT NULL,
                FOREIGN KEY(owner_user_id) REFERENCES user (id),
                FOREIGN KEY(created_by_user_id) REFERENCES user (id)
            )
            """
        )
        cursor.execute(
            f"""
            INSERT INTO modelprovider__noviscope_upgrade (
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
            )
            SELECT
                id,
                name,
                kind,
                {"COALESCE(scope, 'shared')" if "scope" in existing_columns else "'shared'"},
                {"owner_user_id" if "owner_user_id" in existing_columns else "NULL"},
                {"created_by_user_id" if "created_by_user_id" in existing_columns else "NULL"},
                base_url,
                default_model,
                api_key_ciphertext,
                COALESCE(is_active, 1),
                created_at,
                COALESCE(updated_at, created_at)
            FROM modelprovider
            """
        )
        cursor.execute("DROP TABLE modelprovider")
        cursor.execute(
            "ALTER TABLE modelprovider__noviscope_upgrade RENAME TO modelprovider"
        )
        raw_connection.commit()
    except SQLiteError:
        raw_connection.rollback()
        raise
    finally:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        raw_connection.close()


def _drop_legacy_unique_name_constraints(
    connection,
    constraint_names: list[str],
    index_names: list[str],
) -> None:
    for constraint_name in constraint_names:
        connection.execute(
            text(f'ALTER TABLE modelprovider DROP CONSTRAINT IF EXISTS "{constraint_name}"')
        )

    for index_name in index_names:
        connection.execute(text(f'DROP INDEX IF EXISTS "{index_name}"'))


def _upgrade_quest_schema(engine: Engine) -> None:
    with engine.connect() as connection:
        inspector = inspect(connection)
        if not inspector.has_table("quest"):
            return

        columns = {column["name"] for column in inspector.get_columns("quest")}

    missing_columns = {"owner_user_id", "intake_payload"} - columns
    if not missing_columns:
        return

    with engine.begin() as connection:
        if "owner_user_id" in missing_columns:
            if engine.dialect.name == "sqlite":
                connection.execute(
                    text("ALTER TABLE quest ADD COLUMN owner_user_id VARCHAR REFERENCES user (id)")
                )
            else:
                connection.execute(
                    text(
                        'ALTER TABLE quest ADD COLUMN owner_user_id '
                        'VARCHAR REFERENCES "user" (id)'
                    )
                )
        if "intake_payload" in missing_columns:
            connection.execute(text("ALTER TABLE quest ADD COLUMN intake_payload JSON"))
            connection.execute(
                text("UPDATE quest SET intake_payload = '{}' WHERE intake_payload IS NULL")
            )


def _ensure_modelprovider_name_index(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_modelprovider_name "
                "ON modelprovider (name)"
            )
        )


def _ensure_quest_owner_user_id_index(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_quest_owner_user_id "
                "ON quest (owner_user_id)"
            )
        )


def session_generator(engine: Engine) -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
