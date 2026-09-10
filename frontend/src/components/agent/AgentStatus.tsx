import { Navigation2 } from 'lucide-react';
import clsx from 'clsx';
import type { StatusLevel } from '../../lib/types';

interface AgentStatusProps {
  status: StatusLevel;
  label: string;
}

const dotColor: Record<StatusLevel, string> = {
  go: 'bg-go',
  caution: 'bg-caution',
  critical: 'bg-critical',
  info: 'bg-beacon',
  neutral: 'bg-text-muted',
};

export default function AgentStatus({ status, label }: AgentStatusProps) {
  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-line bg-surface px-3 py-1.5 text-xs font-medium">
      <span className="relative flex h-2 w-2">
        <span className={clsx('absolute inline-flex h-full w-full animate-ping rounded-full opacity-60', dotColor[status])} />
        <span className={clsx('relative inline-flex h-2 w-2 rounded-full', dotColor[status])} />
      </span>
      <Navigation2 size={12} className="text-text-muted" />
      <span className="text-text-secondary">{label}</span>
    </div>
  );
}
