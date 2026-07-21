import { render, screen } from "@testing-library/react";
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
