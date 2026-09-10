import { Link } from 'react-router-dom';
import { ArrowUpRight, MapPin, Footprints } from 'lucide-react';
import Card from '../components/ui/Card';
import ProgressRing from '../components/ui/ProgressRing';
import ProgressBar from '../components/ui/ProgressBar';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import { useMission } from '../lib/mission';

export default function Mission() {
  const { goal: missionGoal, categories, scheduleBlocks: todayScheduleBlocks, journeyScore } = useMission();
  return (
    <div className="flex flex-col gap-6 animate-rise-in">
      {/* Header */}
      <div>
        <p className="text-sm text-text-muted">Good morning</p>
        <h1 className="mt-1 font-display text-2xl font-semibold text-text-primary sm:text-[28px]">
          Your destination
        </h1>
        <p className="mt-1.5 max-w-xl text-text-secondary">{missionGoal}</p>
        <div className="mt-3">
          <Badge status="go">Journey status: On route</Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Journey score */}
        <Card className="flex flex-col items-center justify-center gap-1 p-8 lg:col-span-1">
          <ProgressRing value={journeyScore} label="Journey score" sublabel="live" />
        </Card>

        {/* Navigator insight */}
        <Card glow className="flex flex-col justify-between p-6 lg:col-span-2">
          <div>
            <div className="flex items-center gap-2 text-signal-400">
              <span className="text-lg">🧭</span>
              <span className="text-sm font-semibold">Navigator insight</span>
            </div>
            <p className="mt-3 text-[15px] leading-relaxed text-text-primary">
              Your AI coverage is strong, but your production observability path is incomplete.
            </p>
            <p className="mt-2 text-sm text-text-secondary">I found 3 sessions that can close the gap.</p>
            <p className="mt-3 text-sm font-medium text-go">Journey impact: +8%</p>
          </div>
          <div className="mt-5">
            <Link to="/reroute">
              <Button size="sm" icon={<ArrowUpRight size={15} />}>
                View route options
              </Button>
            </Link>
          </div>
        </Card>
      </div>

      {/* Category coverage */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-display text-base font-semibold text-text-primary">Category coverage</h2>
          <Link to="/learning" className="text-sm text-signal-400 hover:underline">
            View learning map
          </Link>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {categories.map((cat) => (
            <Card key={cat.id} interactive className="p-4">
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-sm font-medium text-text-primary">
                  <span>{cat.emoji}</span>
                  {cat.name}
                </span>
                <span className="font-mono text-sm text-text-secondary">{cat.progress}%</span>
              </div>
              <ProgressBar value={cat.progress} className="mt-3" />
            </Card>
          ))}
        </div>
      </div>

      {/* Map preview */}
      <Card className="p-5">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-2 text-sm font-semibold text-text-primary">
            <MapPin size={15} className="text-signal-400" /> Today's map
          </span>
          <Link to="/wayfinder" className="text-sm text-signal-400 hover:underline">
            Open full map
          </Link>
        </div>
        <div className="mt-4 flex items-center justify-center gap-3 rounded-[var(--radius-control)] border border-line-soft bg-hull py-6">
          <span className="text-xs font-medium text-text-secondary">Venetian</span>
          <span className="flex items-center gap-1 text-text-muted">
            <span className="h-px w-8 bg-line-soft" />
            <Footprints size={14} className="text-beacon" />
            <span className="h-px w-8 bg-line-soft" />
          </span>
          <MapPin size={16} className="text-signal-500" />
          <span className="text-xs font-medium text-text-secondary">Caesars Forum</span>
        </div>
        <p className="mt-3 text-center text-xs text-text-muted">3 venues · 6.4 km · 42 min walking today</p>
      </Card>

      {/* Today's route preview */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-display text-base font-semibold text-text-primary">Today's route</h2>
          <Link to="/schedule" className="text-sm text-signal-400 hover:underline">
            Full schedule
          </Link>
        </div>
        <Card className="divide-y divide-line p-0">
          {todayScheduleBlocks
            .filter((b) => b.type === 'session')
            .slice(0, 3)
            .map((b) => (
              <div key={b.session!.id} className="flex items-center justify-between gap-3 px-5 py-4">
                <div>
                  <p className="font-mono text-xs text-text-muted">{b.session!.start}</p>
                  <p className="mt-1 text-sm font-medium text-text-primary">{b.session!.title}</p>
                  <p className="mt-0.5 text-xs text-text-muted">
                    {b.session!.venue} · {b.session!.format}
                  </p>
                </div>
                <Badge status="go">{b.session!.match}% match</Badge>
              </div>
            ))}
        </Card>
      </div>
    </div>
  );
}
