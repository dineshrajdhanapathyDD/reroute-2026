import type { ButtonHTMLAttributes, ReactNode } from 'react';
import clsx from 'clsx';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
type Size = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  icon?: ReactNode;
  fullWidth?: boolean;
}

const variantClasses: Record<Variant, string> = {
  primary:
    'bg-signal-500 text-void hover:bg-signal-400 active:bg-signal-600 shadow-[0_0_0_1px_rgba(255,122,26,0.4),0_8px_20px_-8px_rgba(255,122,26,0.6)]',
  secondary:
    'bg-surface-raised text-text-primary border border-line hover:bg-surface-hover',
  ghost:
    'bg-transparent text-text-secondary hover:text-text-primary hover:bg-surface-raised',
  danger:
    'bg-critical/15 text-critical border border-critical/40 hover:bg-critical/25',
};

const sizeClasses: Record<Size, string> = {
  sm: 'text-xs px-3 py-1.5 gap-1.5',
  md: 'text-sm px-4 py-2.5 gap-2',
  lg: 'text-sm px-5 py-3 gap-2',
};

export default function Button({
  variant = 'primary',
  size = 'md',
  icon,
  fullWidth,
  className,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      className={clsx(
        'inline-flex items-center justify-center rounded-[var(--radius-control)] font-medium transition-all duration-150 disabled:opacity-40 disabled:pointer-events-none whitespace-nowrap',
        variantClasses[variant],
        sizeClasses[size],
        fullWidth && 'w-full',
        className
      )}
      {...rest}
    >
      {icon}
      {children}
    </button>
  );
}
