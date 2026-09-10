import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import SearchInput from '../components/ui/SearchInput';
import FilterChip from '../components/ui/FilterChip';
import EmptyState from '../components/ui/EmptyState';
import { useMission } from '../lib/mission';
import { Search } from 'lucide-react';

const categoryFilters = ['Agentic AI', 'Generative AI', 'Architecture', 'Security', 'Observability', 'Cost Optimization'];

export default function Sessions() {
  const { sessions } = useMission();
  const [query, setQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState<string | null>(null);

  const filtered = useMemo(() => {
    return sessions.filter((s) => {
      const matchesQuery = s.title.toLowerCase().includes(query.toLowerCase());
      const matchesCategory = !activeCategory || s.category === activeCategory;
      return matchesQuery && matchesCategory;
    });
  }, [sessions, query, activeCategory]);

  return (
    <div className="flex flex-col gap-6 animate-rise-in">
      <div>
        <h1 className="font-display text-2xl font-semibold text-text-primary">Sessions</h1>
        <p className="mt-1 text-sm text-text-muted">Discover sessions matched to your mission.</p>
      </div>

      <SearchInput placeholder="Search sessions, speakers, topics..." value={query} onChange={(e) => setQuery(e.target.value)} />

      <div className="flex flex-wrap gap-2">
        {categoryFilters.map((c) => (
          <FilterChip key={c} active={activeCategory === c} onClick={() => setActiveCategory(activeCategory === c ? null : c)}>
            {c}
          </FilterChip>
        ))}
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon={<Search size={26} />}
          title="No sessions match your filters"
          description="Try a different search term or clear your category filter."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {filtered.map((s) => (
            <Link key={s.id} to={`/sessions/${s.id}`}>
              <Card interactive className="flex h-full flex-col p-5">
                <div className="flex items-center justify-between">
                  <Badge status="neutral">{s.category}</Badge>
                  <Badge status="go">{s.match}% match</Badge>
                </div>
                <p className="mt-3 text-sm font-semibold text-text-primary">{s.title}</p>
                <p className="mt-2 flex-1 text-xs text-text-muted line-clamp-2">{s.reason}</p>
                <div className="mt-4 flex flex-wrap items-center gap-1.5 text-xs text-text-muted">
                  <span>Level {s.level}</span>
                  <span>·</span>
                  <span>{s.format}</span>
                  <span>·</span>
                  <span>{s.venue}</span>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
