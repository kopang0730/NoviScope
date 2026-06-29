# NoviScope Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working NoviScope foundation slice: backend scaffold, typed domain contracts, provider/model configuration, agent registry, research quest state machine, and minimal HTTP API.

**Architecture:** Implement a Python FastAPI service with SQLModel over SQLite for the first server-side slice. Keep the code modular: `core` for settings/security, `models` for persisted records, `repositories` for database access, `model_gateway` for provider routing, `agents` for static agent contracts, and `quests` for workflow state transitions.

**Tech Stack:** Python 3.11+, FastAPI, SQLModel, Pydantic v2, pydantic-settings, SQLite, pytest, httpx, ruff.

---

## Scope

This plan implements Phase 1 from the design spec. It creates a working, testable backend foundation, not the full NoviScope product. The following subsystems get their own plans after this one is complete: literature retrieval, demand verification crawling, GPU job runner, evidence auditor, paper/PPT generation, and web frontend.

## File Structure

Create these files:

```text
README.md
pyproject.toml
src/noviscope/__init__.py
src/noviscope/main.py
src/noviscope/api/__init__.py
src/noviscope/api/routes.py
src/noviscope/agents/__init__.py
src/noviscope/agents/registry.py
src/noviscope/core/__init__.py
src/noviscope/core/config.py
src/noviscope/core/security.py
src/noviscope/db/__init__.py
src/noviscope/db/session.py
src/noviscope/model_gateway/__init__.py
src/noviscope/model_gateway/adapters.py
src/noviscope/model_gateway/service.py
src/noviscope/models/__init__.py
src/noviscope/models/agent.py
src/noviscope/models/common.py
src/noviscope/models/provider.py
src/noviscope/models/quest.py
src/noviscope/quests/__init__.py
src/noviscope/quests/service.py
tests/conftest.py
tests/test_agents.py
tests/test_api.py
tests/test_model_gateway.py
tests/test_quests.py
tests/test_security.py
```

Responsibilities:

- `main.py`: FastAPI app factory and app instance.
- `api/routes.py`: HTTP endpoints for health, providers, agents, and quests.
- `core/config.py`: environment-backed service settings.
- `core/security.py`: API key redaction and outbound data policy helpers.
- `db/session.py`: SQLite engine/session setup.
- `models/*.py`: SQLModel table and enum definitions.
- `agents/registry.py`: the 9-agent contract registry from the spec.
- `model_gateway/*.py`: provider profile validation and connection-test abstraction.
- `quests/service.py`: create quest and advance stage cards.

## Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/noviscope/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create package metadata**

Write `pyproject.toml`:

```toml
[project]
name = "noviscope"
version = "0.1.0"
description = "Evidence-driven research workflow for turning vague ideas into verified experiments and paper drafts."
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115.0",
  "httpx>=0.27.0",
  "pydantic>=2.8.0",
  "pydantic-settings>=2.4.0",
  "sqlmodel>=0.0.22",
  "uvicorn[standard]>=0.30.0"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3.0",
  "ruff>=0.6.0"
]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

- [ ] **Step 2: Create README with local commands**

Write `README.md`:

````markdown
# NoviScope

NoviScope is an evidence-driven research workflow that turns vague research directions into verified experiments and traceable paper drafts.

## Development

Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

Run API locally:

```bash
uvicorn noviscope.main:app --reload
```
````

- [ ] **Step 3: Create package marker**

Write `src/noviscope/__init__.py`:

```python
"""NoviScope backend package."""

__all__ = ["__version__"]

__version__ = "0.1.0"
```

- [ ] **Step 4: Create pytest database fixture shell**

Write `tests/conftest.py`:

```python
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine


@pytest.fixture()
def test_db_path(tmp_path: Path) -> Path:
    return tmp_path / "noviscope-test.db"


@pytest.fixture()
def test_engine(test_db_path: Path):
    engine = create_engine(f"sqlite:///{test_db_path}")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture()
