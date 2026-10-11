import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { Home } from "./pages/Home";
import { Interview } from "./pages/Interview";
import { Start } from "./pages/Start";

function NotFound() {
  return (
    <div className="mx-auto w-full max-w-2xl px-5 py-20 text-center">
      <h1 className="text-2xl font-semibold tracking-tight">Page not found</h1>
      <Link to="/" className="mt-4 inline-block font-medium text-brand hover:text-brand-dark">
        Back to the start →
      </Link>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-dvh flex-col font-sans antialiased">
        <header className="border-b border-line bg-surface/80 backdrop-blur">
          <div className="mx-auto flex h-14 w-full max-w-5xl items-center justify-between px-5">
            <Link to="/" className="text-lg font-semibold tracking-tight">
              Qualif<span className="text-brand">AI</span>
            </Link>
            <Link
              to="/start"
              className="rounded-full bg-ink px-4 py-1.5 text-sm font-medium text-white transition hover:bg-brand"
            >
              Start an interview
            </Link>
          </div>
        </header>
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/start" element={<Start />} />
            <Route path="/interviews/:id" element={<Interview />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
        <footer className="border-t border-line py-6 text-center text-sm text-muted">
          QualifAI · adaptive, resume-aware technical interviews
        </footer>
      </div>
    </BrowserRouter>
  );
}
