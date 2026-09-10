import type { ReactNode } from 'react';
import clsx from 'clsx';
import type { StatusLevel } from '../../lib/types';

interface BadgeProps {
  children: ReactNode;
  status?: StatusLevel;
  className?: string;
}

const statusClasses: Record<StatusLevel, string> = {
  go: 'bg-go-soft text-go border-go/30',
  caution: 'bg-caution-soft text-caution border-caution/30',
  critical: 'bg-critical-soft text-critical border-critical/30',
  info: 'bg-beacon-soft text-beacon border-beacon/30',
  neutral: 'bg-surface-raised text-text-secondary border-line',
};

export default function Badge({ children, status = 'neutral', className }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium leading-none',
        statusClasses[status],
        className
      )}
    >
      {children}
    </span>
  );
}
