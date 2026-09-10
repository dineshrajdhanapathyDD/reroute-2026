import clsx from 'clsx';

interface ProgressBarProps {
  value: number;
  className?: string;
  trackClassName?: string;
  barClassName?: string;
}

export default function ProgressBar({ value, className, trackClassName, barClassName }: ProgressBarProps) {
  return (
    <div className={clsx('h-2 w-full overflow-hidden rounded-full bg-surface-raised', trackClassName, className)}>
      <div
        className={clsx('h-full rounded-full bg-signal-500 transition-[width] duration-700 ease-out', barClassName)}
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}
