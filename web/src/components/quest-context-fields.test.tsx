import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { I18nProvider } from "../i18n/i18n-context";
import { emptyIntake, questIntakeExamples, type QuestContextField, type QuestIntakeState } from "../lib/quest-intake";
import { QuestContextFields } from "./quest-context-fields";

function renderContextFields(formState: QuestIntakeState) {
  const onFieldChange = vi.fn<(field: QuestContextField, value: string) => void>();

  render(
    <I18nProvider>
      <QuestContextFields formState={formState} onFieldChange={onFieldChange} />
    </I18nProvider>,
  );

  return { onFieldChange };
}

describe("QuestContextFields", () => {
  beforeEach(() => {
    window.localStorage.setItem("noviscope-language", "en");
  });

  afterEach(() => {
    cleanup();
  });

  it("keeps additional research context hidden for a new intake", () => {
    // Given
    renderContextFields(emptyIntake);

    // When
    const scenarioField = screen.queryByRole("textbox", { name: /^Real-world scenario or demand source/ });

    // Then
    expect(scenarioField).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add research context" })).toBeInTheDocument();
  });

  it("reveals demand reality and experiment readiness fields on request", async () => {
    // Given
    const user = userEvent.setup();
    renderContextFields(emptyIntake);

    // When
    await user.click(screen.getByRole("button", { name: "Add research context" }));

    // Then
    expect(screen.getByRole("heading", { name: "Demand Reality" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Experiment Readiness" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /^Real-world scenario or demand source/ })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /^Data, code, or resources already available/ })).toBeInTheDocument();
  });

  it("opens automatically when an example includes additional context", () => {
    // Given
    renderContextFields(questIntakeExamples.en.erasure);

    // When
    const evidenceField = screen.getByRole("textbox", { name: /^Demand evidence sources to verify/ });

    // Then
    expect(evidenceField).toBeInTheDocument();
  });

  it("keeps visible labels for every disclosed context control", async () => {
    // Given
    const user = userEvent.setup();
    renderContextFields(emptyIntake);

    // When
    await user.click(screen.getByRole("button", { name: "Add research context" }));

    // Then
    expect(screen.getByLabelText(/^Real-world scenario or demand source/)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Demand evidence sources to verify/)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Target user or customer/)).toBeInTheDocument();
    expect(screen.getByLabelText("Input and desired output")).toBeInTheDocument();
    expect(screen.getByLabelText("Current pain point or suspected gap")).toBeInTheDocument();
    expect(screen.getByLabelText(/^Known papers, methods, or baselines/)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Data, code, or resources already available/)).toBeInTheDocument();
    expect(screen.getByLabelText("Evaluation metric or success signal")).toBeInTheDocument();
    expect(screen.getByLabelText("Expected research output")).toBeInTheDocument();
  });
});
