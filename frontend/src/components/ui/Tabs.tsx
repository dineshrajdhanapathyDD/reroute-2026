import clsx from 'clsx';

interface TabsProps {
  tabs: { id: string; label: string }[];
  active: string;
  onChange: (id: string) => void;
  className?: string;
}

export default function Tabs({ tabs, active, onChange, className }: TabsProps) {
  return (
    <div className={clsx('inline-flex items-center gap-1 rounded-[var(--radius-control)] border border-line bg-surface p-1', className)}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={clsx(
            'rounded-[7px] px-3.5 py-1.5 text-sm font-medium transition-colors',
            active === tab.id ? 'bg-signal-500 text-void' : 'text-text-secondary hover:text-text-primary'
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
