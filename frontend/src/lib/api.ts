// Thin client for the QualifAI API. Same origin: FastAPI serves the built app, and the Vite
// dev server proxies /v1 to it.

export const COMPANY_TYPES = [
  {
    id: "service",
    name: "Service-based",
    blurb: "Fundamentals, clear project explanation and communication.",
  },
  {
    id: "startup",
    name: "Startup",
    blurb: "Practical problem solving, ownership and speed.",
  },
  {
    id: "product",
    name: "Product-based",
    blurb: "Depth, trade-offs and scale. Resume claims get challenged.",
  },
  {
    id: "maang",
    name: "MAANG",
    blurb: "The highest bar: rigorous reasoning and large-scale design.",
  },
] as const;

export type CompanyType = (typeof COMPANY_TYPES)[number]["id"];

// What the interview concentrates on. Ids and lengths mirror content/rounds/*.yaml.
export const FOCUSES = [
  {
    id: "r1_technical",
    name: "General",
    minutes: 45,
    blurb: "Your projects and the skills the job description asks for.",
  },
  {
    id: "dsa",
    name: "DSA",
    minutes: 45,
    blurb: "Data structures and algorithms: approach, complexity and edge cases.",
  },
  {
    id: "r2_lld",
    name: "Low-level design",
    minutes: 60,
    blurb: "Classes, responsibilities and designs that stay easy to extend.",
  },
  {
    id: "r3_hld",
    name: "High-level design",
    minutes: 60,
    blurb: "System design: architecture, data, scaling and failure handling.",
  },
  {
    id: "r4_managerial",
    name: "Managerial",
    minutes: 30,
    blurb: "Ownership, conflict, failures and the decisions you made.",
  },
] as const;

export type Focus = (typeof FOCUSES)[number]["id"];

export const focusName = (id: string) =>
  FOCUSES.find((f) => f.id === id)?.name ?? id.replaceAll("_", " ");

// Limits mirror InterviewRequest in src/qualifai/domain/models.py.
export const LIMITS = {
  resume: { min: 200, max: 40_000 },
  jd: { min: 100, max: 20_000 },
  years: { min: 0, max: 40 },
};

export type InterviewInput = {
  resume_text: string;
  jd_text: string;
  round_type: Focus;
  company_tier: CompanyType;
  experience_min_years: number;
  experience_max_years: number;
};

export type InterviewStatus =
  | "submitted"
  | "preparing"
  | "ready"
  | "in_progress"
  | "completed"
  | "evaluating"
  | "report_ready"
  | "failed"
  | "expired";

export type Accepted = {
  meet_id: string; // the interview id; keep it to check back on the interview
  status: InterviewStatus;
};

export type StatusOut = Accepted & {
  round_type: string; // the interview focus
  target_minutes: number;
  detected_role: string | null; // known once the resume and job description have been checked
  support: string | null;
  failure_code: string | null;
  failure_reason: string | null;
  progress: string[]; // prep steps started so far; while preparing the last one is running
  expires_at: string | null;
  server_now: string;
};

const ROLE_NAMES: Record<string, string> = {
  backend_sde: "Backend engineer",
  fullstack: "Full-stack engineer",
  frontend: "Frontend engineer",
  data_eng: "Data engineer",
  devops: "DevOps engineer",
  integration: "Integration engineer",
  qa: "QA engineer",
  ml_eng: "ML engineer",
};

export const roleName = (id: string) => ROLE_NAMES[id] ?? id.replaceAll("_", " ");

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

const FIELD_LABELS: Record<string, string> = {
  resume_text: "Resume",
  jd_text: "Job description",
  round_type: "Interview focus",
  company_tier: "Company type",
  experience_min_years: "Experience",
  experience_max_years: "Experience",
};

async function errorFrom(res: Response): Promise<ApiError> {
  const body = await res.json().catch(() => null);
  if (typeof body?.message === "string") {
    return new ApiError(body.message, res.status); // domain errors
  }
  const first = Array.isArray(body?.detail) ? body.detail[0] : null;
  if (first?.msg) {
    const field = FIELD_LABELS[String(first.loc?.at(-1))];
    return new ApiError(field ? `${field}: ${first.msg}` : first.msg, res.status);
  }
  if (typeof body?.detail === "string") {
    return new ApiError(body.detail, res.status);
  }
  return new ApiError(
    "Something went wrong on our side. Please try again in a moment.",
    res.status,
  );
}

export async function createInterview(input: InterviewInput): Promise<Accepted> {
  const res = await fetch("/v1/interviews", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw await errorFrom(res);
  return res.json();
}

export async function getInterview(id: string): Promise<StatusOut> {
  const res = await fetch(`/v1/interviews/${id}`, { cache: "no-store" });
  if (!res.ok) throw await errorFrom(res);
  return res.json();
}

// ---- the live interview

// Where the interview stands: a question to answer, or the end.
export type Turn = {
  question: string | null;
  seq: number | null; // sent back as `question_seq` with the answer
  ended: boolean;
  phase: string | null;
  final_question: boolean;
  draft: string | null; // text autosaved before the page was reloaded
  started_at: string;
  target_end_at: string;
  server_now: string;
};

// What the page saw while the answer was typed. Offsets are from when the question appeared.
export type AnswerInput = {
  question_seq: number;
  text: string;
  first_keystroke_ms: number | null;
  idle_ms: number; // longest pause without typing
  pastes: { at_ms: number; chars: number }[];
};

async function send<T>(path: string, method: string, body?: unknown): Promise<T> {
  const res = await fetch(`/v1/interviews/${path}`, {
    method,
    cache: "no-store",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) throw await errorFrom(res);
  return (res.status === 204 ? undefined : await res.json()) as T;
}

export const startInterview = (id: string, token: string | null) =>
  send<Turn>(`${id}/start`, "POST", { token });

export const getRoom = (id: string) => send<Turn>(`${id}/room`, "GET");

export const submitAnswer = (id: string, answer: AnswerInput) =>
  send<Turn>(`${id}/answers`, "POST", answer);

export const saveDraft = (id: string, question_seq: number, text: string) =>
  send<void>(`${id}/draft`, "PUT", { question_seq, text });

export const ANSWER_MAX = 8000; // mirrors Answer in src/qualifai/domain/models.py
