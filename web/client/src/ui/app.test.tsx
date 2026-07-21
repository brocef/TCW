import { render, screen } from "@testing-library/react";
import { App } from "./app";

test("renders the established three-axis shell", () => {
  render(<App />);
  expect(screen.getByRole("button", { name: "Taxonomy" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Capabilities" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Work" })).toBeInTheDocument();
  expect(screen.getByRole("tree", { name: "Objects" })).toBeInTheDocument();
});
