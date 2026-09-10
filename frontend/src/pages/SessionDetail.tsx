import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Compass, MapPin, CheckCircle2 } from 'lucide-react';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import AgentExplanation from '../components/agent/AgentExplanation';
import ErrorState from '../components/ui/ErrorState';
import { useMission } from '../lib/mission';

export default function SessionDetail() {
  const { id } = useParams();
  const { sessions } = useMission();
  const session = sessions.find((s) => s.id === id);

  if (!session) {
    return <ErrorState title="Session not found" description="This session may have been removed or the link is incorrect." />;
  }

  return (
    <div className="flex flex-col gap-6 animate-rise-in">
      <Link to="/sessions" className="flex w-fit items-center gap-1.5 text-sm text-text-muted hover:text-text-primary">
        <ArrowLeft size={15} /> Back to sessions
      </Link>

      <div>
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge status="neutral">{session.category}</Badge>
          <Badge status="neutral">Level {session.level}</Badge>
          <Badge status="neutral">{session.format}</Badge>
        </div>
        <h1 className="mt-3 font-display text-2xl font-semibold text-text-primary">{session.title}</h1>
        <p className="mt-2 flex items-center gap-1.5 text-sm text-text-muted">
          <MapPin size={14} /> {session.venue} {session.room && `· ${session.room}`}
          {session.locationVerified ? (
            <span className="ml-1 flex items-center gap-1 text-go"><CheckCircle2 size={12} /> Verified location</span>
          ) : (
            <span className="ml-1 text-caution">Estimated location</span>
          )}
        </p>
      </div>

      <Card className="p-5">
        <div className="flex items-center gap-2 text-signal-400">
          <span>🧭</span>
          <span className="text-sm font-semibold">Why this session</span>
        </div>
        <div className="mt-3">
          <AgentExplanation reason={session.reason} />
        </div>
      </Card>

      {session.description && (
        <Card className="p-5">
          <p className="text-sm font-semibold text-text-primary">Description</p>
          <p className="mt-2 text-sm leading-relaxed text-text-secondary">{session.description}</p>
        </Card>
      )}

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          ['Starts', session.start],
          ['Ends', session.end],
          ['Journey match', `${session.match}%`],
          ['Day', session.day],
        ].map(([label, value]) => (
          <Card key={label} className="p-4">
            <p className="text-xs text-text-muted">{label}</p>
            <p className="mt-1 font-mono text-sm text-text-primary">{value}</p>
          </Card>
        ))}
      </div>

      <div className="flex flex-wrap gap-3">
        <Button icon={<Compass size={15} />}>Take Me There</Button>
        <Button variant="secondary">Add to schedule</Button>
      </div>
    </div>
  );
}
