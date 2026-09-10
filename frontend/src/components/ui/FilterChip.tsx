import clsx from 'clsx';
import type { ReactNode } from 'react';

interface FilterChipProps {
  active?: boolean;
  onClick?: () => void;
  children: ReactNode;
  icon?: ReactNode;
}

export default function FilterChip({ active, onClick, children, icon }: FilterChipProps) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors',
        active
          ? 'border-signal-500/50 bg-signal-500/15 text-signal-400'
          : 'border-line bg-surface text-text-secondary hover:border-line-soft hover:text-text-primary'
      )}
    >
      {icon}
      {children}
    </button>
  );
}
