import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layers, Lightbulb } from 'lucide-react';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import EmptyState from '../components/ui/EmptyState';
import { api, type BackendPlan } from '../lib/api';
import { useMission } from '../lib/mission';

interface ABCPlan {
  key: string;
  label: string;
  rationale: string;
  tip?: string;
  plan: BackendPlan;
  summary: Record<string, number>;
}

export default function Plans() {
  const { mission, applyPlan } = useMission();
  const navigate = useNavigate();
  const [plans, setPlans] = useState<ABCPlan[]>([]);
  const [active, setActive] = useState('A');
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    setLoading(true);
    try {
      const res = await api.plansABC(mission);
      setPlans(res.plans as ABCPlan[]);
      setActive(res.plans?.[0]?.key ?? 'A');
    } catch { /* keep empty */ }
    finally { setLoading(false); }
  };

  const current = plans.find((p) => p.key === active);

  const use = (p: ABCPlan) => {
    applyPlan(p.plan);
    navigate('/mission');
  };

  return (
    <div className="flex flex-col gap-6 animate-rise-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold text-text-primary">Plan A / B / C</h1>
          <p className="mt-1 text-sm text-text-muted">Three routes for one goal — the ideal, a backup, and a low-risk plan.</p>
        </div>
        <Button size="sm" icon={<Layers size={15} />} onClick={generate} disabled={loading}>
          {loading ? 'Building…' : 'Generate plans'}
        </Button>
      </div>

      {plans.length === 0 ? (
        <EmptyState icon={<Layers size={26} />} title="Generate three ranked itineraries"
          description="Always have a backup. Generate Plan A (ideal), B (backup), and C (low-risk)." />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            {plans.map((p) => (
              <Card key={p.key} interactive glow={p.key === active}
                onClick={() => setActive(p.key)} className="flex cursor-pointer flex-col p-5">
                <div className="flex items-center justify-between">
                  <span className="font-display text-base font-semibold text-text-primary">{p.label}</span>
                  {p.key === active && <Badge status="go">Selected</Badge>}
                </div>
                <p className="mt-2 min-h-[56px] text-xs text-text-muted">{p.rationale}</p>
                {p.tip && (
                  <p className="mt-2 flex items-start gap-1.5 rounded-[var(--radius-control)] border border-line-soft bg-hull px-2.5 py-2 text-xs text-text-secondary">
                    <Lightbulb size={13} className="mt-0.5 shrink-0 text-beacon" /> {p.tip}
                  </p>
                )}
                <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                  <Metric k="Journey" v={`${p.summary.journey_score}%`} />
                  <Metric k="Route" v={`${p.summary.route_quality}%`} />
                  <Metric k="Sessions" v={p.summary.sessions} />
                  <Metric k="Walking" v={`${p.summary.walking_km} km`} />
                  <Metric k="Venue hops" v={p.summary.venue_changes} />
                  <Metric k="Hands-on" v={`${p.summary.hands_on}%`} />
                </div>
                <Button size="sm" className="mt-4" onClick={(e) => { e.stopPropagation(); use(p); }}>
                  Use {p.label.split(' ')[1]}
                </Button>
              </Card>
            ))}
          </div>

          {current && (
            <Card className="p-5">
              <h2 className="font-display text-base font-semibold text-text-primary">{current.label} — sessions</h2>
              <div className="mt-3 divide-y divide-line">
                {current.plan.sessions.map((s) => (
                  <div key={s.id} className="flex items-center justify-between gap-3 py-3">
                    <div>
                      <p className="text-sm font-medium text-text-primary">{s.title}</p>
                      <p className="mt-0.5 text-xs text-text-muted">{s.day} · {s.format} · {s.venue}</p>
                    </div>
                    <Badge status="go">{s.match_score}%</Badge>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

function Metric({ k, v }: { k: string; v: string | number }) {
  return (
    <div className="rounded-[var(--radius-control)] border border-line-soft bg-hull px-2.5 py-1.5">
      <p className="text-[10px] uppercase tracking-wide text-text-muted">{k}</p>
      <p className="font-mono text-sm text-text-primary">{v}</p>
    </div>
  );
}
