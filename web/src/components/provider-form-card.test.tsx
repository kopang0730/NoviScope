import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { User } from "../api/types";
import { I18nProvider } from "../i18n/i18n-context";
import { initialProviderFormState } from "../lib/provider-form";
import { ProviderFormCard } from "./provider-form-card";

const user: User = {
  created_at: "2026-07-11T00:00:00Z",
  display_name: "Researcher",
  email: "researcher@example.test",
  id: "user-1",
  is_active: true,
  role: "member",
  updated_at: "2026-07-11T00:00:00Z",
};

describe("ProviderFormCard", () => {
  afterEach(cleanup);

  beforeEach(() => {
    window.localStorage.setItem("noviscope-language", "en");
  });

  it("lets OpenAI-compatible providers select the Responses API", async () => {
    const onUpdate = vi.fn();
    const browserUser = userEvent.setup();
    render(
      <I18nProvider>
        <ProviderFormCard
          currentUser={user}
          formState={initialProviderFormState}
          isEditing={false}
          onCancelEdit={vi.fn()}
          onSubmit={vi.fn()}
          onUpdate={onUpdate}
          scope="personal"
          submitError={null}
          submitting={false}
        />
      </I18nProvider>,
    );

    await browserUser.selectOptions(
      screen.getByRole("combobox", { name: /^OpenAI API mode/ }),
      "responses",
    );

    expect(onUpdate).toHaveBeenCalledWith({
      ...initialProviderFormState,
      apiMode: "responses",
    });
  });

  it("resets API mode when switching to Anthropic", async () => {
    const onUpdate = vi.fn();
    const browserUser = userEvent.setup();
    render(
      <I18nProvider>
        <ProviderFormCard
          currentUser={user}
          formState={{ ...initialProviderFormState, apiMode: "responses" }}
          isEditing={false}
          onCancelEdit={vi.fn()}
          onSubmit={vi.fn()}
          onUpdate={onUpdate}
          scope="personal"
          submitError={null}
          submitting={false}
        />
      </I18nProvider>,
    );

    await browserUser.selectOptions(
      screen.getByRole("combobox", { name: "Provider Kind" }),
      "anthropic",
    );

    expect(onUpdate).toHaveBeenCalledWith({
      ...initialProviderFormState,
      apiMode: "auto",
      kind: "anthropic",
    });
  });
});
