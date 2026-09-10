import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import clsx from 'clsx';
import { Check, Compass } from 'lucide-react';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';

const destinations = [
  { emoji: '🤖', label: 'Become production-ready at AI agents' },
  { emoji: '🏗️', label: 'Build production cloud architecture' },
  { emoji: '🔐', label: 'Improve cloud security' },
  { emoji: '🧠', label: 'Learn Generative AI' },
  { emoji: '🎓', label: 'Prepare for certification' },
  { emoji: '☁️', label: 'Explore AWS services' },
  { emoji: '✏️', label: 'Create a custom mission' },
];

const roles = ['Developer / Engineer', 'Solution Architect', 'DevOps Engineer', 'Data Engineer', 'Security Specialist', 'Technical Manager', 'Executive', 'Other'];

const formats = ['Workshops', 'Chalk Talks', 'Code Talks', 'Breakouts', 'Lightning Talks'];
const levels = ['100 Foundational', '200 Intermediate', '300 Advanced', '400 Expert'];

const accessibilityOptions = [
  'Accessible route required',
  'Accessible seating',
  'Captioning',
  'Assistive listening',
  'Sign-language interpretation',
  'Minimize venue changes',
  'Additional transition time',
];

const creationSteps = [
  'Reading your goal',
  'Creating priorities',
  'Analyzing sessions',
  'Mapping learning relationships',
  'Building your route',
];

