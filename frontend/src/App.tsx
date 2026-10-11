import { BrowserRouter, Link, Route, Routes, useLocation } from "react-router-dom";
import { GuideProvider } from "./components/Guide";
import { useGuide } from "./lib/guide";
import { Home } from "./pages/Home";
import { Interview } from "./pages/Interview";
import { Start } from "./pages/Start";

function NotFound() {
  useGuide("I can't find this page. Head back to the start and I'll take it from there.", "think");
  return (
    <div className="mx-auto w-full max-w-2xl px-5 py-20 text-center">
      <h1 className="text-2xl font-semibold tracking-tight">Page not found</h1>
      <Link to="/" className="mt-4 inline-block font-medium text-brand hover:text-brand-dark">
        Back to the start →
      </Link>
    </div>
  );
}

// The home page and the setup page already have their own way in.
function SetUpLink() {
  const { pathname } = useLocation();
  if (pathname === "/" || pathname === "/start") return null;
  return (
    <Link
      to="/start"
      className="rounded-full bg-brand-soft px-4 py-2 text-sm font-medium text-brand transition hover:bg-brand hover:text-white"
    >
      Set up an interview
    </Link>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-dvh flex-col font-sans antialiased">
        <header className="border-b border-line bg-surface/80 backdrop-blur">
          <div className="mx-auto flex h-16 w-full max-w-5xl items-center justify-between px-5">
            <Link to="/" className="flex items-center gap-2.5 text-2xl font-semibold tracking-tight">
              <img src="/favicon.svg" alt="" className="size-8" />
              <span>
                Qualif<span className="text-brand">AI</span>
              </span>
            </Link>
            <SetUpLink />
          </div>
        </header>
        <main className="flex-1">
          <GuideProvider>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/start" element={<Start />} />
              <Route path="/interviews/:id" element={<Interview />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </GuideProvider>
        </main>
        <footer className="border-t border-line py-6 text-center text-sm text-muted">
          QualifAI · adaptive, resume-aware technical interviews
        </footer>
      </div>
    </BrowserRouter>
  );
}
