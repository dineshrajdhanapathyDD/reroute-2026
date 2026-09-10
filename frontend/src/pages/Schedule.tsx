import { useState } from 'react';
import { Compass, MapPin } from 'lucide-react';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import Tabs from '../components/ui/Tabs';
import { useMission } from '../lib/mission';

const days = [
  { id: 'mon', label: 'Mon 30' },
  { id: 'tue', label: 'Tue 1' },
  { id: 'wed', label: 'Wed 2' },
  { id: 'thu', label: 'Thu 3' },
];

export default function Schedule() {
  const [day, setDay] = useState('mon');
  const { scheduleBlocks: todayScheduleBlocks } = useMission();

  return (
    <div className="flex flex-col gap-6 animate-rise-in">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold text-text-primary">Schedule</h1>
          <p className="mt-1 text-sm text-text-muted">Your realistic, transition-aware route for the day.</p>
        </div>
        <Tabs tabs={days} active={day} onChange={setDay} />
      </div>

      <div className="relative pl-6">
        <div className="absolute left-[9px] top-2 bottom-2 w-px bg-line" />
        <div className="mb-4 font-mono text-xs font-medium text-text-muted">MON NOV 30</div>
        <div className="flex flex-col gap-5">
          {todayScheduleBlocks.map((block, i) => (
            <div key={i} className="relative">
              <span
                className={`absolute -left-6 top-1.5 h-3 w-3 rounded-full border-2 border-void ${
                  block.type === 'session' ? 'bg-signal-500' : block.type === 'transition' ? 'bg-beacon' : 'bg-text-muted'
                }`}
              />
              {block.type === 'session' && block.session && (
                <Card interactive className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-mono text-xs text-text-muted">{block.session.start} – {block.session.end}</p>
                      <p className="mt-1 text-sm font-semibold text-text-primary">{block.session.title}</p>
                      <p className="mt-1 flex items-center gap-1.5 text-xs text-text-muted">
                        <MapPin size={12} /> {block.session.venue} {block.session.room && `· ${block.session.room}`}
                      </p>
                      <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                        <Badge status="neutral">Level {block.session.level}</Badge>
                        <Badge status="neutral">{block.session.format}</Badge>
                        <Badge status="go">{block.session.match}% match</Badge>
                      </div>
                    </div>
                    <Button size="sm" variant="secondary" icon={<Compass size={13} />}>
                      Take Me There
                    </Button>
                  </div>
                </Card>
              )}
              {block.type === 'transition' && (
                <div className="flex items-center gap-2 py-1 text-xs">
                  <span className="text-text-muted">{block.label}</span>
                  <Badge status={block.transitionRisk}>{block.transitionRisk === 'caution' ? 'Tight' : 'Comfortable'}</Badge>
                </div>
              )}
              {block.type === 'break' && (
                <div className="flex items-center gap-2 py-1 text-sm text-text-secondary">
                  <span className="font-mono text-xs text-text-muted">{block.time}</span>
                  {block.label}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
