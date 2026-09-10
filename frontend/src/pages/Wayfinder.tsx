import { useMemo, useState } from 'react';
import { MapPin, Footprints, Compass, CircleDot, ExternalLink, Navigation } from 'lucide-react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';
import { useMission } from '../lib/mission';
import { resolveVenue, venueMapLink, directionsLink } from '../lib/venues';

export default function Wayfinder() {
  const { sessions } = useMission();

  // Sessions that have a resolvable venue, in schedule order.
  const routeSessions = useMemo(
    () =>
      [...sessions]
        .filter((s) => s.venue)
        .sort((a, b) => (a.day + a.start).localeCompare(b.day + b.start)),
    [sessions],
  );

  const [destId, setDestId] = useState<string>('');
  const dest = routeSessions.find((s) => s.id === destId) ?? routeSessions[0];
  const destIndex = dest ? routeSessions.findIndex((s) => s.id === dest.id) : -1;
  const prev = destIndex > 0 ? routeSessions[destIndex - 1] : undefined;

  const destVenue = resolveVenue(dest?.venue);
  const fromLabel = prev?.venue ?? 'Your hotel';

  // Real Google Maps links.
  const dirLink = dest ? directionsLink(prev?.venue, dest.venue) : '#';
  const pinLink = dest ? venueMapLink(dest.venue) : '#';

  const routeSteps = dest
    ? [
        `Leave ${fromLabel}`,
        prev ? `Head toward ${dest.venue}` : `Make your way to ${dest.venue}`,
        `Enter ${dest.venue}`,
        dest.room ? `Go to ${dest.room}` : `Find the session room`,
        `Arrive before ${dest.start}`,
      ]
    : [];

  return (
    <div className="flex flex-col gap-6 animate-rise-in">
      <div>
        <h1 className="font-display text-2xl font-semibold text-text-primary">Wayfinder</h1>
        <p className="mt-1 text-sm text-text-muted">Where do you need to go next?</p>
      </div>

      {routeSessions.length === 0 ? (
        <Card className="p-6 text-center">
          <MapPin size={26} className="mx-auto text-text-muted" />
          <p className="mt-3 text-sm text-text-primary">No sessions with a venue yet.</p>
          <p className="mt-1 text-xs text-text-muted">Build a plan first, then Wayfinder will map your route between venues.</p>
        </Card>
      ) : (
        <>
          {/* Destination picker — your real sessions */}
          <div>
            <p className="mb-2 text-sm font-medium text-text-secondary">Going to</p>
            <div className="flex flex-wrap gap-2">
              {routeSessions.slice(0, 8).map((s) => (
                <button
                  key={s.id}
                  onClick={() => setDestId(s.id)}
                  className={
                    (dest?.id === s.id
                      ? 'border-signal-500/50 bg-signal-500/15 text-signal-400 '
                      : 'border-line text-text-secondary ') +
                    'flex items-center gap-1.5 rounded-full border px-3.5 py-2 text-xs'
                  }
                >
                  <MapPin size={12} /> {s.venue}
                  <span className="text-text-muted">· {s.start}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Map card — real venue links */}
          <Card className="relative overflow-hidden p-0">
            <div className="relative flex h-56 items-center justify-center bg-hull sm:h-64">
              <div
                className="absolute inset-0 opacity-30"
                style={{
                  backgroundImage:
                    'linear-gradient(var(--color-line-soft) 1px, transparent 1px), linear-gradient(90deg, var(--color-line-soft) 1px, transparent 1px)',
                  backgroundSize: '28px 28px',
                }}
              />
              <div className="relative flex items-center gap-4">
                <div className="flex flex-col items-center gap-1.5">
                  <CircleDot size={18} className="text-beacon" />
                  <span className="max-w-[80px] truncate text-xs text-text-secondary">{fromLabel}</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="h-px w-10 border-t border-dashed border-line-soft" />
                  <Footprints size={16} className="text-signal-400" />
                  <span className="h-px w-10 border-t border-dashed border-line-soft" />
                </div>
                <div className="flex flex-col items-center gap-1.5">
                  <MapPin size={22} className="text-signal-500" />
                  <span className="max-w-[80px] truncate text-xs text-text-secondary">{dest?.venue}</span>
                </div>
              </div>
              <Badge status={destVenue ? 'go' : 'info'} className="absolute right-3 top-3">
                {destVenue ? '📍 Real venue' : '🟡 Estimated'}
              </Badge>
            </div>

            <div className="flex flex-col gap-3 border-t border-line p-5 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-semibold text-text-primary">{dest?.title}</p>
                <p className="text-xs text-text-muted">
                  {dest?.venue}
                  {dest?.room ? ` · ${dest.room}` : ''}
                </p>
                <p className="mt-1 text-xs text-text-secondary">
                  {dest?.day} · {dest?.start}–{dest?.end}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <a href={pinLink} target="_blank" rel="noopener noreferrer">
                  <Button variant="secondary" size="sm" icon={<ExternalLink size={14} />}>
                    Open venue
                  </Button>
                </a>
                <a href={dirLink} target="_blank" rel="noopener noreferrer">
                  <Button size="sm" icon={<Navigation size={14} />}>
                    Directions
                  </Button>
                </a>
              </div>
            </div>
          </Card>

          {/* Accessible text route summary */}
          <Card className="p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-text-primary">Route summary</p>
              <a
                href={dirLink}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-xs text-signal-400 hover:text-signal-300"
              >
                <Compass size={13} /> Open in Google Maps
              </a>
            </div>
            <ol className="mt-3 space-y-2">
              {routeSteps.map((step, i) => (
                <li key={i} className="flex items-start gap-3 text-sm text-text-secondary">
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-surface-raised font-mono text-[11px] text-text-muted">
                    {i + 1}
                  </span>
                  {step}
                </li>
              ))}
            </ol>
          </Card>
        </>
      )}
    </div>
  );
}
