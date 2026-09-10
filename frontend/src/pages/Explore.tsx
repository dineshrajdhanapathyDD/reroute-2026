import { useEffect, useMemo, useState } from 'react';
import { Search, ExternalLink } from 'lucide-react';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import SearchInput from '../components/ui/SearchInput';
import Dropdown from '../components/ui/Dropdown';
import EmptyState from '../components/ui/EmptyState';
import { api, type BackendSession } from '../lib/api';

type Facets = { total: number; topics: string[]; levels: string[]; formats: string[]; venues: string[]; days: string[] };
const EMPTY = { topic: '', level: '', format: '', venue: '', day: '', text: '' };

function opts(label: string, values: string[]) {
  return [{ id: '', label: `${label}: All` }, ...values.map((v) => ({ id: v, label: v }))];
}

export default function Explore() {
  const [facets, setFacets] = useState<Facets>({ total: 0, topics: [], levels: [], formats: [], venues: [], days: [] });
  const [filters, setFilters] = useState(EMPTY);
  const [page, setPage] = useState(1);
  const [result, setResult] = useState<{ total: number; pages: number; sessions: BackendSession[] }>({ total: 0, pages: 0, sessions: [] });
  const [loading, setLoading] = useState(false);

  useEffect(() => { api.catalogFacets().then(setFacets).catch(() => {}); }, []);

  useEffect(() => {
    setLoading(true);
    api.catalogFilter({ ...filters, page, limit: 24 })
      .then(setResult)
      .catch(() => setResult({ total: 0, pages: 0, sessions: [] }))
      .finally(() => setLoading(false));
  }, [filters, page]);

  const set = (k: keyof typeof EMPTY, v: string) => { setFilters((f) => ({ ...f, [k]: v })); setPage(1); };

  const dropdowns = useMemo(() => ([
    { k: 'topic' as const, label: 'Topic', options: opts('Topic', facets.topics) },
    { k: 'level' as const, label: 'Level', options: opts('Level', facets.levels) },
    { k: 'format' as const, label: 'Format', options: opts('Format', facets.formats) },
    { k: 'venue' as const, label: 'Venue', options: opts('Venue', facets.venues) },
    { k: 'day' as const, label: 'Day', options: opts('Day', facets.days) },
  ]), [facets]);

  return (
    <div className="flex flex-col gap-6 animate-rise-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold text-text-primary">Explore catalog</h1>
          <p className="mt-1 text-sm text-text-muted">Browse & filter the full re:Invent 2026 catalog.</p>
        </div>
        <Badge status="info">{facets.total} sessions</Badge>
      </div>

      <SearchInput placeholder="Search title or topic..." value={filters.text} onChange={(e) => set('text', e.target.value)} />

      <div className="flex flex-wrap gap-2">
        {dropdowns.map((d) => (
          <Dropdown key={d.k} label={d.label} options={d.options} value={filters[d.k]} onChange={(v) => set(d.k, v)} />
        ))}
        <Button variant="ghost" size="sm" onClick={() => { setFilters(EMPTY); setPage(1); }}>Clear</Button>
      </div>

      <div className="flex items-center justify-between text-sm text-text-muted">
        <span>{loading ? 'Filtering…' : `${result.total} match${result.total === 1 ? '' : 'es'}`}</span>
        {result.pages > 1 && (
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>‹ Prev</Button>
            <span>Page {page} / {result.pages}</span>
            <Button variant="ghost" size="sm" disabled={page >= result.pages} onClick={() => setPage((p) => p + 1)}>Next ›</Button>
          </div>
        )}
      </div>

      {result.sessions.length === 0 && !loading ? (
        <EmptyState icon={<Search size={26} />} title="No sessions match these filters" description="Try clearing some filters." />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {result.sessions.map((s) => (
            <Card key={s.id} className="flex h-full flex-col p-5">
              <div className="flex items-center justify-between">
                <Badge status="neutral">{s.topic}</Badge>
                {(s.match_score ?? 0) > 0 && <Badge status="go">{s.match_score}% match</Badge>}
              </div>
              <p className="mt-3 text-sm font-semibold text-text-primary">{s.title}</p>
              <div className="mt-3 flex flex-wrap items-center gap-1.5 text-xs text-text-muted">
                <span>Level {s.level}</span><span>·</span>
                <span>{s.format}</span><span>·</span>
                <span>{s.venue}</span>
                {s.hands_on && <><span>·</span><span className="text-go">hands-on</span></>}
              </div>
              {(s.catalog_url || s.official_url) && (
                <a href={s.official_url || s.catalog_url} target="_blank" rel="noopener noreferrer"
                  className="mt-4 flex w-fit items-center gap-1.5 text-xs text-signal-400 hover:underline">
                  View on AWS <ExternalLink size={12} />
                </a>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
