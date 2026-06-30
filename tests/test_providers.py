from sqlmodel import Session, select

from noviscope.core.crypto import SecretBox
from noviscope.models.provider import ModelProvider, ProviderKind
from noviscope.providers.service import ProviderService


def test_provider_service_encrypts_api_key_at_rest(db_session: Session):
    secret_box = SecretBox("test-secret")
    service = ProviderService(db_session, secret_box)

    provider = service.create_provider(
        name="primary-openai",
        kind=ProviderKind.OPENAI_COMPATIBLE,
        base_url="https://api.openai.com/v1",
        default_model="gpt-4.1",
        api_key="sk-realistic-test-key",
    )

    saved = db_session.exec(select(ModelProvider).where(ModelProvider.id == provider.id)).one()

    assert saved.api_key_ciphertext != "sk-realistic-test-key"
    assert secret_box.decrypt(saved.api_key_ciphertext) == "sk-realistic-test-key"


def test_provider_service_updates_and_deletes_provider(db_session: Session):
    service = ProviderService(db_session, SecretBox("test-secret"))
    provider = service.create_provider(
        name="primary-deepseek",
        kind=ProviderKind.OPENAI_COMPATIBLE,
        base_url="https://api.deepseek.com",
        default_model="deepseek-chat",
        api_key="sk-old-key",
    )

    updated = service.update_provider(
        provider.id,
        name="backup-deepseek",
        default_model="deepseek-reasoner",
        api_key="sk-new-key",
        is_active=False,
    )

    assert updated.name == "backup-deepseek"
    assert updated.default_model == "deepseek-reasoner"
    assert updated.is_active is False
    assert service.secret_box.decrypt(updated.api_key_ciphertext) == "sk-new-key"

    service.delete_provider(provider.id)

    try:
        service.get_provider(provider.id)
    except LookupError as exc:
        assert provider.id in str(exc)
    else:
        raise AssertionError("deleted provider should not be readable")
