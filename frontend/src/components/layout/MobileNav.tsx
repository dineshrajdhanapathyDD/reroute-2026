import { NavLink } from 'react-router-dom';
import { Compass, Calendar, Map, RefreshCw, MessageCircle } from 'lucide-react';
import clsx from 'clsx';

const items = [
  { to: '/chat', label: 'Chat', icon: MessageCircle },
  { to: '/mission', label: 'Mission', icon: Compass },
  { to: '/schedule', label: 'Schedule', icon: Calendar },
  { to: '/wayfinder', label: 'Maps', icon: Map },
  { to: '/reroute', label: 'ReRoute', icon: RefreshCw },
];

export default function MobileNav() {
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 flex border-t border-line bg-hull/95 backdrop-blur-sm lg:hidden">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) =>
            clsx(
              'flex flex-1 flex-col items-center gap-1 py-2.5 text-[11px] font-medium',
              isActive ? 'text-signal-400' : 'text-text-muted'
            )
          }
        >
          <item.icon size={19} strokeWidth={2} />
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}
