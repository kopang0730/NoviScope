import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getAgentAssignments } from "../api/agent-assignments";
import { getCurrentUser } from "../api/auth";
import { getProviders } from "../api/providers";
import { getQuest, getQuestStages, getQuests, runStage } from "../api/quests";
import type { Quest, StageCard, User } from "../api/types";
import { getWorkflowCapabilities } from "../api/workflow";
import { AuthProvider } from "../auth/auth-context";
import { I18nProvider } from "../i18n/i18n-context";
import { QuestListPage } from "./quest-list";

vi.mock("../api/agent-assignments", () => ({ getAgentAssignments: vi.fn() }));
vi.mock("../api/auth", () => ({ getCurrentUser: vi.fn(), logoutUser: vi.fn() }));
vi.mock("../api/providers", () => ({ getProviders: vi.fn() }));
vi.mock("../api/quests", () => ({
  getQuest: vi.fn(),
  getQuestStages: vi.fn(),
  getQuests: vi.fn(),
  runStage: vi.fn(),
}));
vi.mock("../api/workflow", () => ({ getWorkflowCapabilities: vi.fn() }));

const timestamp = "2026-07-10T00:00:00Z";
const user: User = {
  created_at: timestamp,
  display_name: "Researcher",
  email: "researcher@example.com",
  id: "user-1",
  is_active: true,
  role: "member",
  updated_at: timestamp,
};

const quest: Quest = {
  created_at: timestamp,
  id: "quest-1",
  initial_direction: "Analyze badminton serve technique.",
  owner_user_id: user.id,
  status: "draft",
  title: "Badminton Quest",
  updated_at: timestamp,
};

const stage: StageCard = {
  agent_id: "demand_validator",
  confidence: "unknown",
  created_at: timestamp,
  evidence_payload: {},
  human_approved: null,
  id: "stage-1",
  input_payload: {},
  output_payload: {},
  quest_id: quest.id,
  review_notes: "",
  status: "pending",
  summary: "",
  title: "Demand Validator",
  updated_at: timestamp,
};

function renderQuestList() {
  return render(
    <MemoryRouter initialEntries={["/quests?quest=quest-1"]}>
      <AuthProvider>
        <I18nProvider>
          <Routes>
            <Route element={<QuestListPage />} path="/quests" />
          </Routes>
        </I18nProvider>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("QuestListPage legacy route", () => {
  afterEach(cleanup);

  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.setItem("noviscope-language", "en");
    vi.mocked(getAgentAssignments).mockResolvedValue([]);
    vi.mocked(getCurrentUser).mockResolvedValue(user);
    vi.mocked(getProviders).mockResolvedValue([]);
    vi.mocked(getQuest).mockResolvedValue(quest);
    vi.mocked(getQuestStages).mockResolvedValue([stage]);
    vi.mocked(getQuests).mockResolvedValue([quest]);
    vi.mocked(getWorkflowCapabilities).mockResolvedValue([]);
    vi.mocked(runStage).mockResolvedValue(stage);
  });

  it("keeps the Quest overview reachable without exposing local run workflow controls", async () => {
    renderQuestList();

    await screen.findByRole("heading", { name: "Quest list" });
    await waitFor(() => expect(screen.getAllByText("Badminton Quest").length).toBeGreaterThan(0));
    await waitFor(() => expect(screen.queryByText("Loading Quest detail...")).not.toBeInTheDocument());

    const [openCanvasLink] = screen.getAllByRole("link", { name: "Open full canvas" });
    expect(openCanvasLink).toHaveAttribute("href", "/canvas?quest=quest-1");
    expect(screen.queryByRole("button", { name: /canvas/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /list/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /run/i })).not.toBeInTheDocument();
  });
});
