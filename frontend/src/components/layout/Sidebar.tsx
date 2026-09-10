import { NavLink, Link } from 'react-router-dom';
import { Compass, Calendar, Search, Filter, Layers, Lightbulb, BookOpen, RefreshCw, Map, ClipboardList, Settings, Activity, MessageCircle, ShieldCheck } from 'lucide-react';
import clsx from 'clsx';

const navItems = [
  { to: '/chat', label: 'Chat', icon: MessageCircle },
  { to: '/monitor', label: 'Agent Watch', icon: ShieldCheck },
  { to: '/mission', label: 'Mission', icon: Compass },
  { to: '/plans', label: 'Plan A / B / C', icon: Layers },
  { to: '/schedule', label: 'Schedule', icon: Calendar },
  { to: '/sessions', label: 'Sessions', icon: Search },
  { to: '/explore', label: 'Explore Catalog', icon: Filter },
  { to: '/prep', label: 'Preparation', icon: Lightbulb },
  { to: '/learning', label: 'Learning', icon: BookOpen },
  { to: '/reroute', label: 'ReRoute', icon: RefreshCw },
  { to: '/wayfinder', label: 'Wayfinder', icon: Map },
  { to: '/journey', label: 'Journey', icon: ClipboardList },
  { to: '/agent/activity', label: 'Agent Activity', icon: Activity },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export default function Sidebar() {
  return (
    <aside className="hidden w-[240px] shrink-0 flex-col border-r border-line bg-hull/60 lg:flex">
      <Link to="/chat" className="flex h-[68px] items-center gap-2 border-b border-line px-5 transition-colors hover:bg-surface-raised" aria-label="Go to chat">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-signal-500">
          <Compass size={17} className="text-void" strokeWidth={2.5} />
        </div>
        <span className="font-display text-[15px] font-bold tracking-tight">RE:ROUTE AI</span>
      </Link>
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 rounded-[var(--radius-control)] px-3 py-2.5 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-signal-500/12 text-signal-400 border border-signal-500/25'
                  : 'text-text-secondary border border-transparent hover:bg-surface-raised hover:text-text-primary'
              )
            }
          >
            <item.icon size={17} strokeWidth={2} />
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-line px-3 py-4">
        <div className="rounded-[var(--radius-control)] border border-line-soft bg-surface px-3 py-2.5">
          <p className="text-xs font-medium text-text-secondary">re:Invent 2026</p>
          <p className="mt-0.5 text-xs text-text-muted">Las Vegas · Nov 30 – Dec 4</p>
        </div>
      </div>
    </aside>
  );
}
