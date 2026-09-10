import type { ReactNode } from 'react';

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}

export default function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-[var(--radius-card)] border border-dashed border-line px-6 py-14 text-center">
      {icon && <div className="mb-4 text-text-muted">{icon}</div>}
      <h4 className="font-display text-sm font-semibold text-text-primary">{title}</h4>
      {description && <p className="mt-1.5 max-w-sm text-sm text-text-muted">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
