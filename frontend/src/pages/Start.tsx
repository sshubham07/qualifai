import { type FormEvent, type ReactNode, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Spinner } from "../components/icons";
import {
  COMPANY_TYPES,
  LIMITS,
  type CompanyType,
  createInterview,
} from "../lib/api";

const inputClass =
  "rounded-xl border border-line bg-surface px-3.5 py-2.5 text-[15px] placeholder:text-muted/60 focus:border-brand focus:outline-none focus:ring-3 focus:ring-brand/15";

function Section(props: {
  step: number;
  title: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <fieldset className="rounded-2xl border border-line bg-surface p-5 sm:p-6">
      <legend className="sr-only">{props.title}</legend>
      <div className="mb-4 flex items-baseline gap-3">
        <span className="font-mono text-sm text-brand">0{props.step}</span>
        <div>
          <h2 className="font-semibold">{props.title}</h2>
          {props.hint && <p className="text-sm text-muted">{props.hint}</p>}
        </div>
      </div>
      {props.children}
    </fieldset>
  );
}

function TextBlock(props: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  limits: { min: number; max: number };
  placeholder: string;
  rows: number;
}) {
  const length = props.value.trim().length;
  const short = length > 0 && length < props.limits.min;
  return (
    <div>
      <label htmlFor={props.id} className="sr-only">
        {props.label}
      </label>
      <textarea
        id={props.id}
        required
        rows={props.rows}
        minLength={props.limits.min}
        maxLength={props.limits.max}
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
        placeholder={props.placeholder}
        className={`${inputClass} w-full resize-y bg-canvas/50 leading-relaxed`}
      />
      <p className={`mt-1.5 text-sm ${short ? "text-warm" : "text-muted"}`}>
        {short
          ? `${props.limits.min - length} more characters needed`
          : `${length.toLocaleString()} characters`}
      </p>
    </div>
  );
}

function StartForm() {
  const navigate = useNavigate();
  const [resume, setResume] = useState("");
  const [jd, setJd] = useState("");
  const [company, setCompany] = useState<CompanyType | null>(null);
  const [minYears, setMinYears] = useState("");
  const [maxYears, setMaxYears] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!company) return setError("Choose the type of company you are interviewing for.");
    if (Number(minYears) > Number(maxYears)) {
      return setError("The experience range should go from the lower to the higher number.");
    }
    setError(null);
    setSending(true);
    try {
      const accepted = await createInterview({
        resume_text: resume.trim(),
        jd_text: jd.trim(),
        company_tier: company,
        experience_min_years: Number(minYears),
        experience_max_years: Number(maxYears),
      });
      navigate(`/interviews/${accepted.meet_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setSending(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="mt-8 space-y-5">
      <Section step={1} title="Your resume" hint="Paste it as plain text.">
        <TextBlock
          id="resume"
          label="Resume"
          value={resume}
          onChange={setResume}
          limits={LIMITS.resume}
          rows={9}
          placeholder="Backend Engineer, 3.5 years. Designed microservices on Kubernetes for a fintech platform…"
        />
      </Section>

      <Section step={2} title="The job description" hint="The posting you are preparing for.">
        <TextBlock
          id="jd"
          label="Job description"
          value={jd}
          onChange={setJd}
          limits={LIMITS.jd}
          rows={7}
          placeholder="Backend Engineer (3–5 years). Must have: Python, PostgreSQL, REST API design…"
        />
      </Section>

      <Section step={3} title="Type of company" hint="This sets how deep the questions go and the bar for the verdict.">
        <div role="radiogroup" aria-label="Type of company" className="grid gap-3 sm:grid-cols-2">
          {COMPANY_TYPES.map((type) => {
            const selected = company === type.id;
            return (
              <label
                key={type.id}
                className={`cursor-pointer rounded-xl border p-4 transition has-focus-visible:ring-3 has-focus-visible:ring-brand/30 ${
                  selected
                    ? "border-brand bg-brand-soft"
                    : "border-line hover:border-brand/50"
                }`}
              >
                <input
                  type="radio"
                  name="company"
                  value={type.id}
                  checked={selected}
                  onChange={() => setCompany(type.id)}
                  className="sr-only"
                />
                <span className="flex items-center justify-between font-medium">
                  {type.name}
                  <span
                    className={`size-4 rounded-full border-2 ${
                      selected ? "border-brand bg-brand ring-2 ring-white ring-inset" : "border-line"
                    }`}
                  />
                </span>
                <span className="mt-1 block text-sm text-muted">{type.blurb}</span>
              </label>
            );
          })}
        </div>
      </Section>

      <Section step={4} title="Experience range" hint="Years of experience the role asks for.">
        <div className="flex items-center gap-3">
          <label htmlFor="min-years" className="sr-only">
            Minimum years
          </label>
          <input
            id="min-years"
            type="number"
            inputMode="numeric"
            required
            min={LIMITS.years.min}
            max={LIMITS.years.max}
            value={minYears}
            onChange={(e) => setMinYears(e.target.value)}
            placeholder="3"
            className={`${inputClass} w-24 text-center`}
          />
          <span className="text-muted">to</span>
          <label htmlFor="max-years" className="sr-only">
            Maximum years
          </label>
          <input
            id="max-years"
            type="number"
            inputMode="numeric"
            required
            min={LIMITS.years.min}
            max={LIMITS.years.max}
            value={maxYears}
            onChange={(e) => setMaxYears(e.target.value)}
            placeholder="5"
            className={`${inputClass} w-24 text-center`}
          />
          <span className="text-muted">years</span>
        </div>
      </Section>

      {error && (
        <p role="alert" className="rounded-xl border border-danger/20 bg-danger-soft px-4 py-3 text-sm text-danger">
          {error}
        </p>
      )}

      <div className="flex flex-wrap items-center gap-4 pt-1">
        <button
          type="submit"
          disabled={sending}
          className="inline-flex items-center gap-2.5 rounded-full bg-brand px-7 py-3 font-medium text-white shadow-sm transition hover:bg-brand-dark disabled:opacity-70"
        >
          {sending && <Spinner className="size-4" />}
          {sending ? "Submitting…" : "Prepare my interview"}
        </button>
        <p className="text-sm text-muted">A 45-minute technical round. Preparation takes a few minutes.</p>
      </div>
    </form>
  );
}

export function Start() {
  return (
    <div className="mx-auto w-full max-w-3xl px-5 py-12">
      <h1 className="text-3xl font-semibold tracking-tight">Start an interview</h1>
      <p className="mt-2 text-muted">
        Tell us about you and the role. We first check that the resume and the
        job description are both for a software engineering role, then prepare
        your interview in the background.
      </p>
      <StartForm />
    </div>
  );
}
