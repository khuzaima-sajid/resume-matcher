"use client";

export default function ScoreGauge({ score }: { score: number }) {
  const radius = 70;
  const stroke = 12;
  const normalizedRadius = radius - stroke / 2;
  const circumference = normalizedRadius * 2 * Math.PI;
  const offset = circumference - (score / 100) * circumference;

  const color =
    score >= 80 ? "#16a34a" : score >= 60 ? "#4f6df5" : score >= 40 ? "#d97706" : "#dc2626";

  const label =
    score >= 80
      ? "Strong match"
      : score >= 60
      ? "Good match"
      : score >= 40
      ? "Moderate match"
      : "Weak match";

  return (
    <div className="flex flex-col items-center gap-2">
      <svg height={radius * 2} width={radius * 2} className="-rotate-90">
        <circle
          stroke="#e5edff"
          fill="transparent"
          strokeWidth={stroke}
          r={normalizedRadius}
          cx={radius}
          cy={radius}
        />
        <circle
          stroke={color}
          fill="transparent"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${circumference} ${circumference}`}
          style={{
            strokeDashoffset: offset,
            transition: "stroke-dashoffset 1s ease-out, stroke 0.5s",
          }}
          r={normalizedRadius}
          cx={radius}
          cy={radius}
        />
      </svg>
      <div className="-mt-[7.5rem] flex flex-col items-center">
        <span className="text-4xl font-bold" style={{ color }}>
          {score}
        </span>
        <span className="text-xs text-slate-400">/ 100</span>
      </div>
      <span className="mt-14 text-sm font-medium" style={{ color }}>
        {label}
      </span>
    </div>
  );
}