def db_session(test_engine) -> Generator[Session, None, None]:
    with Session(test_engine) as session:
        yield session
```

- [ ] **Step 5: Install and run baseline tests**

Run:

```bash
pip install -e ".[dev]"
pytest
```

Expected: pytest exits 0 with no tests collected or with an empty suite pass.

- [ ] **Step 6: Commit scaffold**

```bash
git add README.md pyproject.toml src/noviscope/__init__.py tests/conftest.py
git commit -m "chore: scaffold NoviScope backend"
```

## Task 2: Core Settings and Secret Safety

**Files:**
- Create: `src/noviscope/core/__init__.py`
- Create: `src/noviscope/core/config.py`
- Create: `src/noviscope/core/security.py`
- Create: `tests/test_security.py`

- [ ] **Step 1: Write secret redaction tests**

Write `tests/test_security.py`:

```python
from noviscope.core.security import OutboundDataClass, assert_external_upload_allowed, redact_secret


def test_redact_secret_keeps_short_marker():
    assert redact_secret("sk-1234567890abcdef") == "sk-1...cdef"


def test_redact_secret_handles_short_values():
    assert redact_secret("abc") == "***"


def test_public_upload_allowed_without_consent():
    assert_external_upload_allowed(OutboundDataClass.PUBLIC_METADATA, user_approved=False)


