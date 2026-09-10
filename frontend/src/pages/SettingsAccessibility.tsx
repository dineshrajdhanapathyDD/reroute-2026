import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import Button from '../components/ui/Button';
import { useToast } from '../components/ui/Toast';

const options = [
  'Accessible route required',
  'Accessible seating',
  'Captioning',
  'Assistive listening',
  'Sign-language interpretation',
  'Minimize venue changes',
  'Additional transition time',
];

export default function SettingsAccessibility() {
  const [selected, setSelected] = useState<string[]>(['Additional transition time']);
  const { push } = useToast();

  function toggle(opt: string) {
    setSelected((prev) => (prev.includes(opt) ? prev.filter((x) => x !== opt) : [...prev, opt]));
  }

  return (
    <div className="flex max-w-lg flex-col gap-6 animate-rise-in">
      <Link to="/settings" className="flex w-fit items-center gap-1.5 text-sm text-text-muted hover:text-text-primary">
        <ArrowLeft size={15} /> Back to settings
      </Link>

      <div>
        <h1 className="font-display text-2xl font-semibold text-text-primary">Accessibility</h1>
        <p className="mt-1 text-sm text-text-muted">
          These preferences are used only when you select them. We never infer accessibility requirements.
        </p>
      </div>

      <div className="flex flex-col gap-2">
        {options.map((opt) => (
          <label
            key={opt}
            className="flex items-center gap-3 rounded-[var(--radius-control)] border border-line bg-surface px-4 py-3 text-sm text-text-primary"
          >
            <input
              type="checkbox"
              checked={selected.includes(opt)}
              onChange={() => toggle(opt)}
              className="h-4 w-4 accent-[var(--color-signal-500)]"
            />
            {opt}
          </label>
        ))}
      </div>

      <Button className="w-fit" onClick={() => push('Accessibility preferences saved.', 'go')}>
        Save preferences
      </Button>
    </div>
  );
}
