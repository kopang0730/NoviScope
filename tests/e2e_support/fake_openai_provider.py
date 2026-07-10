from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

from noviscope.agents.demand_validation import DemandValidationOutput

E2E_MODEL = "noviscope-e2e-model"


class ChatRequestMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: Literal["system", "user"]
    content: str


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    model: str
    messages: list[ChatRequestMessage]
    temperature: float


class ModelItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str


class ModelListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    data: list[ModelItem]


class AssistantMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: Literal["assistant"] = "assistant"
    content: str


class ChatChoice(BaseModel):
    model_config = ConfigDict(frozen=True)

    index: int
    finish_reason: Literal["stop"]
    message: AssistantMessage


class ChatCompletionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    model: str
    choices: list[ChatChoice]


DEMAND_OUTPUT = DemandValidationOutput(
    confidence="medium",
    demand_assessment="plausible",
    evidence=["The supplied research direction is an unverified lead."],
    evidence_for_demand=[
        "Badminton coaching may benefit from movement and shuttle analysis, but this has not "
        "been externally verified."
    ],
    go_or_no_go_recommendation="go_with_human_review",
    missing_evidence=[
        "No verified coach or athlete interview is available.",
        "No external demand source has been verified.",
    ],
    next_step="Ask a human reviewer to verify demand sources before downstream work.",
    raw_response="Deterministic local E2E response; no external provider was contacted.",
    real_world_scenario="A coach reviews badminton movement and shuttle trajectories.",
    risks=[
        "Demand evidence remains unverified.",
        "No experiment has run, and no experiment result is claimed.",
    ],
    suggested_human_checklist=[
        "Interview a coach or athlete.",
        "Verify a real workflow and measurable pain point.",
    ],
    summary="The badminton-analysis demand is plausible but requires human evidence review.",
    target_user_or_customer="Badminton coaches and athletes",
)

app = FastAPI(title="NoviScope E2E Provider")


@app.get("/v1/models")
def list_models() -> ModelListResponse:
    return ModelListResponse(data=[ModelItem(id=E2E_MODEL)])


@app.post("/v1/chat/completions")
def create_chat_completion(request: ChatCompletionRequest) -> ChatCompletionResponse:
    return ChatCompletionResponse(
        choices=[
            ChatChoice(
                finish_reason="stop",
                index=0,
                message=AssistantMessage(content=DEMAND_OUTPUT.model_dump_json()),
            )
        ],
        model=request.model,
    )
