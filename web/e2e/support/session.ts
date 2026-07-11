import { expect, type Page } from "@playwright/test";

type AccountRole = "admin" | "member";

type Credentials = {
  readonly email: string;
  readonly password: string;
};

class MissingE2EEnvironmentError extends Error {
  readonly variableName: string;

  constructor(variableName: string) {
    super(`${variableName} is required for NoviScope E2E`);
    this.name = "MissingE2EEnvironmentError";
    this.variableName = variableName;
  }
}

function requiredEnvironmentValue(variableName: string): string {
  const value = process.env[variableName];
  if (!value) {
    throw new MissingE2EEnvironmentError(variableName);
  }
  return value;
}

function credentialsFor(role: AccountRole): Credentials {
  const prefix = role === "admin" ? "NOVISCOPE_E2E_ADMIN" : "NOVISCOPE_E2E_MEMBER";
  return {
    email: requiredEnvironmentValue(`${prefix}_EMAIL`),
    password: requiredEnvironmentValue(`${prefix}_PASSWORD`),
  };
}

export async function loginAs(page: Page, role: AccountRole): Promise<void> {
  const credentials = credentialsFor(role);
  await page.goto("/login");
  await page.getByRole("button", { name: "English" }).click();
  await page.getByRole("textbox", { name: "Email" }).fill(credentials.email);
  await page.getByLabel("Password").fill(credentials.password);
  await page.getByRole("button", { name: "Sign In" }).click();
  await expect(page).toHaveURL(/\/canvas(?:\?|$)/);
}

export async function selectSeededQuest(page: Page): Promise<void> {
  await page.goto("/canvas");
  const selector = page.getByRole("combobox", { name: "Quest" });
  if (await selector.isVisible()) {
    await selector.selectOption({ label: "Badminton Performance Analysis" });
  } else {
    await page.getByRole("button", { name: /Badminton Performance Analysis/ }).click();
  }
  await expect(
    page.getByRole("heading", { exact: true, name: "Badminton Performance Analysis" }),
  ).toBeVisible();
}
