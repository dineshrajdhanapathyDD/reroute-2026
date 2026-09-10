// Map backend responses -> the frontend's existing UI types (types.ts), so the
// designed pages render live data without changing their JSX.
import type {
  Session, ScheduleBlock, RerouteOption, AgentActivityItem, JourneyLogEntry, Category, StatusLevel,
} from './types';
import type { BackendSession, BackendPlan, BackendReroute } from './api';

const FORMAT_MAP: Record<string, Session['format']> = {
  Workshop: 'Workshop', 'Chalk Talk': 'Chalk Talk', 'Code Talk': 'Code Talk',
  Breakout: 'Breakout', 'Lightning Talk': 'Lightning Talk',
  "Builders' Session": 'Chalk Talk', Lab: 'Workshop', 'Gamified Learning': 'Workshop',
  'Exam Prep': 'Breakout', Bootcamp: 'Workshop', Keynote: 'Breakout',
};

function toLevel(v?: string): Session['level'] {
  const n = parseInt(String(v ?? '300'), 10);
  if (n <= 100) return 100;
  if (n <= 200) return 200;
  if (n >= 400) return 400;
  return 300;
}

function fmtTime(iso?: string): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return String(iso);
  const h = d.getHours().toString().padStart(2, '0');
  const m = d.getMinutes().toString().padStart(2, '0');
  return `${h}:${m}`;
}

function fmtDay(iso?: string, dayName?: string): string {
  if (dayName && dayName.length <= 12) return dayName.toUpperCase();
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return String(dayName ?? '');
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }).toUpperCase();
}

export function mapSession(s: BackendSession): Session {
  return {
    id: s.id,
    title: s.title,
    category: s.topic || 'General',
    level: toLevel(s.level),
    format: FORMAT_MAP[s.format] ?? 'Breakout',
    venue: s.venue || 'TBD',
    room: s.room || undefined,
    start: fmtTime(s.start),
    end: fmtTime(s.end),
    day: fmtDay(s.start, s.day),
    match: s.match_score ?? 0,
    reason: s.why || '',
    speakers: undefined,
    description: undefined,
    locationVerified: (s.status ?? 'available') === 'available',
  };
}

export function mapSessions(list: BackendSession[]): Session[] {
  return (list || []).map(mapSession);
}

// Backend daily_schedule (one day's items) -> UI ScheduleBlocks for that day.
export function mapScheduleBlocks(plan: BackendPlan, dayFilter?: string): ScheduleBlock[] {
  const sessionById = new Map(plan.sessions.map((s) => [s.id, s]));
  const days = (plan.daily_schedule || []).filter((d) => d.day !== 'Arrival Day');
  const day = dayFilter ? days.find((d) => d.day === dayFilter) : days[0];
  if (!day) return [];
  const blocks: ScheduleBlock[] = [];
  for (const item of day.items) {
    if (item.kind === 'session' && item.session_id && sessionById.has(item.session_id)) {
      blocks.push({ type: 'session', time: item.time, session: mapSession(sessionById.get(item.session_id)!) });
    } else if (item.kind === 'travel') {
      blocks.push({ type: 'transition', time: item.time, label: item.activity, transitionRisk: 'info' });
    } else {
      blocks.push({ type: 'break', time: item.time, label: item.activity });
    }
  }
  return blocks;
}

export function mapCategories(plan: BackendPlan): Category[] {
  const cov = plan.scores?.learning_coverage || {};
  const emoji: Record<string, string> = {
    Agents: '🤖', 'Generative AI': '🧠', 'Amazon Bedrock': '🟠', Architecture: '🏗️',
    Security: '🔐', Serverless: '⚡', Data: '📊', Containers: '📦',
  };
  return Object.entries(cov).map(([name, progress]) => ({
    id: name.toLowerCase().replace(/\s+/g, '-'),
    name,
    emoji: emoji[name] || '📁',
    progress: Math.round(progress as number),
  }));
}

export function mapReroute(r: BackendReroute): RerouteOption[] {
  return (r.alternatives || []).map((a) => ({
    id: a.session.id,
    title: a.session.title,
    reason: a.note,
    impact: `${a.match_score}% match`,
    sessions: [a.session.id],
    recommended: a.session.id === r.recommended_alternative_id,
  }));
}

export function mapAgentActivity(
  events: BackendPlan['agent_activity'] = [],
): AgentActivityItem[] {
  const statusMap: Record<string, StatusLevel> = { done: 'go', active: 'info', waiting: 'caution' };
  return (events || []).map((e, i) => ({
    id: `act-${i}`,
    timestamp: '',
    actor: 'agent',
    action: `${e.icon} ${e.agent}: ${e.task}`,
    detail: `${e.action} → ${e.result}`,
    status: statusMap[e.status ?? 'done'] ?? 'neutral',
  }));
}

// Build a Journey log from the plan: agent milestones + resolved-conflict
// (dropped session) entries + recommendation notes.
export function mapJourneyLog(plan: BackendPlan): JourneyLogEntry[] {
  const day = plan.trip?.arrival_date || 'PLAN';
  const entries: JourneyLogEntry[] = [];
  (plan.agent_activity || []).forEach((e, i) => {
    entries.push({
      id: `j-act-${i}`, day, time: '',
      type: 'milestone',
      title: `${e.icon} ${e.agent}: ${e.task}`,
      detail: e.result,
    });
  });
  (plan.dropped_sessions || []).slice(0, 5).forEach((d, i) => {
    entries.push({
      id: `j-drop-${i}`, day, time: '',
      type: 'rerouted',
      title: `Set aside: ${d.title}`,
      detail: d.reason,
    });
  });
  (plan.recommendations || []).slice(0, 4).forEach((r, i) => {
    entries.push({
      id: `j-rec-${i}`, day, time: '',
      type: 'note',
      title: r.length > 70 ? r.slice(0, 70) + '…' : r,
    });
  });
  return entries;
}
