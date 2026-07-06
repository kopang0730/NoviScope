from dataclasses import dataclass, field
from typing import Final

from pydantic import BaseModel, ConfigDict

from noviscope.core.json_types import JsonObject

INTAKE_RENDER_FIELDS: Final = (
    ("research_direction", "Research direction"),
    ("real_world_scenario", "Real-world scenario"),
    ("target_user_or_customer", "Target user or customer"),
    ("input_and_output", "Input and expected output"),
    ("existing_data", "Existing data"),
    ("known_baselines", "Known baselines"),
    ("evaluation_metrics", "Evaluation metrics"),
    ("preferred_language", "Preferred output language"),
)


class QuestIntake(BaseModel):
    model_config = ConfigDict(frozen=True)

    research_direction: str = ""
    real_world_scenario: str = ""
    target_user_or_customer: str = ""
    input_and_output: str = ""
    existing_data: str = ""
    known_baselines: str = ""
    evaluation_metrics: str = ""
    preferred_language: str = ""


@dataclass(frozen=True, slots=True)
class QuestCreateSpec:
    title: str
    initial_direction: str = ""
    intake: QuestIntake = field(default_factory=QuestIntake)
    owner_user_id: str | None = None


@dataclass(frozen=True, slots=True)
class QuestIntakeUpdateSpec:
    quest_id: str
    intake: QuestIntake
    initial_direction: str | None = None


def quest_intake_payload(intake: QuestIntake) -> JsonObject:
    return {
        key: value
        for key, value in intake.model_dump().items()
        if isinstance(value, str) and value.strip()
    }


def render_initial_direction_from_intake(intake: QuestIntake) -> str:
    lines = []
    for field_name, label in INTAKE_RENDER_FIELDS:
        value = getattr(intake, field_name).strip()
        if value:
            lines.append(f"{label}: {value}")
    return "\n".join(lines)


def resolve_initial_direction(spec: QuestCreateSpec) -> str:
    legacy_direction = spec.initial_direction.strip()
    if legacy_direction:
        return legacy_direction
    return render_initial_direction_from_intake(spec.intake)


def resolve_updated_initial_direction(
    current_initial_direction: str,
    spec: QuestIntakeUpdateSpec,
) -> str:
    if spec.initial_direction is not None:
        return spec.initial_direction.strip()
    rendered_direction = render_initial_direction_from_intake(spec.intake)
    return rendered_direction or current_initial_direction
