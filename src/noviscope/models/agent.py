from enum import StrEnum

from sqlmodel import Field, SQLModel


class ToolPermission(StrEnum):
    WEB_SEARCH = "web_search"
    READ_PDF = "read_pdf"
    GITHUB_SEARCH = "github_search"
    WRITE_FILES = "write_files"
    RUN_CODE = "run_code"
    READ_EXPERIMENT_RESULTS = "read_experiment_results"
    WRITE_PAPER = "write_paper"
    WRITE_PPT = "write_ppt"


class AgentAssignment(SQLModel, table=True):
    agent_id: str = Field(primary_key=True)
    provider_id: str | None = Field(default=None, foreign_key="modelprovider.id")
    model_name: str | None = None
