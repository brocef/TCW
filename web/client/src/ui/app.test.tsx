import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { App } from "./app";

test("renders the established three-axis shell", () => {
  globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
  render(<MemoryRouter><App /></MemoryRouter>);
  expect(screen.getByRole("button", { name: "Taxonomy" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Capabilities" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Work" })).toBeInTheDocument();
  expect(screen.getByRole("tree", { name: "Objects" })).toBeInTheDocument();
});

test.each(["Taxonomy", "Capabilities", "Work"])("renders the %s create button above its object list", (axis) => {
  globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
  render(<MemoryRouter><App /></MemoryRouter>);
  if (axis !== "Work") fireEvent.click(screen.getByRole("button", { name: axis }));

  const tree = screen.getByRole("tree", { name: "Objects" });
  const createButton = screen.getByRole("button", { name: `+ Create ${axis}` });
  expect(createButton.compareDocumentPosition(tree)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
});
