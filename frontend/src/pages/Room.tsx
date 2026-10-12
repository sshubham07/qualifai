import {
  type ClipboardEvent,
  type FormEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { MicIcon, PauseIcon, SpeakerIcon, SpeakerOffIcon, Spinner } from "../components/icons";
import {
  ANSWER_MAX,
  type Turn,
  getRoom,
  questionAudioUrl,
  saveDraft,
  submitAnswer,
} from "../lib/api";
import { useGuide } from "../lib/guide";
import { canListen, canSpeak, useDictation, useSpeaker } from "../lib/voice";

const AUTOSAVE_MS = 3000;
const MAX_PASTES = 50;
const WORDS_PER_SECOND = 2.6; // how fast the interviewer talks; the text keeps pace with it
const QUIET_MS = 3000; // silence after speech before the countdown shows
const COUNTDOWN_MS = 3000; // then this long to keep talking before the answer is sent

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

// The question as far as it has been said: words appear as the voice reaches them, so nobody
// reads ahead of the interviewer. Everything shows once the voice is done (or is off).
function Spoken({ text, audible, done }: { text: string; audible: boolean; done: boolean }) {
  const [words, setWords] = useState(0);
  useEffect(() => {
    if (!audible) return;
    const began = performance.now();
    const timer = setInterval(
      () => setWords(Math.ceil(((performance.now() - began) / 1000) * WORDS_PER_SECOND)),
      120,
    );
    return () => clearInterval(timer);
  }, [audible, text]);
  if (done) return <>{text}</>;
  if (!audible) {
    return (
      <span className="flex items-center gap-3 text-base text-muted">
        <Spinner className="size-4" /> One moment…
      </span>
    );
  }
  return <>{text.split(" ").slice(0, Math.max(words, 1)).join(" ")}</>;
}

function Ended({ id, turn }: { id: string; turn: Turn }) {
  useGuide("That's the interview. Thank you, your answers are saved.", "happy");
  const { speak } = useSpeaker();
  const { farewell, farewell_seq: seq } = turn;
  useEffect(() => {
    if (farewell && seq) speak(farewell, undefined, questionAudioUrl(id, seq));
  }, [id, farewell, seq, speak]);
  return (
    <div className="rounded-2xl border border-line bg-surface p-6 sm:p-8">
      {farewell && <p className="mb-6 text-lg leading-relaxed">{farewell}</p>}
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

  // Voice (ADR-0022): the question is read aloud, then the microphone opens by itself. What is
  // heard is written out as it is said, and a few seconds of silence send it. No send button.
  const [voiceOn, setVoiceOn] = useState(canSpeak);
  const [sendIn, setSendIn] = useState<number | null>(null); // seconds left before it is sent
  const heardAt = useRef<number | null>(null); // last time the candidate was heard on this question
  const paused = useRef(false); // the candidate paused the mic: don't reopen it for them
  const [saidSeq, setSaidSeq] = useState<number | null>(null); // the question that has been read out
  const { speaking, audible, speak, stop: hush } = useSpeaker();
  const addPhrase = useCallback((phrase: string) => {
    heardAt.current = performance.now();
    setText((said) => `${said.trimEnd()} ${phrase.trim()}`.trim().slice(0, ANSWER_MAX));
  }, []);
  const mic = useDictation(addPhrase);
  const { start: listen, stop: pause, cancel: closeMic } = mic;
  const handsFree = canListen && !mic.blocked; // otherwise: a text box and a send button
  const question = turn.ended || turn.seq === null ? null : turn.question;

  async function send() {
    const seq = turn.seq;
    const answer = `${text} ${mic.interim}`.trim().slice(0, ANSWER_MAX); // with the phrase in flight
    if (seq === null || !answer || sending) return;
    closeMic();
    hush();
    setText(answer);
    setSendIn(null);
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
      heardAt.current = null;
      paused.current = false;
      setText("");
      setTurn(next);
    } catch (err) {
      // The answer stays on the page; sending it again is safe.
      setProblem(err instanceof Error ? err.message : "Could not send your answer.");
    } finally {
      setSending(false);
      setIncoming("");
    }
  }

  const latest = useRef({ text, seq: turn.seq, sending, send, mic }); // for the timers below
  useEffect(() => {
    latest.current = { text, seq: turn.seq, sending, send, mic };
  });

  // Autosave: if the page dies or time runs out, what was said or typed is not lost.
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

  // Read the question, then open the microphone.
  const ask = useCallback(() => {
    if (!question || turn.seq === null) return;
    const seq = turn.seq;
    const open = () => {
      setSaidSeq(seq);
      if (paused.current) return;
      if (heardAt.current !== null) heardAt.current = performance.now(); // the silence starts over
      listen();
    };
    if (!voiceOn) return open();
    pause(); // or the mic would hear the interviewer
    speak(question, open, questionAudioUrl(id, seq));
  }, [id, question, turn.seq, voiceOn, speak, pause, listen]);

  useEffect(() => {
    if (!voiceOn || !question) hush();
    if (question) ask();
    else closeMic();
  }, [question, turn.seq, voiceOn, ask, hush, closeMic]);

  useEffect(() => {
    if (mic.interim) heardAt.current = performance.now();
  }, [mic.interim]);

  // The answer ends the way it does in a room: the candidate stops talking. After a silence a
  // short countdown shows, and saying anything more cancels it.
  useEffect(() => {
    const timer = setInterval(() => {
      const now = latest.current;
      const quiet = heardAt.current === null ? 0 : performance.now() - heardAt.current;
      if (!now.mic.listening || now.mic.interim || now.sending || quiet < QUIET_MS) {
        setSendIn(null);
      } else if (quiet >= QUIET_MS + COUNTDOWN_MS) {
        void now.send();
      } else {
        setSendIn(Math.ceil((QUIET_MS + COUNTDOWN_MS - quiet) / 1000));
      }
    }, 250);
    return () => clearInterval(timer);
  }, []);

  useGuide(
    turn.ended
      ? null
      : turn.final_question
        ? "This is the last technical question. Take your time."
        : turn.phase === "closing"
          ? "Anything you'd like to ask? Your question is welcome."
          : handsFree
            ? "Answer out loud, the way you would to a person. Stop talking when you're done."
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
    return <Ended id={id} turn={turn} />;
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

  function toggleMic() {
    paused.current = mic.listening;
    if (mic.listening) return pause();
    if (heardAt.current !== null) heardAt.current = performance.now(); // the silence starts over
    hush();
    listen();
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void send();
  }

  const micStatus = sending
    ? "Sending your answer…"
    : sendIn !== null
      ? `Sending your answer in ${sendIn}… keep talking to add more`
      : speaking
        ? "The microphone opens when the question has been read"
        : mic.listening
          ? text || mic.interim
            ? "Listening… stop talking when you're done"
            : "Listening… answer out loud"
          : "Microphone paused";

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
            {(!voiceOn && incoming) || (
              <span className="flex items-center gap-3 text-base">
                <Spinner className="size-4" /> Thinking about your answer…
              </span>
            )}
          </p>
        ) : (
          <p className="min-h-14 text-lg leading-relaxed">
            <Spoken
              text={turn.question ?? ""}
              audible={audible}
              done={!voiceOn || saidSeq === seq}
            />
          </p>
        )}
        {canSpeak && !sending && (
          <div className="mt-4 flex items-center gap-4 text-sm text-muted">
            {speaking ? (
              <span className="flex items-center gap-2 text-brand">
                <span className="size-2 animate-pulse rounded-full bg-brand" /> Speaking…
              </span>
            ) : (
              voiceOn && (
                <button type="button" onClick={ask} className="hover:text-ink">
                  Hear it again
                </button>
              )
            )}
            <button
              type="button"
              onClick={() => setVoiceOn((on) => !on)}
              aria-pressed={voiceOn}
              className="ml-auto flex items-center gap-1.5 hover:text-ink"
            >
              {voiceOn ? <SpeakerIcon className="size-4" /> : <SpeakerOffIcon className="size-4" />}
              {voiceOn ? "Voice on" : "Voice off"}
            </button>
          </div>
        )}
      </div>

      {handsFree ? (
        <div
          className={`rounded-2xl border bg-surface p-3 transition ${
            mic.listening ? "border-brand/60" : "border-line"
          }`}
        >
          <p className="sr-only">Your answer, written as you speak</p>
          <p className="min-h-32 whitespace-pre-wrap p-3 text-[15px] leading-relaxed">
            {text} <span className="text-muted">{mic.interim}</span>
            {!text && !mic.interim && (
              <span className="text-muted/70">Your answer is written here as you speak.</span>
            )}
          </p>
          <div className="flex items-center gap-3 px-3 pb-2">
            <button
              type="button"
              onClick={toggleMic}
              disabled={sending || speaking}
              aria-pressed={mic.listening}
              aria-label={mic.listening ? "Pause the microphone" : "Turn the microphone on"}
              className={`relative grid size-11 shrink-0 place-items-center rounded-full text-white shadow-sm transition disabled:cursor-not-allowed disabled:opacity-50 ${
                mic.listening ? "bg-danger" : "bg-brand hover:bg-brand-dark"
              }`}
            >
              {mic.listening && (
                <span className="absolute inset-0 animate-ping rounded-full bg-danger/40 motion-reduce:hidden" />
              )}
              {mic.listening ? (
                <PauseIcon className="relative size-5" />
              ) : (
                <MicIcon className="relative size-5" />
              )}
            </button>
            <span className={`text-sm ${sendIn !== null ? "text-ink" : "text-muted"}`} role="status">
              {micStatus}
            </span>
          </div>
        </div>
      ) : (
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
      )}

      {mic.blocked && (
        <p role="alert" className="rounded-xl bg-warm-soft px-4 py-3 text-sm text-warm">
          The microphone isn't available, so type your answer for now. To speak instead, allow the
          microphone for this site in the browser's address bar, then{" "}
          <button type="button" onClick={mic.retry} className="font-medium underline">
            try the microphone again
          </button>
          .
        </p>
      )}

      {problem && (
        <p role="alert" className="rounded-xl bg-danger-soft px-4 py-3 text-sm text-danger">
          {problem} Your answer is still here.{" "}
          {handsFree && (
            <button type="submit" className="font-medium underline">
              Send it again
            </button>
          )}
        </p>
      )}
    </form>
  );
}
