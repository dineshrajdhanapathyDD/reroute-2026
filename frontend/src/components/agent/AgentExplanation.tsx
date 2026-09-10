import { Sparkles } from 'lucide-react';

export default function AgentExplanation({ reason, impact }: { reason: string; impact?: string }) {
  return (
    <div className="flex gap-2.5 rounded-[var(--radius-control)] border border-beacon/25 bg-beacon-soft px-3.5 py-3">
      <Sparkles size={15} className="mt-0.5 shrink-0 text-beacon" />
      <div>
        <p className="text-sm text-text-secondary">{reason}</p>
        {impact && <p className="mt-1 text-xs font-medium text-go">{impact}</p>}
      </div>
    </div>
  );
}
