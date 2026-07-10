import AxeBuilder from "@axe-core/playwright";
import { expect, type Locator, type Page, type TestInfo } from "@playwright/test";

export async function captureState(
  page: Page,
  testInfo: TestInfo,
  stateName: string,
): Promise<void> {
  await page.screenshot({ path: testInfo.outputPath(`${stateName}.png`) });
}

export async function assertTextFits(locator: Locator): Promise<void> {
  const fits = await locator.evaluate(
    (element) =>
      element.scrollWidth <= element.clientWidth && element.scrollHeight <= element.clientHeight,
  );
  expect(fits).toBe(true);
}

export async function assertPageQuality(
  page: Page,
  testInfo: TestInfo,
  surfaceName: string,
): Promise<void> {
  const documentSize = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  const overflowElements = await page.locator("body *").evaluateAll((elements) =>
    elements.flatMap((element) => {
      const rect = element.getBoundingClientRect();
      if (rect.right <= document.documentElement.clientWidth + 1) {
        return [];
      }
      return [
        {
          className: typeof element.className === "string" ? element.className : "",
          display: window.getComputedStyle(element).display,
          label: element.getAttribute("aria-label") ?? element.textContent?.trim().slice(0, 60) ?? "",
          minWidth: window.getComputedStyle(element).minWidth,
          overflowX: window.getComputedStyle(element).overflowX,
          parentClassName:
            typeof element.parentElement?.className === "string"
              ? element.parentElement.className
              : "",
          right: Math.round(rect.right),
          tag: element.tagName.toLowerCase(),
          width: Math.round(rect.width),
        },
      ];
    }),
  );
  expect(
    documentSize.scrollWidth,
    `Overflow elements: ${JSON.stringify(overflowElements.slice(0, 12))}`,
  ).toBeLessThanOrEqual(documentSize.clientWidth);

  const axeResults = await new AxeBuilder({ page }).analyze();
  const blockingViolations = axeResults.violations
    .filter((violation) => violation.impact === "critical" || violation.impact === "serious")
    .map((violation) => ({
      id: violation.id,
      impact: violation.impact,
      targets: violation.nodes.flatMap((node) => node.target),
    }));
  await testInfo.attach(`axe-${surfaceName}`, {
    body: JSON.stringify({ blockingViolations }),
    contentType: "application/json",
  });
  expect(blockingViolations).toEqual([]);

  if (page.viewportSize()?.width === 390) {
    const tooSmall = await page
      .locator("button, a, input, select, textarea, summary")
      .evaluateAll((elements) =>
        elements.flatMap((element) => {
          const rect = element.getBoundingClientRect();
          if (rect.width === 0 || rect.height === 0 || (rect.width >= 44 && rect.height >= 44)) {
            return [];
          }
          return [
            {
              height: Math.round(rect.height),
              label:
                element.getAttribute("aria-label") ?? element.textContent?.trim().slice(0, 80) ?? "",
              tag: element.tagName.toLowerCase(),
              width: Math.round(rect.width),
            },
          ];
        }),
      );
    expect(tooSmall).toEqual([]);
  }
}
