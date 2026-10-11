import { Link } from "react-router-dom";
import { FlowDemo } from "../components/FlowDemo";

const NEEDS = [
  ["Your resume", "Pasted as plain text."],
  ["The job description", "The posting you are preparing for."],
  ["Interview focus", "General, DSA, low-level design, high-level design or managerial."],
  ["Company type", "Service-based, startup, product-based or MAANG."],
  ["Experience range", "The years of experience the role asks for."],
];

export function Home() {
  return (
    <div className="mx-auto w-full max-w-5xl px-5">
      {/* Kept short on purpose: the pitch and the walkthrough both fit on the first screen. */}
      <section className="flex flex-col gap-4 pt-5 md:flex-row md:items-center md:justify-between md:gap-8">
        <div>
          <h1 className="max-w-2xl text-2xl font-semibold md:text-3xl tracking-tight text-balance lg:text-4xl">
            An interview built from <span className="text-brand">your resume</span>{" "}
            and the job you want.
          </h1>
          <p className="mt-2 max-w-2xl text-pretty text-muted max-md:hidden">
            Technical interview practice for backend engineers. QualifAI asks
            about what you claim and what the job needs, then shows how you
            would do, with evidence.
          </p>
        </div>
        <div className="shrink-0 md:text-right">
          <Link
            to="/start"
            className="inline-block rounded-full bg-brand px-7 py-3 font-medium text-white shadow-sm transition hover:bg-brand-dark"
          >
            Set up my interview
          </Link>
          <p className="mt-2 text-sm text-muted max-md:hidden">
            Takes 2 minutes. The interview
            <br /> starts later, when you are ready.
          </p>
        </div>
      </section>

      <section aria-labelledby="how" className="pt-5 pb-14 md:pt-6">
        <h2 id="how" className="sr-only">
          How it works
        </h2>
        <FlowDemo />
      </section>

      <section
        aria-labelledby="needs"
        className="mb-20 grid gap-8 rounded-2xl border border-line bg-surface p-6 sm:p-8 md:grid-cols-[1fr_1.4fr]"
      >
        <div>
          <h2 id="needs" className="text-2xl font-semibold tracking-tight">
            What you need to begin
          </h2>
          <p className="mt-3 text-muted">
            Five things, no account. Once your interview is ready you have
            seven days to take it.
          </p>
          <Link
            to="/start"
            className="mt-6 inline-block font-medium text-brand hover:text-brand-dark"
          >
            Get started →
          </Link>
        </div>
        <dl className="grid gap-x-6 gap-y-5 sm:grid-cols-2 lg:grid-cols-3">
          {NEEDS.map(([term, detail]) => (
            <div key={term} className="border-l-2 border-brand/30 pl-4">
              <dt className="font-medium">{term}</dt>
              <dd className="mt-1 text-sm text-muted">{detail}</dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  );
}
