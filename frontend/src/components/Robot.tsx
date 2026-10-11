export type Mood = "wave" | "think" | "talk" | "happy";

const TEAL = "#5eead4";

// The robot interviewer: the home page walkthrough's host and every other page's guide.
// `line` is what it is saying; the mouth "speaks" again each time it changes.
export function Robot({ mood, className, line }: { mood: Mood; className?: string; line?: string }) {
  const armUp = mood === "wave" || mood === "happy";
  return (
    <svg viewBox="0 0 200 240" className={className}>
      <ellipse cx="100" cy="230" rx="46" ry="6" fill="#000" opacity="0.3" className="robot-shadow" />
      <g className="robot-bob">
        <path d="M100 38V18" stroke="#c7d2fe" strokeWidth="4" strokeLinecap="round" />
        <circle cx="100" cy="14" r="7" fill={TEAL} className="robot-pulse" />
        <rect x="22" y="72" width="12" height="30" rx="5" fill="#a5b4fc" />
        <rect x="166" y="72" width="12" height="30" rx="5" fill="#a5b4fc" />
        <rect x="32" y="38" width="136" height="100" rx="30" fill="#fff" />
        <rect x="46" y="54" width="108" height="68" rx="20" fill="#101828" />
        {mood === "happy" ? (
          <path
            d="M69 87q9-13 18 0M113 87q9-13 18 0"
            fill="none"
            stroke={TEAL}
            strokeWidth="5"
            strokeLinecap="round"
          />
        ) : (
          <g transform={mood === "think" ? "translate(5 -5)" : undefined}>
            <circle cx="78" cy="82" r="9" fill={TEAL} className="robot-blink" />
            <circle cx="122" cy="82" r="9" fill={TEAL} className="robot-blink" />
          </g>
        )}
        <path
          key={line ?? mood}
          d="M86 100q14 13 28 0"
          fill="none"
          stroke="#fff"
          strokeWidth="4.5"
          strokeLinecap="round"
          className="robot-talk"
        />
        <rect x="88" y="138" width="24" height="10" fill="#a5b4fc" />
        <rect x="30" y="152" width="16" height="46" rx="8" fill="#c7d2fe" />
        <circle cx="38" cy="200" r="10" fill="#fff" />
        <g className={armUp ? (mood === "wave" ? "robot-arm robot-wave" : "robot-arm robot-raised") : ""}>
          <rect x="154" y="152" width="16" height="46" rx="8" fill="#c7d2fe" />
          <circle cx="162" cy="200" r="10" fill="#fff" />
        </g>
        <rect x="52" y="146" width="96" height="66" rx="22" fill="#fff" />
        <rect x="78" y="162" width="44" height="26" rx="8" fill="#eef2ff" />
        <circle cx="100" cy="175" r="6" fill="#4263eb" className="robot-pulse" />
      </g>
    </svg>
  );
}
