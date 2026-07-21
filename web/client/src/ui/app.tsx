import { useEffect } from "react";

function loadScript(source: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = source;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error(`failed to load ${source}`));
    document.body.append(script);
  });
}

export function App() {
  useEffect(() => {
    void loadScript("/marked.min.js")
      .then(() => loadScript("/tree.js"))
      .then(() => loadScript("/app.js"))
      .catch((error: unknown) => {
        const detail = document.getElementById("detail");
        if (detail) detail.textContent = error instanceof Error ? error.message : String(error);
      });
  }, []);

  return (
    <>
      <header className="topbar">
        <div><h1>TCW</h1><p id="summary">Loading...</p></div>
        <nav className="tabs" aria-label="TCW views">
          <button type="button" className="tab" data-view="taxonomy">Taxonomy</button>
          <button type="button" className="tab" data-view="capabilities">Capabilities</button>
          <button type="button" className="tab active" data-view="work">Work</button>
        </nav>
      </header>
      <main className="shell">
        <section className="list-pane">
          <div className="list-head">
            <h2 id="list-title">Work</h2>
            <input id="filter" type="search" placeholder="Filter" />
          </div>
          <div id="status-filters" className="status-filters" role="group"
               aria-label="Filter work items by status" hidden />
          <div id="list" className="list" role="tree" aria-label="Objects" />
        </section>
        <div className="col-resizer" id="colResizer" role="separator"
             aria-orientation="vertical" aria-label="Resize list column" />
        <section id="detail" className="detail-pane" aria-live="polite" />
      </main>
      <div id="toast" className="toast" hidden />
    </>
  );
}
