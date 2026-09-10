import { useEffect, useState } from 'react';

interface ProgressRingProps {
  value: number; // 0-100
  size?: number;
  strokeWidth?: number;
  label?: string;
  sublabel?: string;
}

export default function ProgressRing({ value, size = 200, strokeWidth = 14, label, sublabel }: ProgressRingProps) {
  const [animated, setAnimated] = useState(0);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  useEffect(() => {
    const t = requestAnimationFrame(() => setAnimated(value));
    return () => cancelAnimationFrame(t);
  }, [value]);

  const offset = circumference - (animated / 100) * circumference;

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
          className="fill-none stroke-surface-raised"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          className="fill-none stroke-signal-500 transition-[stroke-dashoffset] duration-1000 ease-out"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="font-display text-4xl font-bold tabular-nums">{Math.round(animated)}%</span>
        {label && <span className="mt-1 text-[11px] font-medium tracking-wide text-text-muted">{label}</span>}
        {sublabel && <span className="mt-2 text-xs font-medium text-go">{sublabel}</span>}
      </div>
    </div>
  );
}
