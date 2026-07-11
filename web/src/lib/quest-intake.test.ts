import { describe, expect, it } from "vitest";
import { buildInitialDirection, deriveQuestTitle, emptyIntake, hasAdditionalQuestContext } from "./quest-intake";

describe("quest intake helpers", () => {
  it("derives a normalized title from the required direction when no title is supplied", () => {
    // Given
    const formState = { ...emptyIntake, direction: "  Use CV to analyze badminton actions.  " };

    // When
    const title = deriveQuestTitle(formState, "en");

    // Then
    expect(title).toBe("Use CV to analyze badminton actions");
  });

  it("keeps an explicit title when one is supplied", () => {
    // Given
    const formState = { ...emptyIntake, direction: "Direction", title: "Custom title" };

    // When
    const title = deriveQuestTitle(formState, "en");

    // Then
    expect(title).toBe("Custom title");
  });

  it("clamps a derived title after whitespace normalization", () => {
    // Given
    const formState = { ...emptyIntake, direction: `${"research ".repeat(20)}direction.` };

    // When
    const title = deriveQuestTitle(formState, "en");

    // Then
    expect(title).toHaveLength(80);
    expect(title).not.toMatch(/\s{2,}/);
  });

  it("keeps additional context collapsed for an empty intake", () => {
    // Given
    const formState = emptyIntake;

    // When
    const hasContext = hasAdditionalQuestContext(formState);

    // Then
    expect(hasContext).toBe(false);
  });

  it("keeps every optional intake field in the Chinese backend payload", () => {
    // Given
    const formState = emptyIntake;

    // When
    const initialDirection = buildInitialDirection(formState, "zh");

    // Then
    expect(initialDirection).toContain("进入实验前应先人工复核");
    expect(initialDirection).toContain("未提供");
  });
});
