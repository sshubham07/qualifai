// What the robot guide is saying (rendered by components/Guide.tsx).
import { createContext, useContext, useEffect } from "react";
import type { Mood } from "../components/Robot";

export type Line = { says: string; mood: Mood };

export const GuideContext = createContext<(line: Line | null) => void>(() => {});

// A page calls this with what the robot should say right now (null: nothing to say).
export function useGuide(says: string | null, mood: Mood = "talk") {
  const setLine = useContext(GuideContext);
  useEffect(() => {
    setLine(says ? { says, mood } : null);
    return () => setLine(null);
  }, [setLine, says, mood]);
}