def test_private_dataset_upload_requires_consent():
    try:
        assert_external_upload_allowed(OutboundDataClass.PRIVATE_DATASET, user_approved=False)
    except PermissionError as exc:
        assert "PRIVATE_DATASET requires explicit user approval" in str(exc)
    else:
        raise AssertionError("private dataset upload should require approval")
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
pytest tests/test_security.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'noviscope.core'`.

- [ ] **Step 3: Implement settings and security helpers**

Write `src/noviscope/core/__init__.py`:

```python
"""Core settings and safety helpers."""
```

Write `src/noviscope/core/config.py`:

```python
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NoviScope"
    database_url: str = Field(default="sqlite:///./noviscope.db")
    allow_external_private_uploads: bool = Field(default=False)

    model_config = SettingsConfigDict(env_prefix="NOVISCOPE_", env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

Write `src/noviscope/core/security.py`:

```python
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
    if len(value) < 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def assert_external_upload_allowed(
    data_class: OutboundDataClass,
    *,
    user_approved: bool,
) -> None:
    if data_class in PRIVATE_CLASSES and not user_approved:
        raise PermissionError(f"{data_class.name} requires explicit user approval")
```

- [ ] **Step 4: Verify security tests pass**

Run:

```bash
pytest tests/test_security.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit core safety helpers**

```bash
git add src/noviscope/core tests/test_security.py
git commit -m "feat: add core settings and secret safety helpers"
```

## Task 3: Domain Models

**Files:**
- Create: `src/noviscope/models/__init__.py`
- Create: `src/noviscope/models/common.py`
- Create: `src/noviscope/models/provider.py`
- Create: `src/noviscope/models/agent.py`
- Create: `src/noviscope/models/quest.py`
- Modify: `tests/conftest.py`
- Create: `tests/test_quests.py`

- [ ] **Step 1: Write model persistence test**

Write `tests/test_quests.py`:

```python
from sqlmodel import Session, select

from noviscope.models.provider import ModelProvider, ProviderKind
from noviscope.models.quest import Quest, QuestStatus, StageCard, StageStatus


def test_provider_and_quest_persist(db_session: Session):
    provider = ModelProvider(
        name="primary-deepseek",
        kind=ProviderKind.OPENAI_COMPATIBLE,
        base_url="https://api.deepseek.com",
        default_model="deepseek-chat",
        api_key_ciphertext="encrypted-value",
    )
    quest = Quest(title="AI+Sports Badminton", initial_direction="AI+体育，羽毛球")
    stage = StageCard(
        quest_id=quest.id,
        agent_id="demand_validator",
        title="Demand validation",
        status=StageStatus.PENDING,
    )
    db_session.add(provider)
    db_session.add(quest)
    db_session.add(stage)
    db_session.commit()

    saved_quest = db_session.exec(select(Quest)).one()
    saved_stage = db_session.exec(select(StageCard)).one()

    assert saved_quest.status == QuestStatus.DRAFT
    assert saved_stage.agent_id == "demand_validator"
```

- [ ] **Step 2: Run model test to verify failure**

Run:

```bash
pytest tests/test_quests.py::test_provider_and_quest_persist -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'noviscope.models'`.

- [ ] **Step 3: Implement shared model primitives**

Write `src/noviscope/models/__init__.py`:

```python
"""Database models for NoviScope."""
```

Write `src/noviscope/models/common.py`:

```python
from datetime import UTC, datetime
from uuid import uuid4


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def utc_now() -> datetime:
    return datetime.now(UTC)
```

- [ ] **Step 4: Implement provider model**

Write `src/noviscope/models/provider.py`:

```python
from enum import StrEnum

from sqlmodel import Field, SQLModel

from noviscope.models.common import new_id, utc_now


class ProviderKind(StrEnum):
    OPENAI_COMPATIBLE = "openai_compatible"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"


class ModelProvider(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("provider"), primary_key=True)
    name: str = Field(index=True, unique=True)
    kind: ProviderKind
    base_url: str
    default_model: str
    api_key_ciphertext: str
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
```

- [ ] **Step 5: Implement agent model**

Write `src/noviscope/models/agent.py`:

```python
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
```

- [ ] **Step 6: Implement quest models**

Write `src/noviscope/models/quest.py`:

```python
from enum import StrEnum

from sqlmodel import Field, SQLModel

from noviscope.models.common import new_id, utc_now


class QuestStatus(StrEnum):
    DRAFT = "draft"
    DEMAND_REVIEW = "demand_review"
    IDEA_SELECTION = "idea_selection"
    LIGHTWEIGHT_EXPERIMENT = "lightweight_experiment"
    FULL_EXPERIMENT = "full_experiment"
    WRITING = "writing"
    COMPLETE = "complete"
    ARCHIVED = "archived"


class StageStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    BLOCKED = "blocked"
    COMPLETE = "complete"


class Quest(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("quest"), primary_key=True)
    title: str
    initial_direction: str
    status: QuestStatus = Field(default=QuestStatus.DRAFT, index=True)
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    updated_at: str = Field(default_factory=lambda: utc_now().isoformat())


class StageCard(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("stage"), primary_key=True)
    quest_id: str = Field(index=True, foreign_key="quest.id")
    agent_id: str = Field(index=True)
    title: str
    status: StageStatus = Field(default=StageStatus.PENDING)
    summary: str = ""
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
```

- [ ] **Step 7: Import models in pytest fixture before metadata creation**

Modify `tests/conftest.py` to include model imports before `SQLModel.metadata.create_all(engine)`:

```python
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from noviscope.models.agent import AgentAssignment  # noqa: F401
from noviscope.models.provider import ModelProvider  # noqa: F401
from noviscope.models.quest import Quest, StageCard  # noqa: F401


@pytest.fixture()
def test_db_path(tmp_path: Path) -> Path:
    return tmp_path / "noviscope-test.db"


@pytest.fixture()
def test_engine(test_db_path: Path):
    engine = create_engine(f"sqlite:///{test_db_path}")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture()
def db_session(test_engine) -> Generator[Session, None, None]:
    with Session(test_engine) as session:
        yield session
```

- [ ] **Step 8: Verify model test passes**

Run:

```bash
pytest tests/test_quests.py::test_provider_and_quest_persist -v
```

Expected: 1 passed.

- [ ] **Step 9: Commit domain models**

```bash
git add src/noviscope/models tests/conftest.py tests/test_quests.py
git commit -m "feat: add domain models for providers and quests"
```

## Task 4: Agent Registry

**Files:**
- Create: `src/noviscope/agents/__init__.py`
- Create: `src/noviscope/agents/registry.py`
- Create: `tests/test_agents.py`

- [ ] **Step 1: Write agent registry test**

Write `tests/test_agents.py`:

```python
from noviscope.agents.registry import AGENT_REGISTRY, get_agent_spec
from noviscope.models.agent import ToolPermission


def test_registry_has_nine_agents():
    assert len(AGENT_REGISTRY) == 9


def test_code_runner_is_only_agent_with_run_code_permission():
    runners = [
        spec.agent_id
        for spec in AGENT_REGISTRY.values()
        if ToolPermission.RUN_CODE in spec.tool_permissions
    ]
    assert runners == ["code_runner"]


def test_writer_cannot_run_code_or_freely_search_github():
    writer = get_agent_spec("paper_meeting_writer")
    assert ToolPermission.RUN_CODE not in writer.tool_permissions
    assert ToolPermission.GITHUB_SEARCH not in writer.tool_permissions
```

- [ ] **Step 2: Run registry test to verify failure**

Run:

```bash
pytest tests/test_agents.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'noviscope.agents'`.

- [ ] **Step 3: Implement agent registry**

Write `src/noviscope/agents/__init__.py`:

```python
"""NoviScope agent contracts."""
```

Write `src/noviscope/agents/registry.py`:

```python
from pydantic import BaseModel

from noviscope.models.agent import ToolPermission


class AgentSpec(BaseModel):
    agent_id: str
    display_name: str
    goal: str
    outputs: list[str]
    tool_permissions: set[ToolPermission]
    constraints: list[str]


AGENT_REGISTRY: dict[str, AgentSpec] = {
    "demand_validator": AgentSpec(
        agent_id="demand_validator",
        display_name="Demand Validator",
        goal="Validate whether a direction reflects a real application demand.",
        outputs=["demand_validation_report", "demand_confidence", "source_risk_list"],
        tool_permissions={
            ToolPermission.WEB_SEARCH,
            ToolPermission.READ_PDF,
            ToolPermission.GITHUB_SEARCH,
            ToolPermission.WRITE_FILES,
        },
        constraints=[
            "Weak sources must be marked low_confidence.",
            "Experiment stages require a user demand-review decision.",
        ],
    ),
    "research_refiner": AgentSpec(
        agent_id="research_refiner",
        display_name="Research Refiner",
        goal="Convert a broad direction into a scoped computer-vision research question.",
        outputs=["research_question_brief", "scope", "keywords"],
        tool_permissions={ToolPermission.READ_PDF, ToolPermission.WRITE_FILES},
        constraints=["Do not produce paper conclusions."],
    ),
    "literature_scout": AgentSpec(
        agent_id="literature_scout",
        display_name="Literature Scout",
        goal="Build a paper, code, dataset, and baseline map.",
        outputs=["bibliography_matrix", "method_taxonomy", "baseline_candidates"],
        tool_permissions={
            ToolPermission.WEB_SEARCH,
            ToolPermission.READ_PDF,
            ToolPermission.GITHUB_SEARCH,
            ToolPermission.WRITE_FILES,
        },
        constraints=["Every core paper requires URL or DOI, venue, and year."],
    ),
    "gap_analyst": AgentSpec(
        agent_id="gap_analyst",
        display_name="Gap Analyst",
        goal="Identify limitations, uncovered scenarios, and improvement space.",
        outputs=["gap_matrix", "limitation_map", "application_constraint_map"],
        tool_permissions={
            ToolPermission.WEB_SEARCH,
            ToolPermission.READ_PDF,
            ToolPermission.GITHUB_SEARCH,
            ToolPermission.WRITE_FILES,
        },
        constraints=["Separate cited limitations from system inferences."],
    ),
    "idea_generator": AgentSpec(
        agent_id="idea_generator",
        display_name="Idea Generator",
        goal="Generate evidence-linked research hypotheses and candidate ideas.",
        outputs=["candidate_ideas", "idea_risk_table"],
        tool_permissions={ToolPermission.READ_PDF, ToolPermission.WRITE_FILES},
        constraints=["Every idea must include an experiment that could falsify it."],
    ),
    "experiment_planner": AgentSpec(
        agent_id="experiment_planner",
        display_name="Experiment Planner",
        goal="Turn selected ideas into lightweight and full experiment plans.",
        outputs=["experiment_plan", "ablation_plan", "metric_plan"],
        tool_permissions={
            ToolPermission.WEB_SEARCH,
            ToolPermission.READ_PDF,
            ToolPermission.GITHUB_SEARCH,
            ToolPermission.WRITE_FILES,
            ToolPermission.READ_EXPERIMENT_RESULTS,
        },
        constraints=["Do not execute code."],
    ),
    "code_runner": AgentSpec(
        agent_id="code_runner",
        display_name="Code Runner",
        goal="Run local reproduction, training, evaluation, and ablation jobs.",
        outputs=["experiment_provenance", "run_logs", "metric_records"],
        tool_permissions={
            ToolPermission.WEB_SEARCH,
            ToolPermission.READ_PDF,
            ToolPermission.GITHUB_SEARCH,
            ToolPermission.WRITE_FILES,
            ToolPermission.RUN_CODE,
            ToolPermission.READ_EXPERIMENT_RESULTS,
        },
        constraints=["Private code, data, logs, and checkpoints must not be uploaded."],
    ),
    "evidence_auditor": AgentSpec(
        agent_id="evidence_auditor",
        display_name="Evidence Auditor",
        goal="Audit source truth, claim-reference alignment, and experiment-claim alignment.",
        outputs=["source_verification_report", "claim_alignment_report", "blocking_issues"],
        tool_permissions={
            ToolPermission.WEB_SEARCH,
            ToolPermission.READ_PDF,
            ToolPermission.GITHUB_SEARCH,
            ToolPermission.WRITE_FILES,
            ToolPermission.READ_EXPERIMENT_RESULTS,
        },
        constraints=["Read-only audit; do not rewrite experiment outcomes."],
    ),
    "paper_meeting_writer": AgentSpec(
        agent_id="paper_meeting_writer",
        display_name="Paper & Meeting Writer",
        goal="Generate English IEEE draft, Chinese draft, and Chinese meeting slides.",
        outputs=["english_ieee_draft", "chinese_draft", "chinese_meeting_deck"],
        tool_permissions={
            ToolPermission.READ_PDF,
            ToolPermission.WRITE_FILES,
            ToolPermission.READ_EXPERIMENT_RESULTS,
            ToolPermission.WRITE_PAPER,
            ToolPermission.WRITE_PPT,
        },
        constraints=["Use only verified or weak evidence; weak evidence cannot enter conclusions."],
    ),
}


def get_agent_spec(agent_id: str) -> AgentSpec:
    return AGENT_REGISTRY[agent_id]
```

- [ ] **Step 4: Verify registry tests pass**

Run:

```bash
pytest tests/test_agents.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit agent registry**

```bash
git add src/noviscope/agents tests/test_agents.py
git commit -m "feat: add NoviScope agent registry"
```

## Task 5: Model Gateway Foundation

**Files:**
- Create: `src/noviscope/model_gateway/__init__.py`
- Create: `src/noviscope/model_gateway/adapters.py`
- Create: `src/noviscope/model_gateway/service.py`
- Create: `tests/test_model_gateway.py`

- [ ] **Step 1: Write model gateway tests**

Write `tests/test_model_gateway.py`:

```python
from noviscope.model_gateway.adapters import EchoAdapter
from noviscope.model_gateway.service import ModelGateway, ProviderProfile


def test_gateway_registers_and_tests_provider():
    gateway = ModelGateway()
    gateway.register_adapter("openai_compatible", EchoAdapter())
    profile = ProviderProfile(
        provider_id="provider_1",
        kind="openai_compatible",
        base_url="https://api.example.com/v1",
        api_key="sk-test",
        default_model="example-chat",
    )

    result = gateway.test_connection(profile)

    assert result.ok is True
    assert result.model == "example-chat"


def test_unknown_provider_kind_fails_connection_test():
    gateway = ModelGateway()
    profile = ProviderProfile(
        provider_id="provider_2",
        kind="missing",
        base_url="https://api.example.com/v1",
        api_key="sk-test",
        default_model="example-chat",
    )

    result = gateway.test_connection(profile)

    assert result.ok is False
    assert "No adapter registered" in result.message
```

- [ ] **Step 2: Run gateway tests to verify failure**

Run:

```bash
pytest tests/test_model_gateway.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'noviscope.model_gateway'`.

- [ ] **Step 3: Implement adapter protocol and echo adapter**

Write `src/noviscope/model_gateway/__init__.py`:

```python
"""Model gateway abstractions."""
```

Write `src/noviscope/model_gateway/adapters.py`:

```python
from typing import Protocol


class ProviderAdapter(Protocol):
    def test_connection(self, *, base_url: str, api_key: str, model: str) -> tuple[bool, str]:
        """Return connection status and human-readable message."""


class EchoAdapter:
    def test_connection(self, *, base_url: str, api_key: str, model: str) -> tuple[bool, str]:
        if not base_url.startswith("http"):
            return False, "base_url must start with http"
        if not api_key:
            return False, "api_key is required"
        if not model:
            return False, "model is required"
        return True, "connection parameters accepted"
```

- [ ] **Step 4: Implement gateway service**

Write `src/noviscope/model_gateway/service.py`:

```python
from pydantic import BaseModel

from noviscope.model_gateway.adapters import ProviderAdapter


class ProviderProfile(BaseModel):
    provider_id: str
    kind: str
    base_url: str
    api_key: str
    default_model: str


class ConnectionTestResult(BaseModel):
    ok: bool
    provider_id: str
    model: str
    message: str


class ModelGateway:
    def __init__(self) -> None:
        self._adapters: dict[str, ProviderAdapter] = {}

    def register_adapter(self, kind: str, adapter: ProviderAdapter) -> None:
        self._adapters[kind] = adapter

    def test_connection(self, profile: ProviderProfile) -> ConnectionTestResult:
        adapter = self._adapters.get(profile.kind)
        if adapter is None:
            return ConnectionTestResult(
                ok=False,
                provider_id=profile.provider_id,
                model=profile.default_model,
                message=f"No adapter registered for provider kind {profile.kind}",
            )
        ok, message = adapter.test_connection(
            base_url=profile.base_url,
            api_key=profile.api_key,
            model=profile.default_model,
        )
        return ConnectionTestResult(
            ok=ok,
            provider_id=profile.provider_id,
            model=profile.default_model,
            message=message,
        )
```

- [ ] **Step 5: Verify gateway tests pass**

Run:

```bash
pytest tests/test_model_gateway.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Commit model gateway foundation**

```bash
git add src/noviscope/model_gateway tests/test_model_gateway.py
git commit -m "feat: add model gateway foundation"
```

## Task 6: Quest Service

**Files:**
- Create: `src/noviscope/quests/__init__.py`
- Create: `src/noviscope/quests/service.py`
- Modify: `tests/test_quests.py`

- [ ] **Step 1: Add quest service tests**

Append to `tests/test_quests.py`:

```python
from noviscope.quests.service import QuestService


def test_create_quest_adds_demand_validation_stage(db_session: Session):
    service = QuestService(db_session)

    quest = service.create_quest(
        title="AI+Sports Badminton",
        initial_direction="AI+体育，偏羽毛球相关",
    )

    stages = service.list_stage_cards(quest.id)

    assert quest.status == QuestStatus.DRAFT
    assert len(stages) == 1
    assert stages[0].agent_id == "demand_validator"
    assert stages[0].title == "Demand validation"
```

- [ ] **Step 2: Run service test to verify failure**

Run:

```bash
pytest tests/test_quests.py::test_create_quest_adds_demand_validation_stage -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'noviscope.quests'`.

- [ ] **Step 3: Implement quest service**

Write `src/noviscope/quests/__init__.py`:

```python
"""Research quest workflow services."""
```

Write `src/noviscope/quests/service.py`:

```python
from sqlmodel import Session, select

from noviscope.models.quest import Quest, StageCard, StageStatus


class QuestService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_quest(self, *, title: str, initial_direction: str) -> Quest:
        quest = Quest(title=title, initial_direction=initial_direction)
        stage = StageCard(
            quest_id=quest.id,
            agent_id="demand_validator",
            title="Demand validation",
            status=StageStatus.PENDING,
            summary="Validate real-world demand before literature and experiment stages.",
        )
        self.session.add(quest)
        self.session.add(stage)
        self.session.commit()
        self.session.refresh(quest)
        return quest

    def list_stage_cards(self, quest_id: str) -> list[StageCard]:
        statement = select(StageCard).where(StageCard.quest_id == quest_id)
        return list(self.session.exec(statement).all())
```

- [ ] **Step 4: Verify quest service tests pass**

Run:

```bash
pytest tests/test_quests.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit quest service**

```bash
git add src/noviscope/quests tests/test_quests.py
git commit -m "feat: add research quest service"
```

## Task 7: FastAPI API

**Files:**
- Create: `src/noviscope/db/__init__.py`
- Create: `src/noviscope/db/session.py`
- Create: `src/noviscope/api/__init__.py`
- Create: `src/noviscope/api/routes.py`
- Create: `src/noviscope/main.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: Write API tests**

Write `tests/test_api.py`:

```python
from fastapi.testclient import TestClient

from noviscope.main import create_app


def test_health_endpoint():
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_agents_endpoint_lists_nine_agents():
    client = TestClient(create_app())

    response = client.get("/agents")

    assert response.status_code == 200
    assert len(response.json()["agents"]) == 9


def test_create_quest_endpoint():
    client = TestClient(create_app(database_url="sqlite:///:memory:"))

    response = client.post(
        "/quests",
        json={"title": "AI+Sports Badminton", "initial_direction": "AI+体育，羽毛球"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "AI+Sports Badminton"
    assert body["first_stage"]["agent_id"] == "demand_validator"
```

- [ ] **Step 2: Run API tests to verify failure**

Run:

```bash
pytest tests/test_api.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'noviscope.main'`.

- [ ] **Step 3: Implement database session helpers**

Write `src/noviscope/db/__init__.py`:

```python
"""Database setup helpers."""
```

Write `src/noviscope/db/session.py`:

```python
from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from noviscope.models.agent import AgentAssignment  # noqa: F401
from noviscope.models.provider import ModelProvider  # noqa: F401
from noviscope.models.quest import Quest, StageCard  # noqa: F401


def create_db_engine(database_url: str):
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


def create_schema(engine) -> None:
    SQLModel.metadata.create_all(engine)


def session_generator(engine) -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
```

- [ ] **Step 4: Implement API routes**

Write `src/noviscope/api/__init__.py`:

```python
"""HTTP API package."""
```

Write `src/noviscope/api/routes.py`:

```python
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlmodel import Session

from noviscope.agents.registry import AGENT_REGISTRY
from noviscope.quests.service import QuestService


router = APIRouter()


class QuestCreateRequest(BaseModel):
    title: str
    initial_direction: str


def get_session() -> Session:
    raise RuntimeError("session dependency must be overridden by create_app")


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/agents")
def list_agents():
    return {"agents": [spec.model_dump(mode="json") for spec in AGENT_REGISTRY.values()]}


@router.post("/quests", status_code=status.HTTP_201_CREATED)
def create_quest(
    request: QuestCreateRequest,
    session: Annotated[Session, Depends(get_session)],
):
    service = QuestService(session)
    quest = service.create_quest(
        title=request.title,
        initial_direction=request.initial_direction,
    )
    first_stage = service.list_stage_cards(quest.id)[0]
    return {
        "id": quest.id,
        "title": quest.title,
        "initial_direction": quest.initial_direction,
        "status": quest.status,
        "first_stage": first_stage.model_dump(mode="json"),
    }
```

- [ ] **Step 5: Implement app factory**

Write `src/noviscope/main.py`:

```python
from collections.abc import Generator

from fastapi import FastAPI
from sqlmodel import Session

from noviscope.api.routes import get_session, router
from noviscope.core.config import get_settings
from noviscope.db.session import create_db_engine, create_schema


def create_app(database_url: str | None = None) -> FastAPI:
    settings = get_settings()
    engine = create_db_engine(database_url or settings.database_url)
    create_schema(engine)

    app = FastAPI(title=settings.app_name)
    app.include_router(router)

    def session_dependency() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_dependency
    return app


app = create_app()
```

- [ ] **Step 6: Verify API tests pass**

Run:

```bash
pytest tests/test_api.py -v
```

Expected: 3 passed.

- [ ] **Step 7: Run the full test suite**

Run:

```bash
pytest
```

Expected: all tests pass.

- [ ] **Step 8: Commit FastAPI API**

```bash
git add src/noviscope/api src/noviscope/db src/noviscope/main.py tests/test_api.py
git commit -m "feat: expose foundation API"
```

## Task 8: Lint and Final Verification

**Files:**
- Modify only files needed to satisfy lint if ruff reports issues.

- [ ] **Step 1: Run ruff**

Run:

```bash
ruff check .
```

Expected: no lint errors.

- [ ] **Step 2: Run full tests**

Run:

```bash
pytest
```

Expected: all tests pass.

- [ ] **Step 3: Smoke-test local API**

Run:

```bash
uvicorn noviscope.main:app --host 127.0.0.1 --port 8000
```

In a second shell:

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/agents
curl -s -X POST http://127.0.0.1:8000/quests \
  -H 'Content-Type: application/json' \
  -d '{"title":"AI+Sports Badminton","initial_direction":"AI+体育，羽毛球"}'
```

Expected:

```text
{"status":"ok"}
```

The `/agents` response contains 9 agents. The `/quests` response contains a quest id and `first_stage.agent_id` equal to `demand_validator`.

- [ ] **Step 4: Commit verification fixes if any file changed**

If `git status --short` shows changes after lint or smoke testing:

```bash
git add <changed-files>
git commit -m "chore: verify foundation slice"
```

If no files changed, do not create an empty commit.

## Self-Review Checklist

- Spec coverage:
  - Project scaffold and GitHub-safe repo baseline: Task 1.
  - API-first backend foundation: Task 7.
  - Model Gateway provider abstraction: Task 5.
  - 9-agent team and tool permissions: Task 4.
  - Quest state and first demand-validation stage: Tasks 3 and 6.
  - Private data upload guard: Task 2.
  - Testable working slice: Tasks 1-8.
- Deliberately excluded from this plan:
  - Real literature retrieval APIs.
  - Demand evidence crawling.
  - GPU job execution.
  - Evidence auditor implementation.
  - Paper and PPT generation.
  - Web frontend.
- Placeholder scan: this plan contains no unresolved markers or vague file path references.
- Type consistency:
  - `ProviderKind.OPENAI_COMPATIBLE` maps to gateway kind string `openai_compatible`.
  - Agent IDs in `AGENT_REGISTRY` match stage card `agent_id` values.
  - `QuestStatus.DRAFT` and `StageStatus.PENDING` are used consistently across tests and service code.
