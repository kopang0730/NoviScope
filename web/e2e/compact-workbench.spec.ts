import { expect, test, type Page } from "@playwright/test";
import {
  assertPageQuality,
  assertTabsStayOnOneRow,
  assertTextFits,
  captureState,
} from "./support/quality";
import { loginAs, selectSeededQuest } from "./support/session";

const runtimeErrors = new WeakMap<Page, string[]>();
const roleNames = [
  "Demand Validator",
  "Research Refiner",
  "Literature Scout",
  "Gap Analyst",
  "Idea Generator",
  "Experiment Planner",
  "Code Runner",
  "Evidence Auditor",
  "Paper & Meeting Writer",
];

async function assertMobileCanvasFocusOrder(page: Page): Promise<void> {
  if (page.viewportSize()?.width !== 390) {
    return;
  }
  const targets = [
    page.getByRole("combobox", { name: "Quest" }),
    page.getByRole("button", { name: "Run agent" }),
    page.getByRole("button", { name: /^Phase 1:/ }),
    page.getByRole("tab", { name: "Overview" }),
  ];
  const reached: number[] = [];
  await page.evaluate(() => {
    if (document.activeElement instanceof HTMLElement) {
      document.activeElement.blur();
    }
  });
  for (let step = 0; step < 80 && reached.length < targets.length; step += 1) {
    await page.keyboard.press("Tab");
    for (const [index, target] of targets.entries()) {
      const isFocused = await target.evaluate((element) => element === document.activeElement);
      if (isFocused && !reached.includes(index)) {
        reached.push(index);
      }
    }
  }
  expect(reached).toEqual([0, 1, 2, 3]);
}

test.beforeEach(({ page }) => {
  const errors: string[] = [];
  runtimeErrors.set(page, errors);
  page.on("console", (message) => {
    if (message.type() === "error") {
      errors.push(message.text());
    }
  });
  page.on("pageerror", (error) => errors.push(error.message));
});

test.afterEach(({ page }) => {
  expect(runtimeErrors.get(page) ?? []).toEqual([]);
});