export default function Onboarding() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [destination, setDestination] = useState<string | null>(null);
  const [customGoal, setCustomGoal] = useState('');
  const [role, setRole] = useState<string | null>(null);
  const [selectedFormats, setSelectedFormats] = useState<string[]>(['Workshops', 'Chalk Talks', 'Code Talks']);
  const [selectedLevels, setSelectedLevels] = useState<string[]>(['200 Intermediate', '300 Advanced']);
  const [accessibility, setAccessibility] = useState<string[]>([]);
  const [creationDone, setCreationDone] = useState(0);

  const totalSteps = 6;

  function toggle(list: string[], setList: (v: string[]) => void, value: string) {
    setList(list.includes(value) ? list.filter((v) => v !== value) : [...list, value]);
  }

  useEffect(() => {
    if (step !== 6) return;
    setCreationDone(0);
    const interval = setInterval(() => {
      setCreationDone((d) => {
        if (d >= creationSteps.length) {
          clearInterval(interval);
          return d;
        }
        return d + 1;
      });
    }, 700);
    return () => clearInterval(interval);
  }, [step]);

  return (
    <div className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-5 py-12">
      {step < 6 && (
        <div className="mb-8 flex items-center gap-2">
          {Array.from({ length: totalSteps - 1 }).map((_, i) => (
            <div
              key={i}
              className={clsx('h-1 flex-1 rounded-full', i < step ? 'bg-signal-500' : 'bg-surface-raised')}
            />
          ))}
        </div>
      )}

      {step === 1 && (
        <div className="animate-rise-in">
          <h1 className="font-display text-2xl font-semibold text-text-primary">
            Where do you want your re:Invent journey to take you?
          </h1>
          <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
            {destinations.map((d) => (
              <Card
                key={d.label}
                interactive
                onClick={() => setDestination(d.label)}
                className={clsx('flex items-center gap-3 p-4', destination === d.label && 'border-signal-500/60 bg-signal-500/10')}
              >
                <span className="text-xl">{d.emoji}</span>
                <span className="text-sm text-text-primary">{d.label}</span>
              </Card>
            ))}
          </div>
          {destination === 'Create a custom mission' && (
            <textarea
              value={customGoal}
              onChange={(e) => setCustomGoal(e.target.value)}
              placeholder="I want to become production-ready at building AI agents on AWS."
              className="mt-4 w-full rounded-[var(--radius-control)] border border-line bg-surface p-3.5 text-sm text-text-primary placeholder:text-text-muted focus:border-signal-500"
              rows={3}
            />
          )}
          <Button className="mt-8" fullWidth disabled={!destination} onClick={() => setStep(2)}>
            Continue
          </Button>
        </div>
      )}

      {step === 2 && (
        <div className="animate-rise-in">
          <h1 className="font-display text-2xl font-semibold text-text-primary">What's your role?</h1>
          <p className="mt-1.5 text-sm text-text-muted">This helps tailor session recommendations to your day-to-day work.</p>
          <div className="mt-6 grid grid-cols-2 gap-3">
            {roles.map((r) => (
              <Card
                key={r}
                interactive
                onClick={() => setRole(r)}
                className={clsx('p-4 text-center text-sm text-text-primary', role === r && 'border-signal-500/60 bg-signal-500/10')}
              >
                {r}
              </Card>
            ))}
          </div>
          <div className="mt-8 flex gap-3">
            <Button variant="secondary" onClick={() => setStep(1)}>Back</Button>
            <Button fullWidth disabled={!role} onClick={() => setStep(3)}>Continue</Button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="animate-rise-in">
          <h1 className="font-display text-2xl font-semibold text-text-primary">Learning preferences</h1>
          <div className="mt-6">
            <p className="mb-2.5 text-sm font-medium text-text-secondary">Session formats</p>
            <div className="flex flex-wrap gap-2">
              {formats.map((f) => (
                <button
                  key={f}
                  onClick={() => toggle(selectedFormats, setSelectedFormats, f)}
                  className={clsx(
                    'flex items-center gap-2 rounded-full border px-3.5 py-2 text-sm',
                    selectedFormats.includes(f) ? 'border-signal-500/50 bg-signal-500/15 text-signal-400' : 'border-line text-text-secondary'
                  )}
                >
                  {selectedFormats.includes(f) && <Check size={13} />}
                  {f}
                </button>
              ))}
            </div>
          </div>
          <div className="mt-6">
            <p className="mb-2.5 text-sm font-medium text-text-secondary">Level</p>
            <div className="flex flex-wrap gap-2">
              {levels.map((l) => (
                <button
                  key={l}
                  onClick={() => toggle(selectedLevels, setSelectedLevels, l)}
                  className={clsx(
                    'flex items-center gap-2 rounded-full border px-3.5 py-2 text-sm',
                    selectedLevels.includes(l) ? 'border-signal-500/50 bg-signal-500/15 text-signal-400' : 'border-line text-text-secondary'
                  )}
                >
                  {selectedLevels.includes(l) && <Check size={13} />}
                  {l}
                </button>
              ))}
            </div>
          </div>
          <div className="mt-8 flex gap-3">
            <Button variant="secondary" onClick={() => setStep(2)}>Back</Button>
            <Button fullWidth onClick={() => setStep(4)}>Continue</Button>
          </div>
        </div>
      )}

      {step === 4 && (
        <div className="animate-rise-in">
          <h1 className="font-display text-2xl font-semibold text-text-primary">Schedule preferences</h1>
          <div className="mt-6 space-y-4">
            {[
              ['Maximum sessions/day', '6'],
              ['Minimum break', '20 minutes'],
              ['Lunch', '12:00 – 1:00 PM'],
              ['Earliest session', '9:00 AM'],
              ['Latest session', '6:00 PM'],
              ['Extra transition buffer', '10 minutes'],
            ].map(([label, value]) => (
              <div key={label} className="flex items-center justify-between rounded-[var(--radius-control)] border border-line bg-surface px-4 py-3">
                <span className="text-sm text-text-secondary">{label}</span>
                <span className="font-mono text-sm text-text-primary">{value}</span>
              </div>
            ))}
          </div>
          <div className="mt-8 flex gap-3">
            <Button variant="secondary" onClick={() => setStep(3)}>Back</Button>
            <Button fullWidth onClick={() => setStep(5)}>Continue</Button>
          </div>
        </div>
      )}

      {step === 5 && (
        <div className="animate-rise-in">
          <h1 className="font-display text-2xl font-semibold text-text-primary">Accessibility</h1>
          <p className="mt-1.5 text-sm text-text-muted">
            Select only what applies to you — we never infer accessibility needs.
          </p>
          <div className="mt-6 space-y-2">
            {accessibilityOptions.map((opt) => (
              <label
                key={opt}
                className="flex items-center gap-3 rounded-[var(--radius-control)] border border-line bg-surface px-4 py-3 text-sm text-text-primary"
              >
                <input
                  type="checkbox"
                  checked={accessibility.includes(opt)}
                  onChange={() => toggle(accessibility, setAccessibility, opt)}
                  className="h-4 w-4 accent-[var(--color-signal-500)]"
                />
                {opt}
              </label>
            ))}
          </div>
          <div className="mt-8 flex gap-3">
            <Button variant="secondary" onClick={() => setStep(4)}>Back</Button>
            <Button fullWidth onClick={() => setStep(6)}>Create my mission</Button>
          </div>
        </div>
      )}

      {step === 6 && (
        <div className="flex flex-col items-center text-center animate-rise-in">
          <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-signal-500/15 border border-signal-500/30">
            <Compass size={28} className="text-signal-400" />
          </div>
          <h1 className="font-display text-xl font-semibold text-text-primary">Creating your learning route...</h1>
          <div className="mt-8 w-full max-w-sm space-y-3 text-left">
            {creationSteps.map((s, i) => (
              <div key={s} className="flex items-center gap-3 text-sm">
                {i < creationDone ? (
                  <Check size={16} className="text-go" />
                ) : (
                  <span className={clsx('h-4 w-4 rounded-full border-2 border-line', i === creationDone && 'animate-route-pulse border-signal-500')} />
                )}
                <span className={i < creationDone ? 'text-text-primary' : 'text-text-muted'}>{s}</span>
              </div>
            ))}
          </div>
          {creationDone >= creationSteps.length && (
            <div className="mt-10 animate-rise-in">
              <p className="text-text-primary font-medium">Your route is ready.</p>
              <Button className="mt-4" onClick={() => navigate('/mission')}>
                Enter Mission Control
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
