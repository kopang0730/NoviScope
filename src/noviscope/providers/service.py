from sqlmodel import Session, select

from noviscope.agents.assignments import AgentAssignmentService
from noviscope.core.crypto import SecretBox
from noviscope.models.common import utc_now
from noviscope.models.provider import ModelProvider, ProviderKind, ProviderScope
from noviscope.models.user import User, UserRole


class ProviderService:
    def __init__(self, session: Session, secret_box: SecretBox) -> None:
        self.session = session
        self.secret_box = secret_box

    def create_provider(
        self,
        *,
        name: str,
        kind: ProviderKind,
        base_url: str,
        default_model: str,
        api_key: str,
        scope: ProviderScope = ProviderScope.PERSONAL,
        owner_user_id: str | None = None,
        created_by_user_id: str | None = None,
    ) -> ModelProvider:
        provider = ModelProvider(
            name=name,
            kind=kind,
            base_url=base_url,
            default_model=default_model,
            api_key_ciphertext=self.secret_box.encrypt(api_key),
            scope=scope,
            owner_user_id=owner_user_id,
            created_by_user_id=created_by_user_id,
        )
        self.session.add(provider)
        self.session.commit()
        self.session.refresh(provider)
        return provider

    def list_providers(self) -> list[ModelProvider]:
        return list(self.session.exec(select(ModelProvider)).all())

    def list_providers_for_user(self, user: User) -> list[ModelProvider]:
        statement = select(ModelProvider)
        if user.role != UserRole.ADMIN:
            statement = statement.where(
                (ModelProvider.scope == ProviderScope.SHARED)
                | (ModelProvider.owner_user_id == user.id)
            )
        return list(self.session.exec(statement).all())

    def get_provider(self, provider_id: str) -> ModelProvider:
        provider = self.session.get(ModelProvider, provider_id)
        if provider is None:
            raise LookupError(f"Provider {provider_id} not found")
        return provider

    def get_provider_for_user(self, provider_id: str, user: User) -> ModelProvider:
        provider = self.get_provider(provider_id)
        if user.role == UserRole.ADMIN:
            return provider
        if provider.scope == ProviderScope.SHARED or provider.owner_user_id == user.id:
            return provider
        raise PermissionError(f"Provider {provider_id} is not accessible")

    def decrypt_api_key(self, provider: ModelProvider) -> str:
        return self.secret_box.decrypt(provider.api_key_ciphertext)

    def update_provider(
        self,
        provider_id: str,
        *,
        name: str | None = None,
        kind: ProviderKind | None = None,
        base_url: str | None = None,
        default_model: str | None = None,
        api_key: str | None = None,
        is_active: bool | None = None,
    ) -> ModelProvider:
        provider = self.get_provider(provider_id)
        if name is not None:
            provider.name = name
        if kind is not None:
            provider.kind = kind
        if base_url is not None:
            provider.base_url = base_url
        if default_model is not None:
            provider.default_model = default_model
        if api_key is not None:
            provider.api_key_ciphertext = self.secret_box.encrypt(api_key)
        if is_active is not None:
            provider.is_active = is_active
        provider.updated_at = utc_now().isoformat()
        self.session.add(provider)
        self.session.commit()
        self.session.refresh(provider)
        return provider

    def update_provider_for_user(
        self,
        provider_id: str,
        user: User,
        **updates: object,
    ) -> ModelProvider:
        provider = self.get_provider_for_user(provider_id, user)
        if provider.scope == ProviderScope.SHARED and user.role != UserRole.ADMIN:
            raise PermissionError("Admin access required")
        return self.update_provider(provider_id, **updates)

    def delete_provider(self, provider_id: str) -> None:
        provider = self.get_provider(provider_id)
        AgentAssignmentService(self.session).clear_provider_assignments(provider_id)
        self.session.delete(provider)
        self.session.commit()

    def delete_provider_for_user(self, provider_id: str, user: User) -> None:
        provider = self.get_provider_for_user(provider_id, user)
        if provider.scope == ProviderScope.SHARED and user.role != UserRole.ADMIN:
            raise PermissionError("Admin access required")
        self.delete_provider(provider_id)
