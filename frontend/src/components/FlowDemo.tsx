import { type CSSProperties, type ReactNode, useState } from "react";
import { CheckIcon } from "./icons";
import { type Mood, Robot } from "./Robot";

const STEPS: { title: string; time: string; mood: Mood; says: string; scene: () => ReactNode }[] = [
  {
    title: "Share the role",
    time: "2 min",
    mood: "wave",
    says: "Hi, I'm your AI interviewer. Show me your resume and the job.",
    scene: ShareScene,
  },
  {
    title: "I prepare",
    time: "A few min",
    mood: "think",
    says: "I compare the two and plan what to verify and what to test.",
    scene: PrepareScene,
  },
  {
    title: "We talk",
    time: "45 min",
    mood: "talk",
    says: "Then we talk. My follow-ups depend on what you actually say.",
    scene: InterviewScene,
  },
  {
    title: "Your report",
    time: "Right after",
    mood: "happy",
    says: "You get scores backed by your own words, and a practice plan.",
    scene: ReportScene,
  },
];

// Each scene's pieces enter one after another; `--d` is the piece's delay (see index.css).
const delay = (seconds: number) => ({ "--d": `${seconds}s` }) as CSSProperties;

function Card({ children, at, className = "" }: { children: ReactNode; at: number; className?: string }) {
  return (
    <div
      className={`flow-in rounded-2xl bg-surface px-4 py-3 text-left text-ink shadow-xl shadow-black/20 ${className}`}
      style={delay(at)}
    >
      {children}
    </div>
  );
}

const label = "text-xs font-semibold tracking-wide text-muted uppercase";

