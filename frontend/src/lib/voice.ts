// Voice for the interview room (ADR-0022): the browser reads each question aloud and turns the
// spoken answer into text. Both engines are the browser's own; the server only ever sees text.
import { useCallback, useEffect, useRef, useState } from "react";

// The Web Speech recognition API is not in TypeScript's DOM types; this is the part used here.
type Heard = {
  resultIndex: number;
  results: { length: number; [i: number]: { isFinal: boolean; 0: { transcript: string } } };
};
type Recognition = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((e: Heard) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
};
type RecognitionClass = new () => Recognition;

const speech = window as unknown as {
  SpeechRecognition?: RecognitionClass;
  webkitSpeechRecognition?: RecognitionClass;
};
const RecognitionImpl = speech.SpeechRecognition ?? speech.webkitSpeechRecognition;

export const canSpeak = "speechSynthesis" in window;
export const canListen = Boolean(RecognitionImpl);

// The interviewer is Indian (content/interviewer.yaml), so he sounds it where the device can, and
// the recogniser is told to expect Indian English.
const LANG = "en-IN";
const INTERVIEWER_VOICES = /rishi|prabhat|ravi/i; // male en-IN voices: macOS, Edge, Windows
const GOOD_VOICES = /natural|google us english|samantha|aria|jenny/i;
const SPEAK_DELAY_MS = 150;
// Silence and our own abort() end a session without anything being wrong.
const HARMLESS = new Set(["no-speech", "aborted"]);

if (canSpeak) speechSynthesis.getVoices(); // Chrome loads the list on first ask; ask early

function pickVoice(): SpeechSynthesisVoice | null {
  const english = speechSynthesis.getVoices().filter((v) => v.lang.startsWith("en"));
  const indian = english.filter((v) => v.lang.replace("_", "-") === LANG);
  return (
    indian.find((v) => INTERVIEWER_VOICES.test(v.name)) ??
    indian[0] ??
    english.find((v) => GOOD_VOICES.test(v.name)) ??
    english[0] ??
    null
  );
}

// One utterance per sentence: Chrome's network voices go silent about 15 seconds into a long one
// and then never report that they finished.
const sentences = (text: string) =>
  text
    .split(/(?<=[.!?])\s+/)
    .map((part) => part.trim())
    .filter(Boolean);

// Holding `parts` keeps them alive. `player` is the server's recording of the same text.
type Job = { parts: SpeechSynthesisUtterance[]; timers: number[]; player?: HTMLAudioElement };

