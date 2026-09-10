import { createContext, useCallback, useContext, useState, type ReactNode } from 'react';
import { CheckCircle2, AlertTriangle, Info, XCircle, X } from 'lucide-react';
import clsx from 'clsx';
import type { StatusLevel } from '../../lib/types';

interface ToastItem {
  id: number;
  message: string;
  status: StatusLevel;
}

interface ToastContextValue {
  push: (message: string, status?: StatusLevel) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const icons: Record<StatusLevel, ReactNode> = {
  go: <CheckCircle2 size={16} className="text-go" />,
  caution: <AlertTriangle size={16} className="text-caution" />,
  critical: <XCircle size={16} className="text-critical" />,
  info: <Info size={16} className="text-beacon" />,
  neutral: <Info size={16} className="text-text-muted" />,
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const push = useCallback((message: string, status: StatusLevel = 'go') => {
    const id = Date.now();
    setToasts((t) => [...t, { id, message, status }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4000);
  }, []);

  return (
    <ToastContext.Provider value={{ push }}>
      {children}
      <div className="fixed bottom-5 right-5 z-[100] flex flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={clsx(
              'flex items-center gap-2 rounded-[var(--radius-control)] border border-line bg-surface-raised px-4 py-3 text-sm shadow-2xl animate-rise-in min-w-[260px]'
            )}
          >
            {icons[t.status]}
            <span className="flex-1 text-text-primary">{t.message}</span>
            <button onClick={() => setToasts((ts) => ts.filter((x) => x.id !== t.id))} className="text-text-muted hover:text-text-primary">
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