test.describe.serial("compact Canvas workbench", () => {
  test("1. logs in and selects the seeded Quest", async ({ page }) => {
    await loginAs(page, "member");
    await selectSeededQuest(page);
    await expect(page.getByRole("heading", { name: "Next action" })).toBeVisible();
  });

  test("2. shows one runnable next action in the first viewport", async ({ page }, testInfo) => {
    await loginAs(page, "member");
    await selectSeededQuest(page);
    const nextAction = page.getByRole("heading", { name: "Next action" });
    const primaryCommand = page.getByRole("button", { name: "Run agent" });
    await expect(nextAction).toHaveCount(1);
    await expect(nextAction).toBeInViewport();
    await expect(primaryCommand).toBeInViewport();
    await captureState(page, testInfo, "canvas-runnable");
    await assertPageQuality(page, testInfo, "canvas-runnable");
    await assertMobileCanvasFocusOrder(page);
  });

  test("3-4. navigates five phases and keeps planned roles disabled", async ({ page }, testInfo) => {
    await loginAs(page, "member");
    await selectSeededQuest(page);
    const phases = page.getByRole("button", { name: /^Phase \d:/ });
    await expect(phases).toHaveCount(5);
    for (const roleName of roleNames) {
      const role = page.getByRole("status", { name: new RegExp(roleName) });
      await expect(role).toBeVisible();
      await assertTextFits(role);
    }
    await expect(
      page.getByRole("status", { name: "Code Runner: Planned" }),
    ).toHaveAttribute("aria-disabled", "true");
    await expect(
      page.getByRole("status", { name: "Evidence Auditor: Planned" }),
    ).toHaveAttribute("aria-disabled", "true");
    for (let index = 0; index < 5; index += 1) {
      await phases.nth(index).click();
      await expect(phases.nth(index)).toHaveAttribute("aria-pressed", "true");
    }
    await phases.first().focus();
    await page.keyboard.press("ArrowRight");
    await expect(phases.nth(1)).toBeFocused();
    await phases.nth(3).click();
    await captureState(page, testInfo, "canvas-planned-experiment-roles");
    await expect(page.getByRole("tabpanel")).toHaveCount(1);
  });

  test("5-7. creates, runs with a personal provider, and opens review detail", async ({ page }, testInfo) => {
    await loginAs(page, "member");
    await page.goto("/quests/new");
    const direction = `Analyze badminton serve technique for ${testInfo.project.name} E2E`;
    await page.getByRole("textbox", { name: /^Research direction/ }).fill(direction);
    await expect(page.getByText(/Human review required/)).toBeVisible();
    await expect(page.getByRole("button", { name: "Create Quest" })).toBeInViewport();
    await captureState(page, testInfo, "new-quest-collapsed");
    await page.getByRole("button", { name: "Add research context" }).click();
    await expect(page.getByRole("heading", { name: "Demand Reality" })).toBeVisible();
    await captureState(page, testInfo, "new-quest-expanded");
    await assertPageQuality(page, testInfo, "new-quest");
    await page.getByRole("button", { name: "Create Quest" }).click();
    await expect(page.getByRole("heading", { exact: true, name: direction })).toBeVisible();

    await page.getByRole("combobox", { name: "Provider override" }).selectOption({
      label: "NoviScope E2E Personal · Personal",
    });
    await page.getByRole("button", { name: "Run agent" }).click();
    await expect(page.getByRole("link", { name: "Human review" })).toBeVisible();
    await captureState(page, testInfo, "canvas-human-review-blocker");

    await page.getByRole("tab", { name: "Evidence" }).click();
    await expect(page.getByText(/Stored evidence/)).toBeVisible();
    await page.getByRole("tab", { name: "Review" }).click();
    await page.getByRole("link", { name: "Open Stage Detail" }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Demand validation" })).toBeVisible();
    if (page.viewportSize()?.width === 390) {
      await assertTabsStayOnOneRow(page.getByRole("tablist", { name: "Stage workbench" }));
    }
    await captureState(page, testInfo, "stage-detail-overview");
    await assertPageQuality(page, testInfo, "stage-detail");
    await page.getByRole("tab", { name: "Evidence" }).click();
    await captureState(page, testInfo, "stage-detail-evidence");
    await page.getByRole("tab", { name: "Review" }).click();
    await captureState(page, testInfo, "stage-detail-review");
    await page.getByText("Advanced editor", { exact: true }).click();
    await captureState(page, testInfo, "stage-detail-advanced");
  });

  test("8. filters provider scopes and enforces member-admin permissions", async ({ page }, testInfo) => {
    await loginAs(page, "member");
    await page.goto("/providers");
    await expect(page.getByRole("tab", { name: /^Personal/ })).toHaveAttribute("aria-selected", "true");
    await expect(
      page
        .getByRole("region", { name: "Personal credentials" })
        .getByText("NoviScope E2E Personal", { exact: true })
        .filter({ visible: true }),
    ).toBeVisible();
    await captureState(page, testInfo, "providers-personal");
    await page.getByRole("tab", { name: /^Shared/ }).click();
    await expect(
      page
        .getByRole("region", { name: "Shared credentials" })
        .getByText("NoviScope E2E Shared", { exact: true })
        .filter({ visible: true }),
    ).toBeVisible();
    await expect(page.getByText(/Only administrators can change/)).toBeVisible();
    await expect(
      page.getByRole("combobox", { name: "Demand Validator Default provider" }),
    ).toBeDisabled();
    await captureState(page, testInfo, "providers-shared");
    await assertPageQuality(page, testInfo, "providers-member");
    if (page.viewportSize()?.width !== 1440) {
      const matrix = page.getByRole("table", { name: "Agent defaults" });
      await matrix.scrollIntoViewIfNeeded();
      const providerControl = page.getByRole("combobox", {
        name: "Demand Validator Default provider",
      });
      await providerControl.scrollIntoViewIfNeeded();
      await expect(providerControl).toBeInViewport();
      await captureState(page, testInfo, "providers-shared-matrix");
    }

    await page.getByRole("button", { name: "Logout" }).click();
    await loginAs(page, "admin");
    await page.goto("/providers");
    await expect(
      page.getByRole("combobox", { name: "Demand Validator Default provider" }),
    ).toBeEnabled();
  });

  test("9. switches Chinese and English without missing or overflowing commands", async ({ page }) => {
    await loginAs(page, "member");
    await selectSeededQuest(page);
    const englishCommand = page.getByRole("button", { name: "Run agent" });
    await assertTextFits(englishCommand);
    await page.getByRole("button", { name: "中文" }).click();
    const chineseCommand = page.getByRole("button", { name: "运行智能体" });
    await expect(page.getByRole("button", { name: "中文" })).toHaveCSS(
      "background-color",
      "rgb(11, 118, 111)",
    );
    await expect(chineseCommand).toBeVisible();
    await assertTextFits(chineseCommand);
    await expect(page.locator("body")).not.toContainText(/missing translation|undefined/i);
    await page.getByRole("button", { name: "English" }).click();
    await expect(englishCommand).toBeVisible();
  });

  test("10. captures Chinese Canvas, Quest, Provider, and Stage Detail surfaces", async ({ page }, testInfo) => {
    await loginAs(page, "member");
    await selectSeededQuest(page);
    const selectedCanvasUrl = page.url();
    await page.getByRole("button", { name: "中文" }).click();
    await expect(page.getByRole("button", { name: "中文" })).toHaveCSS(
      "background-color",
      "rgb(11, 118, 111)",
    );
    await captureState(page, testInfo, "zh-canvas");
    await assertPageQuality(page, testInfo, "zh-canvas");

    await page.goto("/quests/new");
    await expect(page.getByRole("heading", { name: "新建 Quest" })).toBeVisible();
    await captureState(page, testInfo, "zh-new-quest");
    await assertPageQuality(page, testInfo, "zh-new-quest");

    await page.goto("/providers");
    await expect(page.getByRole("tab", { name: /^个人/ })).toBeVisible();
    await captureState(page, testInfo, "zh-providers");
    await assertPageQuality(page, testInfo, "zh-providers");

    await page.goto(selectedCanvasUrl);
    await expect(
      page.getByRole("heading", { exact: true, name: "Badminton Performance Analysis" }),
    ).toBeVisible();
    await page.getByRole("link", { name: "查看证据与详情" }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Demand validation" })).toBeVisible();
    await captureState(page, testInfo, "zh-stage-detail");
    await assertPageQuality(page, testInfo, "zh-stage-detail");
  });
});
