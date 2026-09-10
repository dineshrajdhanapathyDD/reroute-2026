import { Bot, User } from 'lucide-react';
import type { AgentActivityItem } from '../../lib/types';
import Badge from '../ui/Badge';

export default function AgentActivity({ items }: { items: AgentActivityItem[] }) {
  return (
    <div className="flex flex-col">
      {items.map((item, i) => (
        <div key={item.id} className="relative flex gap-3 pb-6 last:pb-0">
          {i !== items.length - 1 && <span className="absolute left-[15px] top-8 h-full w-px bg-line" />}
          <div className="z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-line bg-surface-raised">
            {item.actor === 'agent' ? <Bot size={14} className="text-signal-400" /> : <User size={14} className="text-beacon" />}
          </div>
          <div className="flex-1 pt-0.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium text-text-primary">{item.action}</span>
              <Badge status={item.status}>{item.status}</Badge>
            </div>
            <p className="mt-0.5 text-sm text-text-muted">{item.detail}</p>
            <span className="mt-1 block font-mono text-[11px] text-text-muted">{item.timestamp}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
