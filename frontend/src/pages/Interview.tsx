import { type ReactNode, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { CheckIcon, Spinner } from "../components/icons";
import { ApiError, type StatusOut, getInterview, roleName } from "../lib/api";

const POLL_MS = 3000;
const PREP_STEPS = [
  "Checking resume and job description",
  "Parsing resume",
  "Analysing job description",
  "Finding what to verify and what to test",
  "Building a time-budgeted plan",
  "Writing questions and rubrics",
];
const STAGES = ["Submitted", "Preparing", "Ready"];

function Stages({ reached }: { reached: number }) {
  return (
    <ol className="flex items-center gap-2 text-sm">
      {STAGES.map((stage, i) => {
        const done = i < reached;
        const current = i === reached;
        return (
          <li key={stage} className="flex flex-1 items-center gap-2 last:flex-none">
            <span
              className={`grid size-6 shrink-0 place-items-center rounded-full text-xs font-medium ${
                done
                  ? "bg-go text-white"
                  : current
                    ? "bg-brand text-white"
                    : "bg-line text-muted"
              }`}
            >
              {done ? <CheckIcon className="size-3.5" /> : i + 1}
            </span>
            <span className={done || current ? "font-medium" : "text-muted"}>{stage}</span>
            {i < STAGES.length - 1 && (
              <span className={`h-px flex-1 ${done ? "bg-go" : "bg-line"}`} />
            )}
          </li>
        );
      })}
    </ol>
  );
}

function Card({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-6 sm:p-8">{children}</div>
  );
}

// Failures of the resume / job description check: trying again needs different inputs.
const REJECTED = ["not_a_resume", "not_a_jd", "resume_not_software", "jd_not_software"];

function Message(props: { title: string; body: string; retry?: boolean }) {
  return (
    <Card>
      <h1 className="text-2xl font-semibold tracking-tight">{props.title}</h1>
      <p className="mt-2 text-muted">{props.body}</p>
      {props.retry && (
        <Link
          to="/start"
          className="mt-6 inline-block rounded-full bg-brand px-6 py-2.5 font-medium text-white hover:bg-brand-dark"
        >
          Start again
        </Link>
      )}
    </Card>
  );
}

function StartButton() {
  const [clicked, setClicked] = useState(false);
  return (
    <div className="mt-6 flex flex-wrap items-center gap-4">
      {/* TODO(spec-001 T-22): call POST /start and open the interview room. */}
      <button
        type="button"
        onClick={() => setClicked(true)}
        className="rounded-full bg-brand px-7 py-3 font-medium text-white shadow-sm transition hover:bg-brand-dark"
      >
        Start interview
      </button>
      {clicked && (
        <p role="status" className="text-sm text-muted">
          The interview room isn't built yet. Your questions are saved and waiting.
        </p>
      )}
    </div>
  );
}

function MeetId({ id }: { id: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(id);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard unavailable (insecure origin or denied): the id is on screen to select.
    }
  }

  return (
    <div className="mt-5 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-xl border border-line bg-canvas/50 px-4 py-3 text-sm">
      <span className="text-muted">Meet ID</span>
      <code className="font-mono break-all">{id}</code>
      <button
        type="button"
        onClick={copy}
        className="ml-auto rounded-full border border-line px-3 py-1 font-medium transition hover:border-brand/50"
      >
        {copied ? "Copied" : "Copy"}
      </button>
    </div>
  );
}

function PrepStatus({ id }: { id: string }) {
  const [data, setData] = useState<StatusOut | null>(null);
  const [problem, setProblem] = useState<ApiError | Error | null>(null);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    let stopped = false;

    async function poll() {
      try {
        const next = await getInterview(id);
        if (stopped) return;
        setData(next);
        setProblem(null);
        if (next.status === "submitted" || next.status === "preparing") {
          timer = setTimeout(poll, POLL_MS);
        }
      } catch (err) {
        if (stopped) return;
        setProblem(err instanceof Error ? err : new Error("Could not load"));
        const notFound = err instanceof ApiError && (err.status === 404 || err.status === 422);
        if (!notFound) timer = setTimeout(poll, POLL_MS * 2); // API briefly unavailable: keep trying
      }
    }

    poll();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [id]);

  if (!data) {
    if (problem instanceof ApiError && (problem.status === 404 || problem.status === 422)) {
      return (
        <Message
          title="We couldn't find that interview"
          body="The link may be incomplete. You can start a new one any time."
          retry
        />
      );
    }
    return (
      <Card>
        <p className="flex items-center gap-3 text-muted">
          <Spinner className="size-4" />
          {problem ? "Having trouble reaching the server. Retrying…" : "Loading your interview…"}
        </p>
      </Card>
    );
  }

  if (data.status === "failed") {
    return (
      <Message
        title={
          REJECTED.includes(data.failure_code ?? "")
            ? "We can't run this interview"
            : "We couldn't prepare this interview"
        }
        body={data.failure_reason ?? "Something went wrong while building your kit. Please try again."}
        retry
      />
    );
  }
  if (data.status === "expired") {
    return (
      <Message
        title="This interview has expired"
        body="Interviews stay available for seven days after they are ready."
        retry
      />
    );
  }

  const preparing = data.status === "submitted" || data.status === "preparing";

  return (
    <div className="space-y-5">
      <Card>
        <Stages reached={preparing ? 1 : 3} />

        <h1 className="mt-8 text-2xl font-semibold tracking-tight">
          {preparing ? "Preparing your interview" : "Your interview is ready"}
        </h1>
        <p className="mt-2 text-muted">
          {preparing
            ? "This takes a few minutes. You can close this page. Keep your Meet ID or this page's link to check back."
            : "Your questions are prepared. Keep this page's link to come back to it."}
        </p>

        <MeetId id={data.meet_id} />

        {!preparing && data.expires_at && (
          <p className="mt-5 rounded-xl bg-go-soft px-4 py-3 text-sm">
            Available until{" "}
            <strong className="font-semibold">
              {new Date(data.expires_at).toLocaleDateString(undefined, {
                weekday: "long",
                day: "numeric",
                month: "long",
              })}
            </strong>
            . One attempt, about 45 minutes.
          </p>
        )}

        {!preparing && <StartButton />}

        <ul className="mt-6 space-y-3">
          {(preparing ? PREP_STEPS : data.progress).map((step) => (
            <li key={step} className="flex items-center gap-3 text-[15px]">
              {preparing ? (
                <span className="size-2 animate-pulse rounded-full bg-brand" />
              ) : (
                <CheckIcon className="size-4 text-go" />
              )}
              <span className={preparing ? "text-muted" : ""}>{step}</span>
            </li>
          ))}
        </ul>
      </Card>

      {data.detected_role && (
        <p className="px-1 text-sm text-muted">
          Role detected:{" "}
          <span className="font-medium text-ink">{roleName(data.detected_role)}</span>
          {data.support === "partial" &&
            " — limited mode. We support this role partly, so the interview stays on general technical ground."}
        </p>
      )}
    </div>
  );
}

export function Interview() {
  const { id = "" } = useParams();
  return (
    <div className="mx-auto w-full max-w-2xl px-5 py-12">
      <PrepStatus key={id} id={id} />
    </div>
  );
}
