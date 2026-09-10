// Agent Watch — the autonomous background monitor surface.
//
// This is the "runs quietly, pings you only on a real decision" side of
// Re:Route AI. It watches your planned sessions, scans on an interval (standing
// in for the production cron/EventBridge tick), and stays calm and green while
// the route is healthy. When a session fills up, gets cancelled, or a transition
// turns infeasible, it raises a decision with pre-analyzed alternatives and asks
// you to approve or dismiss — the only moment you're pulled in.
import { useCallback, useEffect, useRef, useState } from 'react';
import { ShieldCheck, AlertTriangle, RadioTower, Check, X, Play, Pause } from 'lucide-react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';
import { useMission } from '../lib/mission';
import { api, type MonitorStatus, type MonitorDecision } from '../lib/api';

const SCAN_INTERVAL_MS = 15000;

export default function Monitor() {
  const { selectedIds, sessions, goal } = useMission();
  const [status, setStatus] = useState<MonitorStatus | null>(null);
  const [live, setLive] = useState(true);
  const [lastScan, setLastScan] = useState<Date | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const started = useRef(false);

  const idsForWatch = selectedIds.length ? selectedIds : sessions.slice(0, 8).map((s) => s.id);

  // Start watching once the plan is available.
  useEffect(() => {
    if (started.current || idsForWatch.length === 0) return;
    started.current = true;
    api.monitorWatch(idsForWatch, goal).then(setStatus).catch(() => setLive(false));
  }, [idsForWatch, goal]);

  const runScan = useCallback(async () => {
    try {
      await api.monitorScan();
      const st = await api.monitorStatus();
      setStatus(st);
      setLastScan(new Date());
      setLive(true);
    } catch {
      setLive(false);
    }
  }, []);

  // Autonomous scan loop.
  useEffect(() => {
    if (!live) return;
    const t = setInterval(runScan, SCAN_INTERVAL_MS);
    return () => clearInterval(t);
  }, [live, runScan]);

  async function resolve(d: MonitorDecision, action: 'approve' | 'dismiss', optionId?: string) {
    setBusy(d.id);
    try {
      await api.monitorResolve(d.id, action, optionId);
      const st = await api.monitorStatus();
      setStatus(st);
    } finally {
      setBusy(null);
    }
  }

  const pending = status?.pending_decisions ?? [];
  const resolved = status?.resolved_decisions ?? [];
  const healthy = pending.length === 0;

  return (
    <div className="flex flex-col gap-6 animate-rise-in">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold text-text-primary">Agent Watch</h1>
          <p className="mt-1 text-sm text-text-muted">
            Re:Route runs in the background and only pings you when there's a real decision to make.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="secondary" icon={live ? <Pause size={14} /> : <Play size={14} />} onClick={() => setLive((v) => !v)}>
            {live ? 'Pause' : 'Resume'}
          </Button>
          <Button size="sm" icon={<RadioTower size={14} />} onClick={runScan}>Scan now</Button>
        </div>
      </div>

      {/* Live status banner */}
      <Card glow={!healthy} className="flex items-center gap-4 p-5">
        <div
          className={
            (healthy ? 'bg-go/15 text-go' : 'bg-signal-500/15 text-signal-400') +
            ' flex h-12 w-12 shrink-0 items-center justify-center rounded-xl'
          }
        >
          {healthy ? <ShieldCheck size={24} /> : <AlertTriangle size={24} />}
        </div>
        <div className="flex-1">
          <p className="text-sm font-semibold text-text-primary">
            {healthy ? 'Route healthy — nothing needs you' : `${pending.length} decision${pending.length > 1 ? 's' : ''} waiting for you`}
          </p>
          <p className="mt-0.5 text-xs text-text-muted">
            Watching {status?.watched_sessions ?? idsForWatch.length} sessions · {status?.scan_count ?? 0} scans
            {lastScan && ` · last check ${lastScan.toLocaleTimeString()}`}
          </p>
        </div>
        <span className="flex items-center gap-1.5 text-xs text-text-muted">
          <span className={(live ? 'bg-go animate-route-pulse' : 'bg-text-muted') + ' h-2 w-2 rounded-full'} />
          {live ? 'Monitoring' : 'Paused'}
        </span>
      </Card>

      {/* Pending decisions — the only time the agent surfaces */}
      {pending.map((d) => (
        <Card key={d.id} glow className="p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-2">
              <Badge status={d.severity === 'high' ? 'critical' : 'caution'}>
                {d.kind.replace('_', ' ')}
              </Badge>
              <span className="text-sm font-semibold text-text-primary">{d.title}</span>
            </div>
          </div>
          <p className="mt-2 text-sm text-text-secondary">{d.summary}</p>

          {d.options.length > 0 && (
            <div className="mt-4 space-y-2">
              <p className="text-xs font-medium text-text-muted">Recommended replacements</p>
              {d.options.map((o) => (
                <div
                  key={o.id}
                  className={
                    (o.id === d.recommended_option_id ? 'border-signal-500/50 bg-signal-500/8 ' : 'border-line ') +
                    'flex items-center justify-between gap-3 rounded-[var(--radius-control)] border p-3'
                  }
                >
                  <div>
                    <p className="text-sm font-medium text-text-primary">
                      {o.title}
                      {o.id === d.recommended_option_id && (
                        <span className="ml-2 text-[11px] font-normal text-signal-400">recommended</span>
                      )}
                    </p>
                    <p className="mt-0.5 text-xs text-text-muted">
                      {o.venue} · {o.day} · {o.match_score}% match
                    </p>
                  </div>
                  <Button size="sm" disabled={busy === d.id} onClick={() => resolve(d, 'approve', o.id)}>
                    Use this
                  </Button>
                </div>
              ))}
            </div>
          )}

          <div className="mt-4 flex gap-2">
            <Button
              size="sm"
              icon={<Check size={14} />}
              disabled={busy === d.id || !d.recommended_option_id}
              onClick={() => resolve(d, 'approve')}
            >
              Approve recommended
            </Button>
            <Button size="sm" variant="ghost" icon={<X size={14} />} disabled={busy === d.id} onClick={() => resolve(d, 'dismiss')}>
              Dismiss
            </Button>
          </div>
        </Card>
      ))}

      {/* Resolved history */}
      {resolved.length > 0 && (
        <Card className="p-5">
          <p className="text-sm font-semibold text-text-primary">Handled</p>
          <div className="mt-3 divide-y divide-line">
            {resolved.map((d) => (
              <div key={d.id} className="flex items-center justify-between gap-3 py-2.5">
                <div>
                  <p className="text-sm text-text-primary">{d.title}</p>
                  <p className="mt-0.5 text-xs text-text-muted">{d.resolution}</p>
                </div>
                <Badge status={d.status === 'resolved' ? 'go' : 'neutral'}>{d.status}</Badge>
              </div>
            ))}
          </div>
        </Card>
      )}

      {!live && (
        <p className="text-center text-xs text-text-muted">Monitoring paused — resume to keep watching your route.</p>
      )}
    </div>
  );
}
