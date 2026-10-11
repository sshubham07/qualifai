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

// Limits mirror InterviewRequest in src/qualifai/domain/models.py.
export const LIMITS = {
  resume: { min: 200, max: 40_000 },
  jd: { min: 100, max: 20_000 },
  years: { min: 0, max: 40 },
};

export type InterviewInput = {
  email: string;
  resume_text: string;
  jd_text: string;
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
  interview_id: string;
  status: InterviewStatus;
  detected_role: string;
  support: string;
};

export type StatusOut = Accepted & {
  progress: string[];
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
  email: "Email",
  company_tier: "Company type",
  experience_min_years: "Experience",
  experience_max_years: "Experience",
};

async function errorFrom(res: Response): Promise<ApiError> {
  const body = await res.json().catch(() => null);
  if (typeof body?.message === "string") {
    return new ApiError(body.message, res.status); // domain errors: unsupported role, invalid document
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
