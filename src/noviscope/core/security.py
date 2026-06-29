from enum import StrEnum


class OutboundDataClass(StrEnum):
    PUBLIC_METADATA = "public_metadata"
    PUBLIC_PAPER_TEXT = "public_paper_text"
    PRIVATE_CODE = "private_code"
    PRIVATE_DATASET = "private_dataset"
    PRIVATE_EXPERIMENT_LOG = "private_experiment_log"
    PRIVATE_CHECKPOINT = "private_checkpoint"
    UNPUBLISHED_DRAFT = "unpublished_draft"


PRIVATE_CLASSES = {
    OutboundDataClass.PRIVATE_CODE,
    OutboundDataClass.PRIVATE_DATASET,
    OutboundDataClass.PRIVATE_EXPERIMENT_LOG,
    OutboundDataClass.PRIVATE_CHECKPOINT,
    OutboundDataClass.UNPUBLISHED_DRAFT,
}


def redact_secret(value: str) -> str:
    if len(value) <= 8:
        return "***"
    return f"{value[:3]}...{value[-3:]}"


def assert_external_upload_allowed(
    data_class: OutboundDataClass,
    *,
    user_approved: bool,
) -> None:
    if data_class in PRIVATE_CLASSES and not user_approved:
        raise PermissionError(f"{data_class.name} requires explicit user approval")
