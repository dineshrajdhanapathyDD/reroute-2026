import { Link } from 'react-router-dom';
import { Bell, Compass, MessageCircle } from 'lucide-react';
import Avatar from '../ui/Avatar';
import AgentStatus from '../agent/AgentStatus';

export default function Header() {
  return (
    <header className="flex h-[68px] shrink-0 items-center justify-between border-b border-line bg-hull/70 px-4 backdrop-blur-sm lg:px-6">
      {/* Mobile brand — tap to return to Chat (home) */}
      <Link to="/chat" className="flex items-center gap-2 lg:hidden" aria-label="Go to chat">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-signal-500">
          <Compass size={15} className="text-void" strokeWidth={2.5} />
        </div>
        <span className="font-display text-sm font-bold">RE:ROUTE AI</span>
      </Link>
      <div className="hidden lg:block">
        <AgentStatus status="go" label="Navigator active · route stable" />
      </div>
      <div className="flex items-center gap-2 sm:gap-3">
        <Link
          to="/chat"
          className="flex items-center gap-1.5 rounded-full border border-line px-3 py-1.5 text-sm font-medium text-text-secondary hover:border-signal-500/50 hover:bg-signal-500/10 hover:text-signal-400"
        >
          <MessageCircle size={15} />
          <span className="hidden sm:block">Chat</span>
        </Link>
        <button
          aria-label="Notifications"
          className="relative flex h-9 w-9 items-center justify-center rounded-full border border-line text-text-secondary hover:bg-surface-raised hover:text-text-primary"
        >
          <Bell size={16} />
          <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-signal-500" />
        </button>
        <button className="flex items-center gap-2 rounded-full border border-line py-1 pl-1 pr-3 hover:bg-surface-raised">
          <Avatar name="AWS Builder" size={30} />
          <span className="hidden text-sm font-medium sm:block">AWS Builder</span>
        </button>
      </div>
    </header>
  );
}
