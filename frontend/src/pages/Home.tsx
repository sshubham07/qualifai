import { Link } from "react-router-dom";
import { ChatIcon, DocIcon, PlanIcon, ReportIcon } from "../components/icons";

const STEPS = [
  {
    icon: DocIcon,
    tone: "bg-brand-soft text-brand",
    title: "Share the role",
    time: "2 minutes",
    body: "Paste your resume and the job description, then pick the kind of company and your experience range.",
  },
  {
    icon: PlanIcon,
    tone: "bg-brand-soft text-brand",
    title: "We prepare your kit",
    time: "A few minutes",
    body: "QualifAI compares what you claim with what the job needs and plans what to verify and what to test. You get a Meet ID to check back with.",
  },
  {
    icon: ChatIcon,
    tone: "bg-go-soft text-go",
    title: "Take the interview",
    time: "About 45 minutes",
    body: "A text interview about your own projects and the job's priorities. Follow-ups react to what you actually say.",
  },
  {
    icon: ReportIcon,
    tone: "bg-warm-soft text-warm",
    title: "Read your report",
    time: "Shortly after",
    body: "Scores backed by quotes from your answers, a verdict for that company type, and a plan for what to practise next.",
  },
];

const NEEDS = [
  ["Your resume", "Pasted as plain text."],
  ["The job description", "The posting you are preparing for."],
  ["Company type", "Service-based, startup, product-based or MAANG."],
  ["Experience range", "The years of experience the role asks for."],
];

export function Home() {
  return (
    <div className="mx-auto w-full max-w-5xl px-5">
      <section className="py-16 text-center sm:py-24">
        <p className="mx-auto mb-5 w-fit rounded-full border border-line bg-surface px-3 py-1 text-sm text-muted">
          Technical interview practice for backend engineers
        </p>
        <h1 className="mx-auto max-w-3xl text-4xl font-semibold tracking-tight text-balance sm:text-6xl">
          An interview built from <span className="text-brand">your resume</span>{" "}
          and the job you want.
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-pretty text-muted">
          QualifAI reads both, asks about the things you claim and the things
          the job needs, and tells you how you would do, with evidence.
        </p>
        <Link
          to="/start"
          className="mt-9 inline-block rounded-full bg-brand px-7 py-3 font-medium text-white shadow-sm transition hover:bg-brand-dark"
        >
          Start an interview
        </Link>
      </section>

      <section aria-labelledby="how" className="pb-16">
        <h2 id="how" className="text-center text-2xl font-semibold tracking-tight">
          How it works
        </h2>
        <ol className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map(({ icon: StepIcon, tone, title, time, body }, i) => (
            <li
              key={title}
              className="relative rounded-2xl border border-line bg-surface p-5"
            >
              <div className="flex items-center justify-between">
                <span className={`grid size-10 place-items-center rounded-xl ${tone}`}>
                  <StepIcon className="size-5" />
                </span>
                <span className="font-mono text-sm text-muted">0{i + 1}</span>
              </div>
              <h3 className="mt-4 font-semibold">{title}</h3>
              <p className="mt-0.5 text-sm text-muted">{time}</p>
              <p className="mt-3 text-sm leading-relaxed text-pretty">{body}</p>
            </li>
          ))}
        </ol>
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
            Four things, no account. Once your interview is ready you have
            seven days to take it.
          </p>
          <Link
            to="/start"
            className="mt-6 inline-block font-medium text-brand hover:text-brand-dark"
          >
            Get started →
          </Link>
        </div>
        <dl className="grid gap-x-6 gap-y-5 sm:grid-cols-2">
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
