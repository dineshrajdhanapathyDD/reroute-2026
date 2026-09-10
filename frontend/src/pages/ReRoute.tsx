import { useState } from 'react';
import { AlertTriangle, Compass } from 'lucide-react';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import EmptyState from '../components/ui/EmptyState';
import ApprovalDialog from '../components/agent/ApprovalDialog';
import { useToast } from '../components/ui/Toast';
import { useMission } from '../lib/mission';
import type { RerouteOption } from '../lib/types';

export default function ReRoute() {
  const { sessions, reroute, acceptReroute } = useMission();
  const { push } = useToast();

  const [dropped, setDropped] = useState<string | null>(null);
  const [options, setOptions] = useState<RerouteOption[]>([]);
  const [metrics, setMetrics] = useState<{ label: string; before: string; after: string; direction: string }[]>([]);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [approvalOpen, setApprovalOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const droppedSession = sessions.find((s) => s.id === dropped);
  const option = options.find((o) => o.id === selectedOption);

  const trigger = async (sessionId: string) => {
    setDropped(sessionId);
    setLoading(true);
    setOptions([]);
    setSelectedOption(null);
    const r = await reroute(sessionId, 'Session is full');
    setOptions(r.options);
    setMetrics(r.metrics);
    setSelectedOption(r.recommendedId ?? r.options[0]?.id ?? null);
    setLoading(false);
  };

  const arrow = (d: string) => (d === 'up' ? '↑' : d === 'down' ? '↓' : '·');

  return (
    <div className="flex flex-col gap-6 animate-rise-in">
      <div>
        <h1 className="font-display text-2xl font-semibold text-text-primary">ReRoute</h1>
        <p className="mt-1 text-sm text-text-muted">Simulate a session becoming full — the agents find live alternatives.</p>
      </div>

      {/* Current route — pick a session to mark full */}
      {!dropped && (
        <Card className="p-5">
          <p className="text-sm font-semibold text-text-primary">Your route today</p>
          <p className="mt-1 text-xs text-text-muted">Mark a session as full to trigger a live ReRoute.</p>
          <div className="mt-4 divide-y divide-line">
            {sessions.slice(0, 8).map((s) => (
              <div key={s.id} className="flex items-center justify-between gap-3 py-3">
                <div>
                  <p className="text-sm font-medium text-text-primary">{s.title}</p>
                  <p className="mt-0.5 text-xs text-text-muted">{s.day} · {s.venue} · {s.format}</p>
                </div>
                <Button variant="secondary" size="sm" onClick={() => trigger(s.id)}>Mark full</Button>
              </div>
            ))}
          </div>
        </Card>
      )}

      {dropped && (
        <>
          <Card className="flex items-start gap-3 border-caution/30 bg-caution-soft p-4">
            <AlertTriangle size={18} className="mt-0.5 shrink-0 text-caution" />
            <div>
              <p className="text-sm font-medium text-text-primary">
                Route interrupted: {droppedSession?.title ?? dropped}
              </p>
              <p className="mt-1 text-sm text-text-secondary">
                This session is full. Your learning objective is still protected — the Recovery Navigator found alternatives.
              </p>
            </div>
          </Card>

          {loading ? (
            <p className="text-sm text-text-muted">Finding alternatives…</p>
          ) : options.length === 0 ? (
            <EmptyState icon={<Compass size={26} />} title="No alternatives found"
              description="Try a different session or broaden your goal." />
          ) : (
            <>
              <div className="flex flex-col gap-4">
                {options.map((opt) => (
                  <Card key={opt.id} interactive onClick={() => setSelectedOption(opt.id)}
                    className={`p-5 ${selectedOption === opt.id ? 'border-signal-500/60 bg-signal-500/8' : ''}`}>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-semibold text-text-primary">{opt.title}</p>
                          {opt.recommended && <Badge status="go">Recommended</Badge>}
                        </div>
                        <p className="mt-2 text-sm text-text-secondary">{opt.reason}</p>
                        <p className="mt-2 text-xs font-medium text-signal-400">{opt.impact}</p>
                      </div>
                      <input type="radio" checked={selectedOption === opt.id} onChange={() => setSelectedOption(opt.id)}
                        className="mt-1 h-4 w-4 shrink-0 accent-[var(--color-signal-500)]" />
                    </div>
                  </Card>
                ))}
              </div>

              {metrics.length > 0 && (
                <Card className="p-5">
                  <p className="text-sm font-semibold text-text-primary">Route impact</p>
                  <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
                    {metrics.map((m) => (
                      <div key={m.label} className="rounded-[var(--radius-control)] border border-line-soft bg-hull px-3 py-2">
                        <p className="text-[10px] uppercase tracking-wide text-text-muted">{m.label}</p>
                        <p className="mt-0.5 text-sm text-text-primary">
                          {m.before} → {m.after} <span className={m.direction === 'up' ? 'text-go' : m.direction === 'down' ? 'text-critical' : 'text-text-muted'}>{arrow(m.direction)}</span>
                        </p>
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              <div className="flex gap-3">
                <Button disabled={!selectedOption} icon={<Compass size={15} />} onClick={() => setApprovalOpen(true)}>
                  Review & approve
                </Button>
                <Button variant="ghost" onClick={() => { setDropped(null); setOptions([]); }}>Cancel</Button>
              </div>
            </>
          )}
        </>
      )}

      {option && (
        <ApprovalDialog
          open={approvalOpen}
          onClose={() => setApprovalOpen(false)}
          onApprove={async () => {
            setApprovalOpen(false);
            if (dropped) await acceptReroute(dropped, option.id);
            push('Reroute approved — your schedule has been updated.', 'go');
            setDropped(null); setOptions([]);
          }}
          onReject={() => {
            setApprovalOpen(false);
            push('Reroute rejected. Your original schedule stays unchanged.', 'neutral');
          }}
          title={option.title}
          reason={option.reason}
          impact={option.impact}
        />
      )}
    </div>
  );
}
