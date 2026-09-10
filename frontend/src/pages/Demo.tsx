import { useState } from 'react';
import { Check, Play } from 'lucide-react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import clsx from 'clsx';

const demoSteps = [
  'Mission created',
  'Route created',
  'Map shows today\u2019s journey',
  'Session location confirmed',
  'Walking transition tracked',
  'User misses a session',
  'ReRoute finds an alternative',
  'Map updates',
  'New session location shown',
  'Wayfinder shows the new route',
  'User approves',
];

export default function Demo() {
  const [progress, setProgress] = useState(0);
  const running = progress > 0 && progress < demoSteps.length;

  function runDemo() {
    setProgress(1);
    const interval = setInterval(() => {
      setProgress((p) => {
        if (p >= demoSteps.length) {
          clearInterval(interval);
          return p;
        }
        return p + 1;
      });
    }, 900);
  }

  return (
    <div className="flex flex-col gap-6 animate-rise-in">
      <div>
        <h1 className="font-display text-2xl font-semibold text-text-primary">Demo mode</h1>
        <p className="mt-1 text-sm text-text-muted">Walk through the full Re:Route AI experience, end to end.</p>
      </div>

      <Card className="p-6">
        <Button icon={<Play size={15} />} disabled={running} onClick={runDemo}>
          {progress >= demoSteps.length ? 'Replay demo' : running ? 'Running...' : 'Run demo'}
        </Button>

        <div className="mt-6 flex flex-col gap-3">
          {demoSteps.map((step, i) => (
            <div key={step} className="flex items-center gap-3">
              <span
                className={clsx(
                  'flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-[11px] font-mono',
                  i < progress ? 'border-signal-500 bg-signal-500 text-void' : 'border-line text-text-muted'
                )}
              >
                {i < progress ? <Check size={12} /> : i + 1}
              </span>
              <span className={i < progress ? 'text-sm text-text-primary' : 'text-sm text-text-muted'}>{step}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
