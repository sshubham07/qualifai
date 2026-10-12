import { type ClipboardEvent, type FormEvent, useEffect, useRef, useState } from "react";
import { Spinner } from "../components/icons";
import { ANSWER_MAX, type Turn, getRoom, saveDraft, submitAnswer } from "../lib/api";
import { useGuide } from "../lib/guide";

const AUTOSAVE_MS = 3000;
const MAX_PASTES = 50;

// What the page notices while an answer is typed; sent with it as integrity signals.
type Typing = {
  shownAt: number;
  firstKeystrokeMs: number | null;
  lastKeyAt: number | null;
  idleMs: number;
  pastes: { at_ms: number; chars: number }[];
};

const freshTyping = (): Typing => ({
  shownAt: performance.now(),
  firstKeystrokeMs: null,
  lastKeyAt: null,
  idleMs: 0,
  pastes: [],
});

const clock = (seconds: number) =>
  `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;

// Elapsed time by the server's clock, so a wrong laptop clock doesn't matter.
function Elapsed({ turn }: { turn: Turn }) {
  const [now, setNow] = useState(() => Date.now());
  const [offset] = useState(() => Date.parse(turn.server_now) - Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  const started = Date.parse(turn.started_at);
  const elapsed = Math.max(0, (now + offset - started) / 1000);
  const target = Math.round((Date.parse(turn.target_end_at) - started) / 60000);
  return (
    <span className="font-mono text-sm text-muted" aria-label="Time used">
      {clock(elapsed)} <span className="text-muted/70">/ ~{target} min</span>
    </span>
  );
}

function Ended() {
  useGuide("That's the interview. Thank you, your answers are saved.", "happy");
  return (
    <div className="rounded-2xl border border-line bg-surface p-6 sm:p-8">
      <h1 className="text-2xl font-semibold tracking-tight">Interview complete</h1>
      <p className="mt-2 text-muted">
        Thank you. Every answer is saved. Keep this page's link: your report will appear here once
        it has been written.
      </p>
    </div>
  );
}

export function Room({ id, initial }: { id: string; initial: Turn }) {
  const [turn, setTurn] = useState(initial);
  const [text, setText] = useState(initial.draft ?? "");
  const [sending, setSending] = useState(false);
  const [incoming, setIncoming] = useState(""); // the next question, as it is being written
  const [problem, setProblem] = useState<string | null>(null);
  const typing = useRef<Typing>(freshTyping());
  const saved = useRef(initial.draft ?? "");
  const latest = useRef({ text, seq: turn.seq, sending }); // for the timers below
  useEffect(() => {
    latest.current = { text, seq: turn.seq, sending };
  });

  // Autosave: if the page dies or time runs out, what was typed is not lost.
  useEffect(() => {
    const timer = setInterval(() => {
      const { text: current, seq, sending: busy } = latest.current;
      if (busy || seq === null || current === saved.current) return;
      saved.current = current;
      saveDraft(id, seq, current).catch(() => {
        saved.current = ""; // try again on the next tick
      });
    }, AUTOSAVE_MS);
    return () => clearInterval(timer);
  }, [id]);

  // The next question arrives word by word; the end can arrive without us asking (time up).
  useEffect(() => {
    const stream = new EventSource(`/v1/interviews/${id}/events`);
    stream.addEventListener("token", (e) => {
      const token = JSON.parse((e as MessageEvent).data) as { seq: number; text: string };
      if ((latest.current.seq ?? 0) < token.seq) setIncoming((shown) => shown + token.text);
    });
    stream.addEventListener("ended", () => {
      stream.close();
      if (!latest.current.sending) getRoom(id).then(setTurn).catch(() => {});
    });
    return () => stream.close();
  }, [id]);

  useGuide(
    turn.ended
      ? null
      : turn.final_question
        ? "This is the last technical question. Take your time."
        : turn.phase === "closing"
          ? "Anything you'd like to ask? Your question is welcome."
          : "Answer the way you would to a person. Specifics beat buzzwords.",
    "talk",
  );

  if (turn.ended || turn.seq === null) {
    if (!turn.ended) {
      // In progress but no question waiting: a turn was interrupted. The server finishes it.
      return (
        <div className="rounded-2xl border border-line bg-surface p-6 sm:p-8">
          <p className="flex items-center gap-3 text-muted">
            <Spinner className="size-4" />
            Picking up where you left off. Reload this page in a moment.
          </p>
        </div>
      );
    }
    return <Ended />;
  }
  const seq = turn.seq;

  function onKey() {
    const t = typing.current;
    const now = performance.now();
    if (t.firstKeystrokeMs === null) t.firstKeystrokeMs = Math.round(now - t.shownAt);
    if (t.lastKeyAt !== null) t.idleMs = Math.max(t.idleMs, Math.round(now - t.lastKeyAt));
    t.lastKeyAt = now;
  }

  function onPaste(e: ClipboardEvent<HTMLTextAreaElement>) {
    const t = typing.current;
    const chars = e.clipboardData.getData("text").length;
    if (chars > 0 && t.pastes.length < MAX_PASTES) {
      t.pastes.push({ at_ms: Math.round(performance.now() - t.shownAt), chars });
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const answer = text.trim();
    if (!answer || sending) return;
    setSending(true);
    setProblem(null);
    setIncoming("");
    try {
      const t = typing.current;
      const next = await submitAnswer(id, {
        question_seq: seq,
        text: answer,
        first_keystroke_ms: t.firstKeystrokeMs,
        idle_ms: t.idleMs,
        pastes: t.pastes,
      });
      typing.current = freshTyping();
      saved.current = "";
      setText("");
      setTurn(next);
    } catch (err) {
      // The answer stays in the box; sending it again is safe.
      setProblem(err instanceof Error ? err.message : "Could not send your answer.");
    } finally {
      setSending(false);
      setIncoming("");
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      <div className="flex items-center justify-between px-1">
        <span className="text-sm font-medium text-muted">
          {turn.phase === "closing" ? "Wrapping up" : `Question ${Math.ceil(seq / 2)}`}
          {turn.final_question && " · last one"}
        </span>
        <Elapsed turn={turn} />
      </div>

      <div className="rounded-2xl border border-line bg-surface p-6 sm:p-8" aria-live="polite">
        {sending ? (
          <p className="min-h-14 text-lg leading-relaxed text-muted">
            {incoming || (
              <span className="flex items-center gap-3 text-base">
                <Spinner className="size-4" /> Thinking about your answer…
              </span>
            )}
          </p>
        ) : (
          <p className="min-h-14 text-lg leading-relaxed">{turn.question}</p>
        )}
      </div>

      <div className="rounded-2xl border border-line bg-surface p-3 focus-within:border-brand/60">
        <label htmlFor="answer" className="sr-only">
          Your answer
        </label>
        <textarea
          id="answer"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKey}
          onPaste={onPaste}
          disabled={sending}
          maxLength={ANSWER_MAX}
          rows={8}
          autoFocus
          placeholder="Type your answer…"
          className="w-full resize-y bg-transparent p-3 text-[15px] leading-relaxed outline-none placeholder:text-muted/70 disabled:opacity-60"
        />
        <div className="flex items-center justify-between gap-3 px-3 pb-2">
          <span className="text-xs text-muted">
            {text.length > ANSWER_MAX * 0.9
              ? `${text.length} / ${ANSWER_MAX}`
              : "Saved as you type"}
          </span>
          <button
            type="submit"
            disabled={sending || !text.trim()}
            className="rounded-full bg-brand px-6 py-2.5 font-medium text-white shadow-sm transition hover:bg-brand-dark disabled:cursor-not-allowed disabled:opacity-50"
          >
            {sending ? "Sending…" : "Send answer"}
          </button>
        </div>
      </div>

      {problem && (
        <p role="alert" className="rounded-xl bg-danger-soft px-4 py-3 text-sm text-danger">
          {problem} Your answer is still here. Send it again.
        </p>
      )}
    </form>
  );
}
