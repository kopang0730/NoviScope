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

export async function assertTabsStayOnOneRow(tablist: Locator): Promise<void> {
  const tabTopOffsets = await tablist.getByRole("tab").evaluateAll((tabs) =>
    tabs.map((tab) => Math.round(tab.getBoundingClientRect().top)),
  );
  expect(new Set(tabTopOffsets).size).toBe(1);
}

export async function assertTabsFitWithinTablist(tablist: Locator): Promise<void> {
  const defects = await tablist.evaluate((list) => {
    const listRect = list.getBoundingClientRect();
    const tabs = Array.from(list.querySelectorAll('[role="tab"]'));
    return tabs.flatMap((tab) => {
      const rect = tab.getBoundingClientRect();
      const label = tab.textContent?.trim() ?? "";
      const fitsText =
        tab.scrollWidth <= tab.clientWidth && tab.scrollHeight <= tab.clientHeight;
      const withinBounds = rect.left >= listRect.left - 1 && rect.right <= listRect.right + 1;
      if (fitsText && withinBounds) {
        return [];
      }
      return [{
        fitsText,
        label,
        rectRight: Math.round(rect.right),
        tablistRight: Math.round(listRect.right),
        withinBounds,
      }];
    });
  });
  expect(defects).toEqual([]);
}

export async function assertNoControlOverlap(subject: Locator): Promise<void> {
  const overlaps = await subject.evaluate((subjectElement) => {
    const subjectRect = subjectElement.getBoundingClientRect();
    const candidates = Array.from(
      document.querySelectorAll(
        'input, select, textarea, button, [role="alert"], [role="status"]',
      ),
    );
    return candidates.flatMap((candidate) => {
      if (candidate === subjectElement) {
        return [];
      }
      const rect = candidate.getBoundingClientRect();
      const style = window.getComputedStyle(candidate);
      const isVisible =
        rect.width > 0 &&
        rect.height > 0 &&
        style.visibility !== "hidden" &&
        style.display !== "none";
      const intersects =
        subjectRect.left < rect.right &&
        subjectRect.right > rect.left &&
        subjectRect.top < rect.bottom &&
        subjectRect.bottom > rect.top;
      if (!isVisible || !intersects) {
        return [];
      }
      return [{
        candidate: candidate.getAttribute("aria-label") ?? candidate.textContent?.trim() ?? "",
        tag: candidate.tagName.toLowerCase(),
      }];
    });
  });
  expect(overlaps).toEqual([]);
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
