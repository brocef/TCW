import ReactDOM from "react-dom/client";
import { RouterProvider, createBrowserRouter } from "react-router";
import { App } from "./ui/app";
import "./style.css";

const router = createBrowserRouter([
  { path: "*", Component: App }
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <RouterProvider router={router} />
);
