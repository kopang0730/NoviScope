from typing import ClassVar, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict

InputKind: TypeAlias = Literal["long_text", "short_text", "single_select"]
LanguageCode: TypeAlias = Literal["zh", "en"]
SubmissionTarget: TypeAlias = Literal["initial_direction", "title"]


class LocalizedTextResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    en: str
    zh: str


class QuestIntakeOptionResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    label: LocalizedTextResponse
    value: str


class QuestIntakeFieldResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    example: LocalizedTextResponse
    helper: LocalizedTextResponse
    input_kind: InputKind
    key: str
    label: LocalizedTextResponse
    maps_to: tuple[SubmissionTarget, ...]
    options: tuple[QuestIntakeOptionResponse, ...] = ()
    placeholder: LocalizedTextResponse
    prompt: LocalizedTextResponse
    required: bool


class QuestIntakeExampleResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    initial_direction: LocalizedTextResponse
    key: str
    title: LocalizedTextResponse


class QuestIntakeTemplateResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    examples: tuple[QuestIntakeExampleResponse, ...]
    fields: tuple[QuestIntakeFieldResponse, ...]
    initial_direction_field_order: tuple[str, ...]
    supported_languages: tuple[LanguageCode, ...]
    title_field_key: str
    version: str
