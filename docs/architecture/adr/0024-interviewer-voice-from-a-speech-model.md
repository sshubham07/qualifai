# ADR-0024: The interviewer's voice comes from a speech model; the browser's voice is the fallback

- Status: Accepted
- Date: 2026-10-12

## Context
ADR-0022 gave the room a voice using the browser's own speech synthesis. It costs nothing, but on most devices it sounds robotic, and a candidate who is put off by the voice does not stay for the interview. ADR-0022 left a server-side speech model open as a later swap behind the same contract: the engine still emits text.

## Options considered
1. Keep the browser voice and only pick better system voices.
2. A hosted open-weight speech model (Groq's Orpheus) through the gateway.
3. An open-weight speech model run locally: Kokoro-82M behind an OpenAI-compatible speech server.

## Decision
Option 3, built so that option 2 is a config change. `speech` is an LLM task: `content/models.yaml` names the provider, model, voice, audio format and the longest text one request carries. Kokoro runs as a Docker service (`make up-voice`, started by `start.sh`). `LLMGateway.speak` cuts the text at sentence ends and sends the pieces one after another, passing each on as soon as it is ready, so the first sentence is heard while the rest is being made. `GET /v1/interviews/{id}/turns/{seq}/audio` streams a stored interviewer turn; the page names a turn and never sends words, so the endpoint cannot be used to voice arbitrary text. The room plays that audio, shows the question's words in step with it, and falls back to the browser's voice when the request fails.

## Consequences
The voice is natural, the same on every device, free and offline: no key, no quota, no terms to accept. Only `qualifai.llm` talks to the speech server, and the model is chosen in config. On a laptop CPU the first sentence takes 2 to 4 seconds to arrive, so every question starts after a short pause; the text waits for the voice so the two stay together. The Docker image is several gigabytes. Audio is not stored: a replay is served from the browser's cache, and a reload synthesises the turn again. Kokoro's English voices are American or British, so the interviewer's name and accent do not match. The hosted route (Orpheus on Groq) needs its terms accepted in the provider's console and answers only in WAV, which is sent whole, not in pieces. The candidate's own speech is still transcribed by the browser (ADR-0022). Supersedes the "browser voice" part of ADR-0022 for the interviewer's side.
