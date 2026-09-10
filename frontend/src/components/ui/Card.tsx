import type { HTMLAttributes } from 'react';
import clsx from 'clsx';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  interactive?: boolean;
  glow?: boolean;
}

export default function Card({ interactive, glow, className, children, ...rest }: CardProps) {
  return (
    <div
      className={clsx(
        'rounded-[var(--radius-card)] border border-line bg-surface/80 backdrop-blur-sm',
        interactive && 'cursor-pointer transition-colors duration-150 hover:bg-surface-raised hover:border-line-soft',
        glow && 'shadow-[0_0_0_1px_rgba(255,122,26,0.25),0_20px_40px_-24px_rgba(255,122,26,0.35)]',
        className
      )}
      {...rest}
    >
      {children}
    </div>
  );
}
