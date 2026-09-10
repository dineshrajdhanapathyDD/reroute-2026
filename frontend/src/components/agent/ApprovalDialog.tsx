import { Compass } from 'lucide-react';
import Modal from '../ui/Modal';
import Button from '../ui/Button';
import AgentExplanation from './AgentExplanation';

interface ApprovalDialogProps {
  open: boolean;
  onClose: () => void;
  onApprove: () => void;
  onReject: () => void;
  title: string;
  reason: string;
  impact: string;
}

export default function ApprovalDialog({ open, onClose, onApprove, onReject, title, reason, impact }: ApprovalDialogProps) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Approval needed"
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onReject}>
            Reject
          </Button>
          <Button variant="primary" size="sm" icon={<Compass size={15} />} onClick={onApprove}>
            Approve reroute
          </Button>
        </>
      }
    >
      <p className="font-display text-sm font-semibold text-text-primary">{title}</p>
      <div className="mt-3">
        <AgentExplanation reason={reason} impact={impact} />
      </div>
      <p className="mt-3 text-xs text-text-muted">
        Re:Route only changes your schedule with your approval. Nothing updates automatically.
      </p>
    </Modal>
  );
}
