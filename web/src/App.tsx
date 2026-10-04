import { useState } from "react";
import { Shell } from "./components/v2/Shell";
import { AnalyzePage } from "./components/v2/AnalyzePage";
import { AnalysisPage } from "./components/v2/AnalysisPage";
import { AnalysesList } from "./components/v2/AnalysesList";
import { SourcesPage } from "./components/v2/SourcesPage";
import { BenchmarkPage } from "./components/v2/BenchmarkPage";
import { VerifyPage } from "./components/v2/VerifyPage";
import { LegacyPage } from "./components/v2/LegacyPage";
import { BackendContext, loadBackendUrl } from "./lib/v2api";
import { useRoute } from "./lib/route";
import "./App.css";
import "./v2.css";

export default function App() {
  const [base, setBase] = useState(loadBackendUrl());
  const route = useRoute();

  let page;
  const m = /^\/analyses\/([^/]+)/.exec(route);
  if (m) page = <AnalysisPage key={m[1]} id={decodeURIComponent(m[1])} />;
  else if (route === "/analyses") page = <AnalysesList />;
  else if (route === "/sources") page = <SourcesPage />;
  else if (route === "/benchmark") page = <BenchmarkPage />;
  else if (route === "/verify") page = <VerifyPage />;
  else if (route === "/legacy") page = <LegacyPage />;
  else page = <AnalyzePage />;

  return (
    <BackendContext.Provider value={base}>
      <Shell route={route} base={base} onBase={setBase}>
        {page}
      </Shell>
    </BackendContext.Provider>
  );
}
