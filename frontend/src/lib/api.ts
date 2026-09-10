// Typed API client for the Re:Route AI backend (FastAPI + Strands agent + MCP).
//
// Base URL: uses VITE_API_BASE when set (e.g. the deployed Lambda API Gateway
// URL), else the local Vite proxy at '/api'. Every call fails soft — callers
// fall back to bundled mock data so the UI always renders.

const API_ROOT = (import.meta.env?.VITE_API_BASE || '').replace(/\/$/, '');
const BASE = API_ROOT ? `${API_ROOT}/api` : '/api';

async function get<T>(path: string): Promise<T> {
  const res = await fetch(BASE + path);
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? {}),
  });
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

// ---- Backend response shapes (loose; mappers normalize into UI types) ---- //
export interface BackendSession {
  id: string;
  title: string;
  topic: string;
  format: string;
  venue: string;
  room?: string;
  day: string;
  start: string; // ISO
  end: string;
  level?: string;
  learning_mode?: string;
  hands_on?: boolean;
  match_score?: number;
  why?: string;
  catalog_url?: string;
  official_url?: string;
  status?: string;
}

export interface BackendPlan {
  trip: { origin: string; destination: string; learning_goal: string; arrival_date?: string };
  sessions: BackendSession[];
  dropped_sessions?: { id: string; title: string; reason: string }[];
  daily_schedule?: {
    day: string;
    items: { time: string; activity: string; venue?: string; session_id?: string; kind: string; icon: string }[];
    walking_km: number;
    venue_changes: number;
    break_minutes: number;
    capacity: string;
  }[];
  travel_routes?: {
    from_venue: string; to_venue: string; walk_minutes: number;
    shuttle_available: boolean; buffer_minutes: number;
  }[];
  scores?: {
    journey_score: number;
    route_quality: number;
    learning_coverage?: Record<string, number>;
    breakdown?: Record<string, number>;
    learning_mode_mix?: Record<string, number>;
  };
  agent_activity?: { agent: string; icon: string; task: string; action: string; result: string; status?: string }[];
  recommendations?: string[];
}

export interface BackendReroute {
  reason: string;
  dropped_session_id: string;
  alternatives: { session: BackendSession; match_score: number; note: string }[];
  recommended_alternative_id?: string;
  metrics: { label: string; before: string; after: string; direction: string }[];
  agent_activity?: { agent: string; icon: string; task: string; action: string; result: string; status?: string }[];
}

export interface ChatTurn {
  role: 'user' | 'assistant';
  content: string;
}

export interface ABCPlanEntry {
  key: string;
  label: string;
  rationale: string;
  tip?: string;
  plan: BackendPlan;
  summary: Record<string, number>;
}

export interface ChatReply {
  reply: string;
  intent: string;
  suggestions: string[];
  data: {
    kind: 'plan' | 'plans_abc' | 'sessions' | 'tips' | null;
    plan?: BackendPlan;
    plans?: ABCPlanEntry[];
    goal?: string;
    sessions?: BackendSession[];
    tips?: { id: string; text: string; tags: string[]; source: string; score: number }[];
  };
}

export interface MonitorOption {
  id: string;
  title: string;
  note: string;
  match_score: number;
  venue?: string;
  day?: string;
}

export interface MonitorDecision {
  id: string;
  kind: string;
  severity: 'high' | 'medium';
  session_id: string;
  title: string;
  summary: string;
  options: MonitorOption[];
  recommended_option_id?: string;
  status: string;
  resolution?: string;
}

export interface MonitorStatus {
  watching: boolean;
  learning_goal: string;
  watched_sessions: number;
  selected_ids: string[];
  scan_count: number;
  last_scan_at: number;
  pending_decisions: MonitorDecision[];
  resolved_decisions: MonitorDecision[];
  healthy: boolean;
}

export interface MonitorScan {
  watching: boolean;
  scan_count?: number;
  checked: number;
  new_decisions: MonitorDecision[];
  pending?: number;
}

// ---- API ---- //
export const api = {
  health: () => get<Record<string, unknown>>('/health'),

  createPlan: (mission: string) => post<BackendPlan>('/plan', { mission }),

  plansABC: (mission: string) =>
    post<{ goal: string; plans: { key: string; label: string; rationale: string; tip?: string; plan: BackendPlan; summary: Record<string, number> }[] }>(
      '/plans/abc', { mission },
    ),

  catalogFacets: () =>
    get<{ total: number; topics: string[]; levels: string[]; formats: string[]; venues: string[]; days: string[]; learning_modes: string[] }>(
      '/catalog/facets',
    ),

  catalogFilter: (params: Record<string, string | number>) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== '' && v != null).map(([k, v]) => [k, String(v)]),
    ).toString();
    return get<{ total: number; page: number; pages: number; sessions: BackendSession[] }>(`/catalog/filter?${qs}`);
  },

  sessions: (topics = '') => get<{ sessions: BackendSession[] }>(`/sessions?topics=${encodeURIComponent(topics)}`),

  reroute: (droppedId: string, selectedIds: string[], reason: string) =>
    post<BackendReroute>('/reroute', { dropped_session_id: droppedId, current_selected_ids: selectedIds, reason }),

  addSession: (sessionId: string, currentIds: string[], learningGoal: string) =>
    post<BackendPlan>('/plan/add-session', { session_id: sessionId, current_selected_ids: currentIds, learning_goal: learningGoal }),

  advice: (mission: string) =>
    post<{ tips: { id: string; text: string; tags: string[]; source: string; score: number }[]; commentary: string; knowledge_count: number }>(
      '/advice', { mission },
    ),

  chat: (message: string, history: ChatTurn[] = []) =>
    post<ChatReply>('/chat', { message, history }),

  // Autonomous background monitor.
  monitorWatch: (selectedIds: string[], learningGoal: string) =>
    post<MonitorStatus>('/monitor/watch', { selected_ids: selectedIds, learning_goal: learningGoal }),
  monitorScan: () => post<MonitorScan>('/monitor/scan', {}),
  monitorStatus: () => get<MonitorStatus>('/monitor/status'),
  monitorResolve: (decisionId: string, action: 'approve' | 'dismiss', chosenOptionId?: string) =>
    post<{ decision: MonitorDecision; selected_ids: string[] }>(
      `/monitor/decision/${decisionId}/resolve`, { action, chosen_option_id: chosenOptionId },
    ),

  event: () => get<Record<string, unknown>>('/event'),
  officialLinks: () => get<Record<string, string>>('/official-links'),
  awsStatus: () => get<Record<string, unknown>>('/aws/status'),
};

export function apiConfigured(): boolean {
  return true; // BASE always resolves (proxy or VITE_API_BASE)
}
