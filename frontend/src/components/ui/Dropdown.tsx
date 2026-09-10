import { useState, useRef, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';
import clsx from 'clsx';

interface DropdownProps {
  label: string;
  options: { id: string; label: string }[];
  value?: string;
  onChange: (id: string) => void;
}

export default function Dropdown({ label, options, value, onChange }: DropdownProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const selected = options.find((o) => o.id === value);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-[var(--radius-control)] border border-line bg-surface px-3 py-2 text-sm text-text-secondary hover:border-line-soft hover:text-text-primary"
      >
        {selected ? selected.label : label}
        <ChevronDown size={14} className={clsx('transition-transform', open && 'rotate-180')} />
      </button>
      {open && (
        <div className="absolute left-0 z-20 mt-1.5 min-w-[180px] overflow-hidden rounded-[var(--radius-control)] border border-line bg-surface-raised shadow-xl animate-rise-in">
          {options.map((opt) => (
            <button
              key={opt.id}
              onClick={() => {
                onChange(opt.id);
                setOpen(false);
              }}
              className={clsx(
                'block w-full px-3.5 py-2 text-left text-sm hover:bg-surface-hover',
                value === opt.id ? 'text-signal-400' : 'text-text-secondary'
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
