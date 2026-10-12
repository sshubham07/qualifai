# ADR-0022: The live room talks: voice runs in the browser, the transcript stays text

- Status: Accepted
- Date: 2026-10-12

## Context
ADR-0006 made the MVP text-only and deferred voice. A typed chat does not feel like an interview: nobody reads the question to you, and nobody answers an interviewer by typing into a box. ADR-0006 kept an event contract for this: the engine emits `say(text)` and consumes `candidate_turn_ended(text)`, so voice can be an adapter on either side of it.

## Options considered
1. Stay text-only until V3.
2. Use the browser's own speech engines: `speechSynthesis` reads the question, `SpeechRecognition` turns the spoken answer into text. The server keeps seeing only text.
3. Server-side speech models behind `qualifai.llm` (a TTS route and a speech-to-text route in `models.yaml`), with audio streamed both ways.

## Decision
Option 2. The room reads each question aloud, then opens the microphone by itself. What is heard is written on the page as it is said and autosaved as the draft. There is no send button: after 3 seconds of silence a 3-second countdown shows, saying anything more cancels it, and otherwise the answer is sent with the same `POST /answers` and stored as the turn. The candidate can pause the microphone, which also holds the answer back, and can switch the interviewer's voice off. Where the browser cannot listen or the microphone is refused, the room falls back to a text box with a send button. The interviewer has a name and a greeting in `content/interviewer.yaml`: at the start he introduces himself and asks for an introduction, as fixed text in front of the opening question, and the room picks an Indian English voice (`en-IN`) when the device has one and listens for Indian English.

## Consequences
No backend change, no new model route, no keys and no cost, and the code that picks the next question still only handles text. The evidence check keeps working because the stored answer is exactly the text the candidate saw and sent. Voice quality is whatever the device has. Speech recognition exists in Chrome, Edge and Safari but not Firefox, where the room falls back to typing; in Chrome the audio goes to the browser vendor's speech service, not to us. Recognition gets technical terms wrong at times, and a spoken answer cannot be corrected before it is sent, so a misheard word reaches the transcript and the evaluation. A long thinking pause after starting to speak ends the answer; the two timings are constants in `frontend/src/pages/Room.tsx`. Nothing is sent until the candidate has said something, so a candidate who stays silent is moved on only by the time window. There is no barge-in: the microphone is paused while the question is read. The typing integrity signals (time to first keystroke, idle time) say nothing about a spoken answer; a signal for how an answer was given is a follow-up. Option 3 stays open as a later swap behind the same contract. Supersedes the "voice deferred" part of ADR-0006; avatar and webcam remain deferred.
