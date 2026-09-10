import { Search } from 'lucide-react';
import type { InputHTMLAttributes } from 'react';
import clsx from 'clsx';

export default function SearchInput({ className, ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div className={clsx('relative flex items-center', className)}>
      <Search size={16} className="pointer-events-none absolute left-3 text-text-muted" />
      <input
        type="text"
        className="w-full rounded-[var(--radius-control)] border border-line bg-surface py-2.5 pl-9 pr-3 text-sm text-text-primary placeholder:text-text-muted focus:border-signal-500"
        {...rest}
      />
    </div>
  );
}
