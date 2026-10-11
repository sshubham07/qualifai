import { type CSSProperties, type ReactNode, useState } from "react";
import { GuideContext, type Line } from "../lib/guide";
import { Robot } from "./Robot";

// The robot from the home page, small, in the corner of every page that has something to
// explain. Clicking it hides or shows what it is saying.
export function GuideProvider({ children }: { children: ReactNode }) {
  const [line, setLine] = useState<Line | null>(null);
  const [open, setOpen] = useState(true);

  return (
    <GuideContext.Provider value={setLine}>
      {children}
      {line && (
        <aside
          aria-label="Guide"
          className="pointer-events-none fixed right-3 bottom-3 z-40 flex flex-col items-end gap-2.5 sm:right-5 sm:bottom-5"
        >
          <div aria-live="polite" className="pointer-events-auto">
            {open && (
              <p
                key={line.says}
                className="flow-in relative w-60 rounded-2xl border border-line bg-surface px-4 py-3 text-sm leading-snug shadow-xl shadow-ink/10"
              >
                {line.says.split(" ").map((word, i) => (
                  <span key={i} className="flow-fade" style={{ "--d": `${0.15 + i * 0.03}s` } as CSSProperties}>
                    {word}{" "}
                  </span>
                ))}
                <span className="absolute right-8 -bottom-1.5 size-3 rotate-45 border-r border-b border-line bg-surface" />
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={() => setOpen(!open)}
            aria-expanded={open}
            aria-label={open ? "Hide the guide's tips" : "Show the guide's tips"}
            className="flow-stage pointer-events-auto grid size-18 cursor-pointer place-items-center rounded-2xl shadow-xl shadow-ink/20 transition hover:scale-105"
          >
            <Robot mood={line.mood} line={open ? line.says : undefined} className="w-13" />
          </button>
        </aside>
      )}
    </GuideContext.Provider>
  );
}
