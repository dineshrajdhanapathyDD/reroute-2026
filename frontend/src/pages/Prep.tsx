import { useEffect, useState } from 'react';
import { Compass } from 'lucide-react';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import SearchInput from '../components/ui/SearchInput';
import { api } from '../lib/api';
import { useMission } from '../lib/mission';

interface Tip { id: string; text: string; tags: string[]; source: string; score: number }

export default function Prep() {
  const { mission } = useMission();
  const [query, setQuery] = useState('');
  const [tips, setTips] = useState<Tip[]>([]);
  const [commentary, setCommentary] = useState('');
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(false);

  const ask = async (q: string) => {
    setLoading(true);
    try {
      const res = await api.advice(q || mission);
      setTips(res.tips as Tip[]);
      setCommentary(res.commentary);
      setCount(res.knowledge_count);
    } catch { /* keep prior */ }
    finally { setLoading(false); }
  };

  useEffect(() => { ask(''); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex flex-col gap-6 animate-rise-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold text-text-primary">Preparation advice</h1>
          <p className="mt-1 text-sm text-text-muted">Grounded in past re:Invent experience (RAG).</p>
        </div>
        <Badge status="info">{count} tips</Badge>
      </div>

      <div className="flex gap-2">
        <div className="flex-1">
          <SearchInput placeholder="Ask about preparing (e.g. travel between venues)..." value={query}
            onChange={(e) => setQuery(e.target.value)} />
        </div>
        <Button size="sm" onClick={() => ask(query)} disabled={loading}>{loading ? 'Asking…' : 'Ask'}</Button>
      </div>

      {commentary && (
        <Card glow className="flex items-start gap-2 p-5">
          <Compass size={16} className="mt-0.5 shrink-0 text-signal-400" />
          <p className="text-sm text-text-primary">{commentary}</p>
        </Card>
      )}

      <div className="flex flex-col gap-3">
        {tips.map((t) => (
          <Card key={t.id} className="p-4">
            <p className="text-sm text-text-primary">{t.text}</p>
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap gap-1.5">
                {t.tags.slice(0, 4).map((tag) => (
                  <span key={tag} className="rounded-full border border-line-soft bg-hull px-2 py-0.5 text-[11px] text-text-muted">{tag}</span>
                ))}
              </div>
              {t.source && <span className="text-[11px] text-text-muted">{t.source}</span>}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
