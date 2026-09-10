import { useState } from 'react';
import Card from '../components/ui/Card';
import ProgressBar from '../components/ui/ProgressBar';
import Badge from '../components/ui/Badge';
import { useMission } from '../lib/mission';

export default function Learning() {
  const { categories, sessions } = useMission();
  const [selected, setSelected] = useState<string | null>(null);
  const activeCategory = categories.find((c) => c.id === (selected ?? categories[0]?.id)) ?? categories[0];
  const relatedSessions = activeCategory ? sessions.filter((s) => s.category === activeCategory.name) : [];

  if (!activeCategory) {
    return (
      <div className="flex flex-col gap-6 animate-rise-in">
        <h1 className="font-display text-2xl font-semibold text-text-primary">Learning map</h1>
        <p className="mt-1 text-sm text-text-muted">Building your learning map…</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 animate-rise-in">
      <div>
        <h1 className="font-display text-2xl font-semibold text-text-primary">Learning map</h1>
        <p className="mt-1 text-sm text-text-muted">Your objectives, mapped by category and completion.</p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[280px_1fr]">
        <div className="flex flex-col gap-2">
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelected(cat.id)}
              className={`rounded-[var(--radius-card)] border p-4 text-left transition-colors ${
                selected === cat.id ? 'border-signal-500/50 bg-signal-500/10' : 'border-line bg-surface hover:bg-surface-raised'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-sm font-medium text-text-primary">
                  <span>{cat.emoji}</span> {cat.name}
                </span>
                <span className="font-mono text-xs text-text-secondary">{cat.progress}%</span>
              </div>
              <ProgressBar value={cat.progress} className="mt-2.5" />
            </button>
          ))}
        </div>

        <div className="flex flex-col gap-4">
          <Card className="p-5">
            <div className="flex items-center justify-between">
              <h2 className="font-display text-lg font-semibold text-text-primary">
                {activeCategory.emoji} {activeCategory.name}
              </h2>
              <Badge status={activeCategory.progress >= 80 ? 'go' : activeCategory.progress >= 40 ? 'caution' : 'critical'}>
                {activeCategory.progress}% complete
              </Badge>
            </div>
            <ProgressBar value={activeCategory.progress} className="mt-3" />
          </Card>

          <div>
            <p className="mb-2 text-sm font-medium text-text-secondary">Recommended sessions in this category</p>
            {relatedSessions.length === 0 ? (
              <Card className="p-5 text-sm text-text-muted">No sessions found in this category yet.</Card>
            ) : (
              <div className="flex flex-col gap-3">
                {relatedSessions.map((s) => (
                  <Card key={s.id} interactive className="p-4">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium text-text-primary">{s.title}</p>
                      <Badge status="go">{s.match}%</Badge>
                    </div>
                    <p className="mt-1 text-xs text-text-muted">{s.venue} · {s.start} · Level {s.level}</p>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
