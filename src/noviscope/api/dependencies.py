from sqlmodel import Session


def get_session() -> Session:
    raise RuntimeError("session dependency must be overridden by create_app")
