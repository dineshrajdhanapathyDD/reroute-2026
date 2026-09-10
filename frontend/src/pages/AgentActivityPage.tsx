import Card from '../components/ui/Card';
import AgentActivity from '../components/agent/AgentActivity';
import { useMission } from '../lib/mission';

export default function AgentActivityPage() {
  const { agentActivity } = useMission();
  return (
    <div className="flex flex-col gap-6 animate-rise-in">
      <div>
        <h1 className="font-display text-2xl font-semibold text-text-primary">Agent activity</h1>
        <p className="mt-1 text-sm text-text-muted">Every decision the Navigator has made or proposed, in order.</p>
      </div>
      <Card className="p-6">
        <AgentActivity items={agentActivity} />
      </Card>
    </div>
  );
}
