import { Link } from 'react-router-dom';
import { ChevronRight, Accessibility } from 'lucide-react';
import Card from '../components/ui/Card';

const sections = [
  { title: 'Learning destination', desc: 'Update your mission and goals' },
  { title: 'Role', desc: 'Change your role for better recommendations' },
  { title: 'Schedule preferences', desc: 'Max sessions/day, breaks, transition buffer' },
  { title: 'Notifications', desc: 'Route changes, approvals, reminders' },
];

export default function Settings() {
  return (
    <div className="flex flex-col gap-6 animate-rise-in">
      <div>
        <h1 className="font-display text-2xl font-semibold text-text-primary">Settings</h1>
        <p className="mt-1 text-sm text-text-muted">Manage your mission, preferences, and accessibility needs.</p>
      </div>

      <Link to="/settings/accessibility">
        <Card interactive className="flex items-center justify-between p-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-signal-500/12 text-signal-400">
              <Accessibility size={18} />
            </div>
            <div>
              <p className="text-sm font-semibold text-text-primary">Accessibility</p>
              <p className="text-xs text-text-muted">Route, seating, captioning, and transition preferences</p>
            </div>
          </div>
          <ChevronRight size={16} className="text-text-muted" />
        </Card>
      </Link>

      <div className="flex flex-col gap-3">
        {sections.map((s) => (
          <Card key={s.title} interactive className="flex items-center justify-between p-5">
            <div>
              <p className="text-sm font-semibold text-text-primary">{s.title}</p>
              <p className="text-xs text-text-muted">{s.desc}</p>
            </div>
            <ChevronRight size={16} className="text-text-muted" />
          </Card>
        ))}
      </div>
    </div>
  );
}
