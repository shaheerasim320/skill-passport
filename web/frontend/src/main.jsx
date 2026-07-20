import { createRoot } from "react-dom/client";
import "./styles.css";
import { AppErrorBoundary } from "./components/AppErrorBoundary";
import { AnalysisPage } from "./pages/AnalysisPage";
import { LandingPage } from "./pages/LandingPage";

const page = window.location.pathname.replace(/\/+$/, "") === "/analysis"
  ? <AnalysisPage />
  : <LandingPage />;

// A repository analysis has real external work, so render once in development
// instead of allowing StrictMode to intentionally replay the streaming effect.
createRoot(document.getElementById("root")).render(<AppErrorBoundary>{page}</AppErrorBoundary>);
