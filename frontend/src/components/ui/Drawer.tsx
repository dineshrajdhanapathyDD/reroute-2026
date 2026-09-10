import type { ReactNode } from 'react';
import { X } from 'lucide-react';

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  side?: 'right' | 'bottom';
}

export default function Drawer({ open, onClose, title, children, side = 'right' }: DrawerProps) {
  if (!open) return null;
  const isBottom = side === 'bottom';
  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="absolute inset-0 bg-void/80 backdrop-blur-sm" onClick={onClose} />
      <div
        className={
          isBottom
            ? 'relative z-10 mt-auto w-full rounded-t-2xl border-t border-line bg-surface-raised p-5 animate-rise-in max-h-[85vh] overflow-y-auto'
            : 'relative z-10 ml-auto h-full w-full max-w-md border-l border-line bg-surface-raised p-5 overflow-y-auto animate-rise-in'
        }
      >
        <div className="mb-4 flex items-center justify-between">
          {isBottom && <div className="absolute left-1/2 top-2 h-1 w-10 -translate-x-1/2 rounded-full bg-line" />}
          <h3 className="font-display text-base font-semibold">{title}</h3>
          <button onClick={onClose} aria-label="Close" className="rounded-full p-1.5 text-text-muted hover:bg-surface-hover hover:text-text-primary">
            <X size={16} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