function ShareScene() {
  const docs = [
    ["Your resume", ["Backend engineer, 4 yrs", "FastAPI order service", "Postgres, Redis, Kafka"], "-rotate-2"],
    ["The job", ["Senior Backend Engineer", "Distributed systems", "API design, scaling"], "rotate-2 mt-6"],
  ] as const;
  return (
    <div className="w-full max-w-md">
      <div className="grid grid-cols-2 gap-3">
        {docs.map(([title, lines, tilt], d) => (
          <Card key={title} at={0.2 + d * 0.5} className={tilt}>
            <p className={label}>{title}</p>
            <ul className="mt-1.5 space-y-1 text-sm">
              {lines.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </Card>
        ))}
      </div>
      <p className="flow-in mt-4 text-center text-sm text-white/80" style={delay(1.4)}>
        Paste both as text. No account needed.
      </p>
    </div>
  );
}

function PrepareScene() {
  const rows = [
    ["Kafka at 2k req/s", "On your resume", "Verify", "bg-warm-soft text-warm"],
    ["API design", "The job needs it", "Test", "bg-brand-soft text-brand"],
    ["Scaling Postgres", "On both", "Go deep", "bg-go-soft text-go"],
  ];
  return (
    <Card at={0.2} className="w-full max-w-md">
      <p className={label}>Your interview plan</p>
      <ul className="mt-1 divide-y divide-line">
        {rows.map(([topic, why, tag, tone], i) => (
          <li key={topic} className="flow-in flex items-center justify-between gap-3 py-2" style={delay(0.6 + i * 0.4)}>
            <span>
              <span className="font-medium">{topic}</span>{" "}
              <span className="text-sm text-muted">· {why}</span>
            </span>
            <span className={`shrink-0 rounded-full px-3 py-0.5 text-sm font-medium ${tone}`}>{tag}</span>
          </li>
        ))}
      </ul>
      <p className="flow-in mt-2 flex items-center gap-2 text-sm font-medium text-go" style={delay(2)}>
        <span className="grid size-4 place-items-center rounded-full bg-go text-white">
          <CheckIcon className="size-2.5" />
        </span>
        Ready. Take it any time in 7 days.
      </p>
    </Card>
  );
}

function InterviewScene() {
  const turns = [
    ["q", "Your order service did 2k req/s. Where was the bottleneck?"],
    ["a", "Postgres writes. We put a Redis queue in front."],
    ["q", "What happens to queued orders if Redis restarts?"],
  ] as const;
  return (
    <div className="w-full max-w-md space-y-2 text-left text-sm">
      {turns.map(([who, text], i) => (
        <div key={text} className={`flow-in flex ${who === "a" ? "justify-end" : ""}`} style={delay(0.2 + i * 0.7)}>
          <p
            className={`max-w-[85%] rounded-2xl px-4 py-2 shadow-xl shadow-black/20 ${
              who === "a" ? "bg-brand text-white" : "bg-surface text-ink"
            }`}
          >
            {i === 2 && <span className="mb-0.5 block text-xs font-semibold text-go uppercase">Follow-up</span>}
            {text}
          </p>
        </div>
      ))}
    </div>
  );
}

function ReportScene() {
  const scores = [
    ["API design", 3.5],
    ["Databases", 3],
    ["Failure recovery", 2],
  ] as const;
  return (
    <Card at={0.2} className="w-full max-w-md">
      <p className="flex items-center gap-2 font-semibold text-go">
        <span className="grid size-5 place-items-center rounded-full bg-go text-white">
          <CheckIcon className="size-3" />
        </span>
        Ready for product-based rounds
      </p>
      <ul className="mt-2 space-y-1.5 text-sm">
        {scores.map(([topic, score], i) => (
          <li key={topic} className="flex items-center gap-3">
            <span className="w-28 shrink-0">{topic}</span>
            <div className="h-2 flex-1 rounded-full bg-canvas">
              <div
                className="flow-grow h-full rounded-full bg-brand"
                style={{ width: `${(score / 4) * 100}%`, ...delay(0.5 + i * 0.3) }}
              />
            </div>
            <span className="font-mono text-muted">{score}/4</span>
          </li>
        ))}
      </ul>
      <p className="flow-in mt-2.5 border-l-2 border-brand/40 pl-3 text-sm text-muted italic" style={delay(1.6)}>
        “We put a Redis queue in front.”
      </p>
      <p className="flow-in mt-2 text-sm" style={delay(2)}>
        <span className="font-medium">Practise next:</span> durability and recovery
      </p>
    </Card>
  );
}

// The animated walkthrough on the home page: the robot interviewer says one line per step
// while the step plays out beside it. The active step's progress bar drives the
// auto-advance, so pausing the bar (hover, keyboard focus) pauses the tour, and with
// reduced motion there is no bar animation and the steps only change on click.
export function FlowDemo() {
  const [active, setActive] = useState(0);
  const [paused, setPaused] = useState(false);
  const step = STEPS[active];
  const Scene = step.scene;

  return (
    <div
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
    >
      <div
        aria-hidden="true"
        className="flow-stage grid grid-cols-[auto_1fr] items-center gap-x-4 gap-y-3 rounded-3xl p-4 sm:p-5 md:gap-x-8 md:px-8"
      >
        <div className="md:col-start-1 md:row-start-2">
          <Robot
            mood={step.mood}
            className="w-20 shrink-0 sm:w-28 md:w-[clamp(10rem,calc((100dvh-29rem)*0.8),14rem)]"
          />
        </div>
        <p
          key={active}
          className="flow-in relative min-h-20 rounded-2xl bg-white px-4 py-2.5 leading-snug font-medium md:text-lg text-ink shadow-xl shadow-black/20 md:col-span-2 md:row-start-1 md:min-h-0 md:w-fit"
        >
          {step.says.split(" ").map((word, i) => (
            <span key={i} className="flow-fade" style={delay(0.2 + i * 0.05)}>
              {word}{" "}
            </span>
          ))}
          <span className="absolute top-1/2 -left-1.5 size-4 -translate-y-1/2 rotate-45 bg-white md:top-auto md:-bottom-1.5 md:left-18 md:translate-y-0" />
        </p>
        {/* grows with the window so the whole tour stays on the first screen */}
        <div className="col-span-2 grid min-h-48 place-items-center md:col-span-1 md:col-start-2 md:row-start-2 md:min-h-[clamp(12.5rem,calc(100dvh-29rem),20rem)]">
          <Scene key={active} />
        </div>
      </div>

      <ol className="mt-3 grid grid-cols-4 gap-2.5">
        {STEPS.map(({ title, time, says }, i) => (
          <li key={title}>
            <button
              type="button"
              onClick={() => setActive(i)}
              aria-current={i === active ? "step" : undefined}
              className={`relative flex w-full cursor-pointer items-center gap-2.5 overflow-hidden rounded-xl border bg-surface px-3 py-2 text-left max-md:justify-center transition ${
                i === active ? "border-brand shadow-sm" : "border-line hover:border-brand/40"
              }`}
            >
              <span
                className={`grid size-6 shrink-0 place-items-center rounded-full font-mono text-xs font-medium ${
                  i === active ? "bg-brand text-white" : "bg-brand-soft text-brand"
                }`}
              >
                {i + 1}
              </span>
              <span className="text-sm max-md:sr-only">
                <span className="font-semibold">{title}</span>
                <span className="hidden text-muted lg:inline"> {time}</span>
                <span className="sr-only">{says}</span>
              </span>
              {i === active && (
                <span
                  className={`flow-progress absolute inset-x-0 bottom-0 h-1 bg-brand ${paused ? "flow-paused" : ""}`}
                  onAnimationEnd={() => setActive((i + 1) % STEPS.length)}
                />
              )}
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
