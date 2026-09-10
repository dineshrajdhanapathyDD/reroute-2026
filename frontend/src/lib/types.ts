export type StatusLevel = 'go' | 'caution' | 'critical' | 'info' | 'neutral';

export interface Category {
  id: string;
  name: string;
  emoji: string;
  progress: number; // 0-100
}

export interface Session {
  id: string;
  title: string;
  category: string;
  level: 100 | 200 | 300 | 400;
  format: 'Workshop' | 'Chalk Talk' | 'Code Talk' | 'Breakout' | 'Lightning Talk';
  venue: string;
  room?: string;
  start: string; // ISO-ish display time e.g. "09:00"
  end: string;
  day: string; // e.g. "MON NOV 30"
  match: number; // journey match %
  reason: string;
  speakers?: string[];
  description?: string;
  locationVerified?: boolean;
}

export interface ScheduleBlock {
  type: 'session' | 'break' | 'transition';
  time: string;
  session?: Session;
  label?: string;
  durationMin?: number;
  transitionRisk?: StatusLevel;
}

export interface RerouteOption {
  id: string;
  title: string;
  reason: string;
  impact: string;
  sessions: string[];
  recommended?: boolean;
}

export interface AgentActivityItem {
  id: string;
  timestamp: string;
  actor: 'agent' | 'user';
  action: string;
  detail: string;
  status: StatusLevel;
}

export interface JourneyLogEntry {
  id: string;
  day: string;
  time: string;
  type: 'attended' | 'missed' | 'rerouted' | 'note' | 'milestone';
  title: string;
  detail?: string;
}
