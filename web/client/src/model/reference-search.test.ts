import { describe, expect, test } from "vitest";
import { highlightMatches, rankReferenceOptions, referenceOptions, type TReferenceOption } from "./reference-search";

const choices: TReferenceOption[] = [
  { displayName: "Useful editor", identifier: "web/use" },
  { displayName: "Use", identifier: "commands/long-identifier" },
  { displayName: "Unused", identifier: "use" },
];

describe("reference search", () => {
  test("uses weighted name and identifier ranking with deterministic ties", () => {
    const ranked = rankReferenceOptions(choices, " use ");
    expect(ranked.map((item) => item.identifier)).toEqual(["use", "web/use", "commands/long-identifier"]);
    const ties = rankReferenceOptions([
      { displayName: "Same", identifier: "z/use" },
      { displayName: "Same", identifier: "a/use" },
    ], "same");
    expect(ties.map((item) => item.identifier)).toEqual(["a/use", "z/use"]);
  });

  test("matches case-insensitively, limits results, and highlights every substring", () => {
    expect(rankReferenceOptions(Array.from({ length: 12 }, (_, index) => ({
      displayName: `USE ${index}`, identifier: `item-${index}`,
    })), "use")).toHaveLength(10);
    expect(highlightMatches("Use use USE", "use").filter((part) => part.matched).map((part) => part.text))
      .toEqual(["Use", "use", "USE"]);
  });

  test("applies centralized candidate restrictions and duplicate filtering", () => {
    const context = {
      currentIdentifier: "parent", selected: ["duplicate"],
      work: [
        { slug: "parent", title: "Parent" }, { slug: "child", title: "Child", parent: "parent" },
        { slug: "epic", title: "Epic", type: "epic" }, { slug: "duplicate", title: "Duplicate" },
      ],
      taxonomy: [
        { slug: "term", name: "Term", kind: "Vocabulary" }, { slug: "feature", name: "Feature", kind: "Feature" },
      ],
      capabilities: [
        { path: "roles/admin", name: "Admin" }, { path: "conditions/online", name: "Online" },
        { path: "parent", name: "Current" },
      ],
    };
    expect(referenceOptions("work-parent", context).map((item) => item.identifier)).toEqual(["epic", "duplicate"]);
    expect(referenceOptions("work-initiative", context).map((item) => item.identifier)).toEqual(["epic"]);
    expect(referenceOptions("work-blockers", context).map((item) => item.identifier)).toEqual(["child", "epic"]);
    expect(referenceOptions("taxonomy-vocabulary", context).map((item) => item.identifier)).toEqual(["term"]);
    expect(referenceOptions("capability-roles", context).map((item) => item.identifier)).toEqual(["roles/admin"]);
    expect(referenceOptions("capability-when", context).map((item) => item.identifier)).toEqual(["conditions/online"]);
  });
});
