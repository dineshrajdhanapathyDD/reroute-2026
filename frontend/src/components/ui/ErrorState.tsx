import { AlertOctagon } from 'lucide-react';
import Button from './Button';

interface ErrorStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
}

export default function ErrorState({ title = 'Something went wrong', description, onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-[var(--radius-card)] border border-critical/30 bg-critical-soft px-6 py-14 text-center">
      <AlertOctagon size={28} className="mb-4 text-critical" />
      <h4 className="font-display text-sm font-semibold text-text-primary">{title}</h4>
      {description && <p className="mt-1.5 max-w-sm text-sm text-text-muted">{description}</p>}
      {onRetry && (
        <Button variant="secondary" size="sm" className="mt-5" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}