// Says text aloud: the server's recording (`audioUrl`, a natural voice) when it can be played,
// otherwise the browser's own voice. `onDone` runs when it has been said, or when nothing could
// be said; not when we cut it short ourselves.
export function useSpeaker() {
  const [speaking, setSpeaking] = useState(false);
  const [audible, setAudible] = useState(false); // sound has actually started coming out
  const job = useRef<Job | null>(null);

  const stop = useCallback(() => {
    job.current?.timers.forEach((timer) => {
      clearTimeout(timer);
      clearInterval(timer);
    });
    job.current?.player?.pause();
    job.current = null;
    if (canSpeak) speechSynthesis.cancel();
    setSpeaking(false);
    setAudible(false);
  }, []);

  const speakLocally = useCallback(
    (text: string, onDone?: () => void) => {
      stop();
      const voice = canSpeak ? pickVoice() : null;
      const parts = (canSpeak ? sentences(text) : []).map((sentence) => {
        const utterance = new SpeechSynthesisUtterance(sentence);
        utterance.lang = voice?.lang ?? LANG;
        utterance.voice = voice;
        return utterance;
      });
      if (parts.length === 0) return onDone?.();

      const mine: Job = { parts, timers: [] };
      const finish = () => {
        if (job.current !== mine) return;
        stop();
        onDone?.();
      };
      // An error: the browser refuses to speak before the first click on a page (a reload, say).
      for (const part of parts) part.onerror = finish;
      parts[0].onstart = () => job.current === mine && setAudible(true);
      parts[parts.length - 1].onend = finish;
      job.current = mine;
      setSpeaking(true);

      // Chrome drops speech queued in the same tick as a cancel(), so start a moment later.
      mine.timers.push(
        window.setTimeout(() => {
          speechSynthesis.resume(); // a synthesiser left paused stays silent
          for (const part of parts) speechSynthesis.speak(part);
          // Some engines stop without an end event; don't leave the room waiting on them.
          let idle = 0;
          mine.timers.push(
            window.setInterval(() => {
              idle = speechSynthesis.speaking || speechSynthesis.pending ? 0 : idle + 1;
              if (idle >= 3) finish();
            }, 500),
          );
        }, SPEAK_DELAY_MS),
      );
    },
    [stop],
  );

  const speak = useCallback(
    (text: string, onDone?: () => void, audioUrl?: string) => {
      if (!audioUrl) return speakLocally(text, onDone);
      stop();
      const player = new Audio(audioUrl);
      const mine: Job = { parts: [], timers: [], player };
      const mineStill = () => job.current === mine;
      player.onplaying = () => mineStill() && setAudible(true);
      player.onended = () => {
        if (!mineStill()) return;
        stop();
        onDone?.();
      };
      // No recording (the server has no voice, or it failed), or the browser will not play yet.
      const fallBack = () => mineStill() && speakLocally(text, onDone);
      player.onerror = fallBack;
      job.current = mine;
      setSpeaking(true);
      player.play().catch(fallBack);
    },
    [stop, speakLocally],
  );

  useEffect(() => stop, [stop]);
  return { speaking, audible, speak, stop };
}

// Listens until told to stop. Finished phrases go to `onPhrase`; `interim` is the phrase still
// being heard. The browser ends a session after a pause, so it is started again while wanted.
export function useDictation(onPhrase: (text: string) => void) {
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");
  const [blocked, setBlocked] = useState(false); // no microphone, or permission refused
  const session = useRef<Recognition | null>(null);
  const wanted = useRef(false);
  const denied = useRef(false); // stays set, so each new question does not ask again
  const deliver = useRef(onPhrase);
  useEffect(() => {
    deliver.current = onPhrase;
  });

  const start = useCallback(() => {
    if (!RecognitionImpl || wanted.current || denied.current) return;
    const rec = new RecognitionImpl();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = LANG;
    rec.onresult = (e) => {
      let live = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const result = e.results[i];
        if (result.isFinal) deliver.current(result[0].transcript);
        else live += result[0].transcript;
      }
      setInterim(live);
    };
    rec.onerror = (e) => {
      if (HARMLESS.has(e.error) || session.current !== rec) return;
      wanted.current = false;
      denied.current = true;
      setBlocked(true);
    };
    rec.onend = () => {
      if (session.current !== rec) return; // a newer session has taken over
      setInterim("");
      if (wanted.current) {
        try {
          rec.start();
          return;
        } catch {
          wanted.current = false;
        }
      }
      setListening(false);
    };
    wanted.current = true;
    session.current = rec;
    try {
      rec.start();
      setListening(true);
    } catch {
      wanted.current = false;
    }
  }, []);

  // Stop and keep what was heard so far.
  const stop = useCallback(() => {
    wanted.current = false;
    session.current?.stop();
  }, []);

  // Stop and drop anything not delivered yet.
  const cancel = useCallback(() => {
    wanted.current = false;
    session.current?.abort();
    session.current = null;
    setInterim("");
    setListening(false);
  }, []);

  // After the candidate has allowed the microphone in the browser.
  const retry = useCallback(() => {
    denied.current = false;
    setBlocked(false);
    start();
  }, [start]);

  useEffect(() => cancel, [cancel]);
  return { listening, interim, blocked, start, stop, cancel, retry };
}
