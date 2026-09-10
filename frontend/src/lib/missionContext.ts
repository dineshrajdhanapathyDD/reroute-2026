import { createContext, useContext } from 'react';
import type { Session, ScheduleBlock, Category, AgentActivityItem, JourneyLogEntry, RerouteOption } from './types';
import type { BackendPlan } from './api';

export interface DroppedSession { id: string; title: string; reason: string }

export interface MissionState {
  mission: string;
  goal: string;
  loading: boolean;
  live: boolean;
  journeyScore: number;
  routeQuality: number;
  sessions: Session[];
  scheduleBlocks: ScheduleBlock[];
  categories: Category[];
  agentActivity: AgentActivityItem[];
  journeyLog: JourneyLogEntry[];
  droppedSessions: DroppedSession[];
  recommendations: string[];
  selectedIds: string[];
  setMission: (m: string) => void;
  runPlan: (m?: string) => Promise<void>;
  applyPlan: (p: BackendPlan) => void;
  reroute: (droppedId: string, reason?: string) => Promise<{ options: RerouteOption[]; recommendedId?: string; metrics: { label: string; before: string; after: string; direction: string }[] }>;
  acceptReroute: (droppedId: string, newSessionId: string) => Promise<void>;
}

export const MissionContext = createContext<MissionState | null>(null);

export function useMission(): MissionState {
  const ctx = useContext(MissionContext);
  if (!ctx) throw new Error('useMission must be used within MissionProvider');
  return ctx;
}
