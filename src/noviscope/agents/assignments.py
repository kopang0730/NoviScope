from sqlmodel import Session, select

from noviscope.agents.registry import AGENT_REGISTRY
from noviscope.models.agent import AgentAssignment


class AgentAssignmentService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_assignments(self) -> list[AgentAssignment]:
        assignments = self.session.exec(select(AgentAssignment)).all()
        order = {agent_id: index for index, agent_id in enumerate(AGENT_REGISTRY)}
        return sorted(assignments, key=lambda assignment: order.get(assignment.agent_id, 999))

    def get_assignment(self, agent_id: str) -> AgentAssignment | None:
        self.ensure_known_agent(agent_id)
        return self.session.get(AgentAssignment, agent_id)

    def upsert_assignment(
        self,
        agent_id: str,
        *,
        provider_id: str,
        model_name: str | None = None,
    ) -> AgentAssignment:
        self.ensure_known_agent(agent_id)
        assignment = self.session.get(AgentAssignment, agent_id)
        if assignment is None:
            assignment = AgentAssignment(agent_id=agent_id)
        assignment.provider_id = provider_id
        assignment.model_name = normalize_model_name(model_name)
        self.session.add(assignment)
        self.session.commit()
        self.session.refresh(assignment)
        return assignment

    def clear_assignment(self, agent_id: str) -> AgentAssignment:
        self.ensure_known_agent(agent_id)
        assignment = self.session.get(AgentAssignment, agent_id)
        if assignment is None:
            assignment = AgentAssignment(agent_id=agent_id)
        assignment.provider_id = None
        assignment.model_name = None
        self.session.add(assignment)
        self.session.commit()
        self.session.refresh(assignment)
        return assignment

    def clear_provider_assignments(self, provider_id: str) -> None:
        assignments = self.session.exec(
            select(AgentAssignment).where(AgentAssignment.provider_id == provider_id)
        ).all()
        for assignment in assignments:
            assignment.provider_id = None
            assignment.model_name = None
            self.session.add(assignment)

    @staticmethod
    def ensure_known_agent(agent_id: str) -> None:
        if agent_id not in AGENT_REGISTRY:
            raise LookupError(f"Agent {agent_id} not found")


def normalize_model_name(model_name: str | None) -> str | None:
    if model_name is None:
        return None
    stripped = model_name.strip()
    return stripped or None
