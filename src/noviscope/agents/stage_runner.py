from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from pydantic import SecretStr

from noviscope.core.json_types import JsonObject
from noviscope.models.provider import ProviderKind
from noviscope.models.quest import Quest, StageCard


@dataclass(frozen=True, slots=True)
class ModelProviderCredentials:
    id: str
    name: str
    kind: ProviderKind
    base_url: str
    model: str
    api_key: SecretStr


@dataclass(frozen=True, slots=True)
class StageRunContext:
    stage: StageCard
    quest: Quest
    provider: ModelProviderCredentials


@dataclass(frozen=True, slots=True)
class StageRunResult:
    summary: str
    confidence: str
    input_payload: JsonObject
    output_payload: JsonObject
    evidence_payload: JsonObject


class StageRunner(Protocol):
    @property
    def agent_id(self) -> str: ...

    @property
    def supported_provider_kinds(self) -> frozenset[ProviderKind]: ...

    def build_input_payload(self, context: StageRunContext) -> JsonObject: ...

    def run(self, context: StageRunContext) -> StageRunResult: ...


@dataclass(frozen=True, slots=True)
class StageRunnerRegistry:
    runners: Mapping[str, StageRunner]

    def get_runner(self, agent_id: str) -> StageRunner | None:
        return self.runners.get(agent_id)
