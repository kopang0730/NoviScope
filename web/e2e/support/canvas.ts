import { expect, type Page } from "@playwright/test";

export const canvasRoleNames = [
  "Demand Validator",
  "Research Refiner",
  "Literature Scout",
  "Gap Analyst",
  "Idea Generator",
  "Experiment Planner",
  "Code Runner",
  "Evidence Auditor",
  "Paper & Meeting Writer",
] as const;

export async function assertMobileCanvasFocusOrder(page: Page): Promise<void> {
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
